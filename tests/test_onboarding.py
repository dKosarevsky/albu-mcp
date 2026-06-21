import json
from pathlib import Path

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


def _write_image(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (16, 12), color=(80, 120, 160))
    image.save(path)
    return path
