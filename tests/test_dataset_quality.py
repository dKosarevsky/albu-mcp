from __future__ import annotations

from pathlib import Path

from PIL import Image

from albumentationsx_mcp.dataset_quality import inspect_dataset_quality
from albumentationsx_mcp.preview import PathPolicy


def test_inspect_dataset_quality_summarizes_supported_images(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    _write_image(dataset_dir / "normal.png", color=(90, 120, 150))
    _write_image(dataset_dir / "clipped.png", color=(255, 255, 255))
    (dataset_dir / "notes.txt").write_text("not an image", encoding="utf-8")

    report = inspect_dataset_quality(dataset_path=dataset_dir, path_policy=PathPolicy([tmp_path]), max_images=2)

    assert report.status == "warning"
    assert report.image_count == 2
    assert report.sampled_image_count == 2
    assert report.ignored_file_count == 1
    assert report.unreadable_image_count == 0
    assert report.aggregate.image_count == 2
    assert "build_review_packet" in report.recommended_next_tools
    assert "render_preview_batch" in report.recommended_next_tools
    assert "dataset_high_clipping" in {finding.code for finding in report.findings}


def test_inspect_dataset_quality_reports_unreadable_images(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    (dataset_dir / "broken.png").write_text("not really an image", encoding="utf-8")

    report = inspect_dataset_quality(dataset_path=dataset_dir, path_policy=PathPolicy([tmp_path]), max_images=1)

    assert report.status == "warning"
    assert report.image_count == 1
    assert report.sampled_image_count == 1
    assert report.unreadable_image_count == 1
    assert report.aggregate.image_count == 0
    assert report.findings[0].code == "sample_unreadable_images"
    assert report.remediation_actions[0]["code"] == "fix_unreadable_images"


def test_inspect_dataset_quality_blocks_outside_allowed_root(tmp_path: Path) -> None:
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    report = inspect_dataset_quality(dataset_path=outside_dir, path_policy=PathPolicy([tmp_path / "allowed"]))

    assert report.status == "error"
    assert report.image_count == 0
    assert report.recommended_next_tools == ["fix_dataset_path"]
    assert report.remediation_actions[0]["code"] == "move_dataset_under_allowed_root"


def _write_image(path: Path, *, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (24, 16), color=color).save(path)
