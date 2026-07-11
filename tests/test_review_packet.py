from pathlib import Path

from PIL import Image

from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.preview import PathPolicy
from albumentationsx_mcp.recipes import recommend_recipe
from albumentationsx_mcp.review_packet import build_review_packet


def test_review_packet_builds_first_preview_handoff(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    _write_image(dataset_dir / "sample.png")

    packet = build_review_packet(
        dataset_path=dataset_dir,
        task="classification",
        intensity="low",
        targets=["image"],
        max_images=1,
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert packet.status == "ok"
    assert packet.preview_ready is True
    assert packet.recommended_next_tool == "validate_preview_request"
    assert packet.review_brief[0] == "Preview-ready dataset: 1 sampled image out of 1 supported image."
    assert packet.tool_sequence == [
        "validate_preview_request",
        "render_preview_batch",
        "adjust_pipeline",
        "render_preview_batch",
        "compare_preview_runs",
        "export_preview_report",
        "export_pipeline",
    ]
    assert packet.preview_request_template is not None
    assert packet.preview_request_template["tool"] == "render_preview_batch"
    assert packet.report_handoff["tool"] == "export_preview_report"
    assert packet.report_handoff["resource"] == "albumentationsx://examples/report-handoff"


def test_review_packet_accepts_one_supported_image(tmp_path: Path) -> None:
    image_path = _write_image(tmp_path / "sample.png")

    packet = build_review_packet(
        dataset_path=image_path,
        task="classification",
        intensity="low",
        targets=["image"],
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert packet.preview_ready is True
    assert packet.dataset_path == str(image_path.resolve())
    assert packet.preview_request_template is not None
    assert packet.preview_request_template["request"]["input_paths"] == [str(image_path.resolve())]


def test_review_packet_blocks_unready_dataset_with_remediation(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "empty"
    dataset_dir.mkdir()

    packet = build_review_packet(
        dataset_path=dataset_dir,
        task="classification",
        intensity="low",
        targets=["image"],
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert packet.preview_ready is False
    assert packet.recommended_next_tool == "fix_dataset"
    assert packet.preview_request_template is None
    assert packet.remediation_actions[0]["code"] == "add_dataset_images"


def _write_image(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 12), color=(80, 120, 160)).save(path)
    return path
