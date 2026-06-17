from pathlib import Path

import numpy as np
from PIL import Image

from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.models import TargetSpec
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.presets import recommend_pipeline
from albumentationsx_mcp.preview import PathPolicy
from albumentationsx_mcp.preview_validation import PreviewRequestValidator


def test_validate_preview_request_reports_missing_input_path(tmp_path: Path) -> None:
    validator = _validator(tmp_path)

    report = validator.validate(_request(tmp_path / "images" / "missing.png"), target=TargetSpec(targets=["image"]))

    assert report.valid is False
    assert report.status == "error"
    assert "input_path_missing" in {check.code for check in report.checks}
    assert any(action.code == "fix_input_paths" for action in report.remediation_actions)
    assert any("missing.png" in action for action in report.next_actions)


def test_validate_preview_request_reports_outside_allowed_root(tmp_path: Path) -> None:
    outside_path = tmp_path / "outside" / "sample.png"
    _write_image(outside_path)
    validator = _validator(tmp_path)

    report = validator.validate(_request(outside_path), target=TargetSpec(targets=["image"]))

    assert report.valid is False
    assert report.status == "error"
    outside_check = next(check for check in report.checks if check.code == "input_path_outside_allowed_root")
    assert outside_check.severity == "high"
    assert outside_check.details["path"] == str(outside_path.resolve())
    assert any(action.code == "move_inputs_under_allowed_root" for action in report.remediation_actions)


def test_validate_preview_request_reports_annotation_count_mismatch(tmp_path: Path) -> None:
    image_path = tmp_path / "images" / "sample.png"
    _write_image(image_path)
    validator = _validator(tmp_path)
    request = {
        **_request(image_path),
        "annotations": [None, None],
    }

    report = validator.validate(request, target=TargetSpec(targets=["image"]))

    assert report.valid is False
    assert "annotation_count_mismatch" in {check.code for check in report.checks}
    assert any(action.code == "fix_annotations" for action in report.remediation_actions)


def test_validate_preview_request_reports_mask_path_missing(tmp_path: Path) -> None:
    image_path = tmp_path / "images" / "sample.png"
    _write_image(image_path)
    validator = _validator(tmp_path)
    request = {
        **_request(image_path),
        "annotations": [{"mask_path": str(tmp_path / "images" / "missing-mask.png")}],
    }

    report = validator.validate(request, target=TargetSpec(targets=["image", "mask"]))

    assert report.valid is False
    assert "mask_path_missing" in {check.code for check in report.checks}
    assert any(action.code == "fix_mask_paths" for action in report.remediation_actions)


def test_validate_preview_request_accepts_valid_request(tmp_path: Path) -> None:
    image_path = tmp_path / "images" / "sample.png"
    _write_image(image_path)
    validator = _validator(tmp_path)

    report = validator.validate(_request(image_path), target=TargetSpec(targets=["image"]))

    assert report.valid is True
    assert report.status == "ok"
    assert report.warnings == []
    assert report.remediation_actions == []
    assert report.normalized_request is not None
    assert "input_path_accessible" in {check.code for check in report.checks}
    assert report.next_actions == ["Call `render_preview_batch` with the validated request."]


def _validator(tmp_path: Path) -> PreviewRequestValidator:
    images_root = tmp_path / "images"
    images_root.mkdir(parents=True, exist_ok=True)
    return PreviewRequestValidator(
        pipeline_service=PipelineService(TransformCatalog()),
        path_policy=PathPolicy([images_root]),
    )


def _request(image_path: Path) -> dict:
    pipeline = recommend_pipeline(task="classification", intensity="low", targets=["image"])
    return {
        "input_paths": [str(image_path)],
        "pipeline": pipeline.model_dump(mode="json", exclude_none=True),
        "variants_per_image": 1,
        "seed": 137,
        "max_side": 128,
    }


def _write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.full((16, 16, 3), 127, dtype=np.uint8)).save(path)
