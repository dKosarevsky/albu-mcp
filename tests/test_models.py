from pathlib import Path

import pytest
from pydantic import ValidationError

from albumentationsx_mcp.models import ComposeSpec, PreviewRequest, TransformSpec


def test_transform_spec_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        TransformSpec.model_validate({"name": "GaussNoise", "params": {}, "unexpected": True})


@pytest.mark.parametrize("probability", [-0.1, 1.1])
def test_transform_probability_must_be_between_zero_and_one(probability: float) -> None:
    with pytest.raises(ValidationError):
        TransformSpec(name="Blur", p=probability)


def test_compose_spec_requires_at_least_one_transform() -> None:
    with pytest.raises(ValidationError):
        ComposeSpec(transforms=[])


@pytest.mark.parametrize("count", [0, 17])
def test_preview_request_bounds_variant_count(count: int, tmp_path: Path) -> None:
    pipeline = ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)])

    with pytest.raises(ValidationError):
        PreviewRequest(input_paths=[tmp_path / "image.png"], pipeline=pipeline, variants_per_image=count)
