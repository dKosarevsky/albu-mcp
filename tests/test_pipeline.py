from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from albumentationsx_mcp.models import (
    ComposeSpec,
    ConstraintInfo,
    ParameterInfo,
    TargetSpec,
    TransformMetadata,
    TransformSpec,
)
from albumentationsx_mcp.pipeline import PipelineService


class DummyTransform:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


@dataclass
class FakeCatalog:
    transforms: dict[str, TransformMetadata]

    def get_transform_schema(self, name: str) -> TransformMetadata:
        if name not in self.transforms:
            raise KeyError(name)
        return self.transforms[name]

    def resolve_transform(self, name: str) -> type[DummyTransform]:
        if name not in self.transforms:
            raise KeyError(name)
        return DummyTransform


@pytest.fixture
def catalog() -> FakeCatalog:
    return FakeCatalog(
        transforms={
            "GaussNoise": TransformMetadata(
                name="GaussNoise",
                module="albumentations.augmentations.pixel.transforms",
                transform_type="image_only",
                targets=["image", "volume"],
                parameters={
                    "std_range": ParameterInfo(
                        name="std_range",
                        type_hint="tuple[float, float]",
                        default=(0.1, 0.2),
                        constraints=ConstraintInfo(ge=0.0, le=1.0),
                    ),
                    "p": ParameterInfo(
                        name="p",
                        type_hint="float",
                        default=0.5,
                        constraints=ConstraintInfo(ge=0.0, le=1.0),
                    ),
                },
            ),
        },
    )


def test_validate_pipeline_reports_unknown_transform(catalog: FakeCatalog) -> None:
    service = PipelineService(catalog)
    spec = ComposeSpec(transforms=[TransformSpec(name="NotARealTransform")])

    report = service.validate_pipeline(spec, TargetSpec(targets=["image"]))

    assert not report.valid
    assert report.errors[0].code == "unknown_transform"
    assert report.errors[0].path == "transforms.0.name"


def test_validate_pipeline_reports_unknown_parameter(catalog: FakeCatalog) -> None:
    service = PipelineService(catalog)
    spec = ComposeSpec(transforms=[TransformSpec(name="GaussNoise", params={"bad": 1})])

    report = service.validate_pipeline(spec, TargetSpec(targets=["image"]))

    assert not report.valid
    assert report.errors[0].code == "unknown_parameter"
    assert report.errors[0].path == "transforms.0.params.bad"


def test_validate_pipeline_checks_numeric_constraints(catalog: FakeCatalog) -> None:
    service = PipelineService(catalog)
    spec = ComposeSpec(transforms=[TransformSpec(name="GaussNoise", params={"std_range": (0.2, 2.0)})])

    report = service.validate_pipeline(spec, TargetSpec(targets=["image"]))

    assert not report.valid
    assert report.errors[0].code == "constraint_violation"
    assert "le=1.0" in report.errors[0].message


def test_export_python_contains_reproducible_compose(catalog: FakeCatalog) -> None:
    service = PipelineService(catalog)
    spec = ComposeSpec(
        transforms=[TransformSpec(name="GaussNoise", params={"std_range": (0.1, 0.2)}, p=0.25)],
        seed=137,
    )

    exported = service.export_pipeline(spec, output_format="python")

    assert "import albumentations as A" in exported.content
    assert "A.Compose" in exported.content
    assert "A.GaussNoise" in exported.content
    assert "seed=137" in exported.content
