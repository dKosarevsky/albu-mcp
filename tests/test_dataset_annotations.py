import json
from pathlib import Path

from PIL import Image

from albumentationsx_mcp.dataset_annotations import build_sample_annotations


def test_build_sample_annotations_reads_coco_bboxes_for_sampled_images(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    image_path = _write_image(dataset_dir / "images/a.png", size=(40, 20))
    _write_image(dataset_dir / "images/b.png", size=(40, 20))
    annotations_dir = dataset_dir / "annotations"
    annotations_dir.mkdir()
    (annotations_dir / "instances_train.json").write_text(
        json.dumps(
            {
                "images": [
                    {"id": 1, "file_name": "images/a.png"},
                    {"id": 2, "file_name": "images/b.png"},
                ],
                "annotations": [
                    {"id": 1, "image_id": 1, "bbox": [2, 3, 10, 8], "category_id": 7},
                    {"id": 2, "image_id": 2, "bbox": [1, 1, 4, 4], "category_id": 8},
                ],
                "categories": [
                    {"id": 7, "name": "car"},
                    {"id": 8, "name": "person"},
                ],
            }
        ),
        encoding="utf-8",
    )

    annotation_set = build_sample_annotations(dataset_dir, [image_path])

    assert annotation_set is not None
    assert annotation_set.source_format == "coco"
    assert annotation_set.matched_count == 1
    assert annotation_set.annotations[0] is not None
    assert annotation_set.annotations[0].bboxes == [[2.0, 3.0, 12.0, 11.0]]
    assert annotation_set.annotations[0].bbox_labels == ["car"]


def test_build_sample_annotations_reads_yolo_bboxes_for_sampled_images(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    image_path = _write_image(dataset_dir / "images/a.png", size=(40, 20))
    labels_dir = dataset_dir / "labels"
    labels_dir.mkdir()
    (labels_dir / "a.txt").write_text("3 0.5 0.5 0.25 0.4\n", encoding="utf-8")

    annotation_set = build_sample_annotations(dataset_dir, [image_path])

    assert annotation_set is not None
    assert annotation_set.source_format == "yolo"
    assert annotation_set.matched_count == 1
    assert annotation_set.annotations[0] is not None
    assert annotation_set.annotations[0].bboxes == [[15.0, 6.0, 25.0, 14.0]]
    assert annotation_set.annotations[0].bbox_labels == [3]


def test_build_sample_annotations_preserves_input_count_when_some_labels_are_missing(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    annotated = _write_image(dataset_dir / "images/a.png", size=(40, 20))
    missing = _write_image(dataset_dir / "images/b.png", size=(40, 20))
    labels_dir = dataset_dir / "labels"
    labels_dir.mkdir()
    (labels_dir / "a.txt").write_text("1 0.5 0.5 0.5 0.5\n", encoding="utf-8")

    annotation_set = build_sample_annotations(dataset_dir, [annotated, missing])

    assert annotation_set is not None
    assert annotation_set.matched_count == 1
    assert len(annotation_set.annotations) == 2
    assert annotation_set.annotations[0] is not None
    assert annotation_set.annotations[1] is None
    assert any("without annotations" in warning for warning in annotation_set.warnings)


def _write_image(path: Path, *, size: tuple[int, int]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(80, 120, 160)).save(path)
    return path.resolve()
