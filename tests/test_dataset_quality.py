from __future__ import annotations

import json
from pathlib import Path

import pytest
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


def test_inspect_dataset_quality_reports_split_class_size_and_duplicates(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    duplicate_color = (10, 20, 30)
    _write_image(dataset_dir / "train" / "cat" / "cat-1.png", color=duplicate_color, size=(32, 16))
    _write_image(dataset_dir / "train" / "cat" / "cat-duplicate.png", color=duplicate_color, size=(32, 16))
    _write_image(dataset_dir / "train" / "dog" / "dog-1.png", color=(80, 90, 100), size=(20, 20))
    _write_image(dataset_dir / "val" / "cat" / "cat-val.png", color=(120, 130, 140), size=(12, 24))

    report = inspect_dataset_quality(dataset_path=dataset_dir, path_policy=PathPolicy([tmp_path]), max_images=4)

    assert report.split_distribution == {"train": 3, "val": 1}
    assert report.class_distribution == {"cat": 3, "dog": 1}
    assert report.image_size_summary is not None
    assert report.image_size_summary.min_width == 12
    assert report.image_size_summary.max_width == 32
    assert report.image_size_summary.min_height == 16
    assert report.image_size_summary.max_height == 24
    assert report.image_size_summary.aspect_ratio_min == pytest.approx(0.5)
    assert report.image_size_summary.aspect_ratio_max == pytest.approx(2.0)
    assert report.duplicate_image_count == 2
    assert len(report.duplicate_groups) == 1
    assert {Path(path).name for path in report.duplicate_groups[0].sample_paths} == {
        "cat-1.png",
        "cat-duplicate.png",
    }
    finding_codes = {finding.code for finding in report.findings}
    assert "dataset_class_imbalance" in finding_codes
    assert "dataset_exact_duplicate_images" in finding_codes


def test_inspect_dataset_quality_reports_coco_annotation_consistency(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    _write_image(dataset_dir / "images" / "annotated.png", color=(90, 120, 150))
    _write_image(dataset_dir / "images" / "missing.png", color=(80, 110, 140))
    annotations_dir = dataset_dir / "annotations"
    annotations_dir.mkdir()
    (annotations_dir / "instances_train.json").write_text(
        json.dumps(
            {
                "images": [
                    {"id": 1, "file_name": "images/annotated.png"},
                    {"id": 2, "file_name": "images/missing.png"},
                ],
                "annotations": [
                    {"id": 1, "image_id": 1, "bbox": [2, 3, 10, 8], "category_id": 7},
                    {"id": 2, "image_id": 999, "bbox": [1, 1, 4, 4], "category_id": 7},
                    {"id": 3, "image_id": 1, "bbox": [1, 1, -4, 4], "category_id": 7},
                ],
                "categories": [{"id": 7, "name": "object"}],
            }
        ),
        encoding="utf-8",
    )

    report = inspect_dataset_quality(dataset_path=dataset_dir, path_policy=PathPolicy([tmp_path]), max_images=2)

    assert report.annotation_summary is not None
    assert report.annotation_summary.source_format == "coco"
    assert report.annotation_summary.annotated_image_count == 1
    assert report.annotation_summary.missing_annotation_count == 1
    assert report.annotation_summary.orphan_annotation_count == 1
    assert report.annotation_summary.invalid_annotation_count == 1
    finding_codes = {finding.code for finding in report.findings}
    assert "dataset_missing_annotations" in finding_codes
    assert "dataset_orphan_annotations" in finding_codes
    assert "dataset_invalid_annotations" in finding_codes
    assert "review_annotation_consistency" in {action["code"] for action in report.remediation_actions}


def test_inspect_dataset_quality_reports_yolo_annotation_consistency(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    _write_image(dataset_dir / "images" / "annotated.png", color=(90, 120, 150))
    _write_image(dataset_dir / "images" / "missing.png", color=(80, 110, 140))
    labels_dir = dataset_dir / "labels"
    labels_dir.mkdir()
    (labels_dir / "annotated.txt").write_text("1 0.5 0.5 0.4 0.4\nbad label\n", encoding="utf-8")
    (labels_dir / "orphan.txt").write_text("1 0.5 0.5 0.4 0.4\n", encoding="utf-8")

    report = inspect_dataset_quality(dataset_path=dataset_dir, path_policy=PathPolicy([tmp_path]), max_images=2)

    assert report.annotation_summary is not None
    assert report.annotation_summary.source_format == "yolo"
    assert report.annotation_summary.annotated_image_count == 1
    assert report.annotation_summary.missing_annotation_count == 1
    assert report.annotation_summary.orphan_annotation_count == 1
    assert report.annotation_summary.invalid_annotation_count == 1
    assert "dataset_invalid_annotations" in {finding.code for finding in report.findings}


def test_inspect_dataset_quality_blocks_outside_allowed_root(tmp_path: Path) -> None:
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    report = inspect_dataset_quality(dataset_path=outside_dir, path_policy=PathPolicy([tmp_path / "allowed"]))

    assert report.status == "error"
    assert report.image_count == 0
    assert report.recommended_next_tools == ["fix_dataset_path"]
    assert report.remediation_actions[0]["code"] == "move_dataset_under_allowed_root"


def _write_image(path: Path, *, color: tuple[int, int, int], size: tuple[int, int] = (24, 16)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=color).save(path)
