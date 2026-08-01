from pathlib import Path

import pytest
from pydantic import ValidationError

from albumentationsx_mcp.models import MAX_SIGNED_64, ComposeSpec, PreviewRequest, PreviewResult, TransformSpec


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


def test_preview_result_tracks_variant_trace_count_with_zero_default() -> None:
    default_result = PreviewResult.model_validate(_preview_result_payload())
    traced_result = PreviewResult.model_validate(_preview_result_payload(variant_trace_count=3))

    assert default_result.variant_trace_count == 0
    assert traced_result.variant_trace_count == 3


@pytest.mark.parametrize("variant_trace_count", [-1, MAX_SIGNED_64 + 1])
def test_preview_result_bounds_variant_trace_count(variant_trace_count: int) -> None:
    with pytest.raises(ValidationError):
        PreviewResult.model_validate(_preview_result_payload(variant_trace_count=variant_trace_count))


def _preview_result_payload(*, variant_trace_count: int | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "run_id": "preview-run",
        "artifacts": [],
        "manifest": {
            "kind": "manifest",
            "uri": "artifact://preview-run/manifest.json",
            "path": "/artifacts/preview-run/manifest.json",
            "mime_type": "application/json",
            "sha256": "0" * 64,
            "size_bytes": 1,
        },
        "pipeline": {},
    }
    if variant_trace_count is not None:
        payload["variant_trace_count"] = variant_trace_count
    return payload
