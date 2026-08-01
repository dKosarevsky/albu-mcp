from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import albumentations as A
import numpy as np
import pytest

from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.models import (
    ComposeSpec,
    ConstraintInfo,
    ParameterInfo,
    TargetSpec,
    TransformMetadata,
    TransformSpec,
)
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.preview_trace import build_variant_trace


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


def test_build_pipeline_adapts_public_bbox_format_for_runtime() -> None:
    service = PipelineService(TransformCatalog())
    spec = ComposeSpec(
        transforms=[TransformSpec(name="HorizontalFlip", p=1.0)],
        bbox_params={"format": "pascal_voc", "label_fields": ["labels"]},
    )

    pipeline = service.build_pipeline(spec)

    assert pipeline is not None


def test_build_pipeline_records_applied_params_without_changing_seeded_output() -> None:
    image = np.arange(16 * 16 * 3, dtype=np.uint8).reshape((16, 16, 3))
    spec = ComposeSpec(
        transforms=[
            TransformSpec(name="HorizontalFlip", p=1.0),
            TransformSpec(name="GaussNoise", params={"std_range": (0.01, 0.02)}, p=1.0),
        ],
        seed=17,
    )
    ordinary_result = A.Compose(
        [A.HorizontalFlip(p=1.0), A.GaussNoise(std_range=(0.01, 0.02), p=1.0)],
        seed=17,
    )(image=image)

    instrumented_result = PipelineService(TransformCatalog()).build_pipeline(spec)(image=image)

    assert instrumented_result["image"].tobytes() == ordinary_result["image"].tobytes()
    applied_transforms = instrumented_result["applied_transforms"]
    assert type(applied_transforms) is list
    assert all(type(entry) is tuple and type(entry[1]) is dict for entry in applied_transforms)
    assert [name for name, _ in applied_transforms] == [
        "HorizontalFlip",
        "GaussNoise",
    ]
    trace = build_variant_trace(
        image_index=0,
        variant_index=0,
        source_path="source.png",
        artifact_uri="artifact://run/000-000.png",
        effective_seed=17,
        applied_transforms=applied_transforms,
    )
    assert [transform.name for transform in trace.applied_transforms] == ["HorizontalFlip", "GaussNoise"]


def test_export_python_adapts_public_bbox_format_for_runtime() -> None:
    service = PipelineService(TransformCatalog())
    spec = ComposeSpec(
        transforms=[TransformSpec(name="HorizontalFlip", p=1.0)],
        bbox_params={"format": "pascal_voc", "label_fields": ["labels"]},
    )

    exported = service.export_pipeline(spec, output_format="python")

    assert "'coord_format': 'pascal_voc'" in exported.content
    assert "'format': 'pascal_voc'" not in exported.content
