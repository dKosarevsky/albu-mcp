import json
from pathlib import Path

import pytest
from PIL import Image

from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.onboarding import build_dataset_onboarding_report
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.preview import PathPolicy
from albumentationsx_mcp.recipes import recommend_recipe


def test_dataset_onboarding_report_samples_images_and_builds_preview_template(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    image_paths = [_write_image(dataset_dir / name) for name in ["b.png", "a.jpg", "nested/c.webp"]]
    (dataset_dir / "notes.txt").write_text("not an image", encoding="utf-8")

    report = build_dataset_onboarding_report(
        dataset_path=dataset_dir,
        task="classification",
        intensity="low",
        targets=["image"],
        max_images=2,
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert report.status == "ok"
    assert report.preview_ready is True
    assert report.image_count == 3
    assert report.sampled_image_count == 2
    assert report.ignored_file_count == 1
    assert report.recipe.recipe_name == "classification"
    assert report.validation.valid is True
    assert report.preview_request_template is not None
    assert report.preview_request_template.tool == "render_preview_batch"
    assert report.preview_request_template.request["input_paths"] == [
        str(image_paths[1].resolve()),
        str(image_paths[0].resolve()),
    ]
    assert report.preview_request_template.request["variants_per_image"] == 1
    assert report.preview_request_template.request["max_side"] == 512
    assert "validate_preview_request" in " ".join(report.next_actions)
    assert "render_preview_batch" in " ".join(report.next_actions)


def test_dataset_onboarding_report_blocks_empty_dataset(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()

    report = build_dataset_onboarding_report(
        dataset_path=dataset_dir,
        task="classification",
        intensity="low",
        targets=["image"],
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert report.status == "warning"
    assert report.preview_ready is False
    assert report.image_count == 0
    assert report.preview_request_template is None
    assert report.remediation_actions[0].code == "add_dataset_images"


@pytest.mark.parametrize("suffix", [".png", ".jpg", ".webp"])
def test_dataset_onboarding_report_accepts_one_supported_image(tmp_path: Path, suffix: str) -> None:
    image_path = _write_image(tmp_path / f"sample{suffix}")

    report = build_dataset_onboarding_report(
        dataset_path=image_path,
        task="classification",
        intensity="low",
        targets=["image"],
        max_images=8,
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert report.status == "ok"
    assert report.preview_ready is True
    assert report.dataset_path == str(image_path.resolve())
    assert report.image_count == 1
    assert report.sampled_image_count == 1
    assert report.ignored_file_count == 0
    assert report.sample_paths == [str(image_path.resolve())]
    assert report.checks[0].code == "dataset_path_accessible"
    assert report.checks[0].details["path_kind"] == "file"
    assert report.preview_request_template is not None
    assert report.preview_request_template.request["input_paths"] == [str(image_path.resolve())]


def test_dataset_onboarding_report_rejects_unsupported_file(tmp_path: Path) -> None:
    source_path = tmp_path / "notes.txt"
    source_path.write_text("not an image", encoding="utf-8")

    report = build_dataset_onboarding_report(
        dataset_path=source_path,
        task="classification",
        intensity="low",
        targets=["image"],
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert report.status == "error"
    assert report.preview_ready is False
    assert report.checks[0].code == "dataset_path_unsupported_file"
    assert report.checks[0].details["path_kind"] == "file"
    assert report.checks[0].details["supported_extensions"]
    assert report.remediation_actions[0].code == "fix_dataset_path"
    assert report.remediation_actions[0].check_codes == ["dataset_path_unsupported_file"]


def test_single_image_onboarding_uses_parent_for_annotation_context(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    image_path = _write_image(dataset_dir / "sample.png")
    annotations_dir = dataset_dir / "annotations"
    annotations_dir.mkdir()
    (annotations_dir / "instances.json").write_text(
        json.dumps(
            {
                "images": [{"id": 1, "file_name": "sample.png"}],
                "annotations": [{"id": 1, "image_id": 1, "bbox": [2, 3, 10, 8], "category_id": 7}],
                "categories": [{"id": 7, "name": "car"}],
            }
        ),
        encoding="utf-8",
    )

    report = build_dataset_onboarding_report(
        dataset_path=image_path,
        task="object_detection",
        intensity="low",
        targets=["image", "bboxes"],
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert report.preview_ready is True
    assert report.dataset_structure is not None
    assert "coco_manifest" in report.dataset_structure.detected_layouts
    assert report.preview_request_template is not None
    assert report.preview_request_template.request["annotations"] == [
        {"bboxes": [[2.0, 3.0, 12.0, 11.0]], "bbox_labels": ["car"]}
    ]


def test_dataset_onboarding_report_rejects_outside_allowed_root(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    dataset_dir = tmp_path / "outside"
    allowed_root.mkdir()
    dataset_dir.mkdir()
    _write_image(dataset_dir / "sample.png")

    report = build_dataset_onboarding_report(
        dataset_path=dataset_dir,
        task="classification",
        intensity="low",
        targets=["image"],
        path_policy=PathPolicy([allowed_root]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert report.status == "error"
    assert report.preview_ready is False
    assert report.checks[0].code == "dataset_path_outside_allowed_root"
    assert report.remediation_actions[0].code == "move_dataset_under_allowed_root"


def test_dataset_onboarding_report_detects_class_directories_and_splits(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    _write_image(dataset_dir / "train/cat/a.png")
    _write_image(dataset_dir / "train/dog/b.png")
    _write_image(dataset_dir / "val/cat/c.png")

    report = build_dataset_onboarding_report(
        dataset_path=dataset_dir,
        task="classification",
        intensity="low",
        targets=["image"],
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert report.preview_ready is True
    assert report.dataset_structure is not None
    assert "class_directories" in report.dataset_structure.detected_layouts
    assert "split_directories" in report.dataset_structure.detected_layouts
    assert {item.name: item.image_count for item in report.dataset_structure.class_directories} == {
        "cat": 2,
        "dog": 1,
    }
    assert {item.name: item.image_count for item in report.dataset_structure.splits} == {
        "train": 2,
        "val": 1,
    }
    assert any("class imbalance" in warning.lower() for warning in report.dataset_structure.balance_warnings)
    assert any("classification" in hint.lower() for hint in report.dataset_structure.recipe_hints)


def test_dataset_onboarding_report_detects_yolo_and_coco_annotations(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    _write_image(dataset_dir / "images/a.png")
    labels_dir = dataset_dir / "labels"
    labels_dir.mkdir(parents=True)
    (labels_dir / "a.txt").write_text("0 0.5 0.5 0.25 0.25\n", encoding="utf-8")
    annotations_dir = dataset_dir / "annotations"
    annotations_dir.mkdir()
    (annotations_dir / "instances_train.json").write_text(
        json.dumps(
            {
                "images": [{"id": 1, "file_name": "a.png"}],
                "annotations": [{"id": 1, "image_id": 1, "bbox": [1, 1, 4, 4], "category_id": 1}],
                "categories": [{"id": 1, "name": "object"}],
            }
        ),
        encoding="utf-8",
    )

    report = build_dataset_onboarding_report(
        dataset_path=dataset_dir,
        task="object_detection",
        intensity="low",
        targets=["image", "bboxes"],
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert report.preview_ready is True
    assert report.dataset_structure is not None
    assert "yolo_labels" in report.dataset_structure.detected_layouts
    assert "coco_manifest" in report.dataset_structure.detected_layouts
    assert {item.format for item in report.dataset_structure.annotation_formats} == {"coco", "yolo"}
    assert any("bbox" in hint.lower() or "detection" in hint.lower() for hint in report.dataset_structure.recipe_hints)
    assert report.review_brief[0] == "Preview-ready dataset: 1 sampled image out of 1 supported image."
    assert any("Detected layouts: coco_manifest, yolo_labels." in item for item in report.review_brief)
    assert any("Annotation formats: coco, yolo." in item for item in report.review_brief)
    assert any("Bounding boxes require bbox_params-compatible transforms" in item for item in report.review_brief)
    assert any("Validate preview_request_template.request before rendering." in item for item in report.review_brief)


def test_dataset_onboarding_report_builds_annotation_aware_preview_template(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    image_path = _write_image(dataset_dir / "images/a.png")
    annotations_dir = dataset_dir / "annotations"
    annotations_dir.mkdir()
    (annotations_dir / "instances_train.json").write_text(
        json.dumps(
            {
                "images": [{"id": 1, "file_name": "images/a.png"}],
                "annotations": [{"id": 1, "image_id": 1, "bbox": [2, 3, 10, 8], "category_id": 7}],
                "categories": [{"id": 7, "name": "car"}],
            }
        ),
        encoding="utf-8",
    )

    report = build_dataset_onboarding_report(
        dataset_path=dataset_dir,
        task="object_detection",
        intensity="low",
        targets=["image", "bboxes"],
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert report.preview_ready is True
    assert report.preview_request_template is not None
    request = report.preview_request_template.request
    assert request["input_paths"] == [str(image_path.resolve())]
    assert request["annotations"] == [{"bboxes": [[2.0, 3.0, 12.0, 11.0]], "bbox_labels": ["car"]}]
    assert request["pipeline"]["bbox_params"] == {"format": "pascal_voc", "label_fields": ["labels"]}
    assert any("overlay" in instruction.lower() for instruction in report.preview_request_template.instructions)


def test_dataset_onboarding_report_builds_segmentation_mask_preview_template(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    image_path = _write_image(dataset_dir / "images/a.png")
    annotations_dir = dataset_dir / "annotations"
    annotations_dir.mkdir()
    (annotations_dir / "instances_train.json").write_text(
        json.dumps(
            {
                "images": [{"id": 1, "file_name": "images/a.png"}],
                "annotations": [
                    {
                        "id": 1,
                        "image_id": 1,
                        "segmentation": [[2, 3, 12, 3, 12, 11, 2, 11]],
                        "category_id": 7,
                    }
                ],
                "categories": [{"id": 7, "name": "car"}],
            }
        ),
        encoding="utf-8",
    )

    report = build_dataset_onboarding_report(
        dataset_path=dataset_dir,
        task="segmentation",
        intensity="low",
        targets=["image", "mask"],
        path_policy=PathPolicy([tmp_path]),
        pipeline_service=PipelineService(TransformCatalog()),
        recipe_builder=recommend_recipe,
    )

    assert report.preview_ready is True
    assert report.preview_request_template is not None
    request = report.preview_request_template.request
    assert request["input_paths"] == [str(image_path.resolve())]
    assert request["annotations"] == [{"mask_polygons": [[[2.0, 3.0, 12.0, 3.0, 12.0, 11.0, 2.0, 11.0]]]}]
    assert "bbox_params" not in request["pipeline"]
    assert report.preview_request_template.annotation_summary == {
        "source_format": "coco",
        "sample_count": 1,
        "matched_count": 1,
        "missing_count": 0,
        "bbox_count": 1,
        "keypoint_count": 0,
        "mask_path_count": 0,
        "mask_polygon_count": 1,
        "mask_rle_count": 0,
        "compressed_rle_count": 0,
        "uncompressed_rle_count": 0,
        "mask_formats": ["polygons"],
        "warnings": [],
    }
    assert any("Masks require mask-aware review" in item for item in report.review_brief)
    assert any("Annotation formats: coco." in item for item in report.review_brief)
    assert any("mask" in instruction.lower() for instruction in report.preview_request_template.instructions)
    assert any("mask_polygons=1" in instruction for instruction in report.preview_request_template.instructions)


def _write_image(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (16, 12), color=(80, 120, 160))
    image.save(path)
    return path
