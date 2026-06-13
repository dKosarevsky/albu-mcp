import numpy as np

from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.models import TargetSpec
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.presets import recommend_pipeline


def test_recommended_classification_pipeline_validates_and_runs_with_real_albumentationsx() -> None:
    service = PipelineService(TransformCatalog())
    spec = recommend_pipeline(task="classification", intensity="low", targets=["image"])

    report = service.validate_pipeline(spec, TargetSpec(targets=["image"]))
    transform = service.build_pipeline(spec)
    result = transform(image=np.full((32, 32, 3), 127, dtype=np.uint8))

    assert report.valid
    assert result["image"].shape == (32, 32, 3)


def test_recommended_task_presets_validate_against_real_catalog() -> None:
    service = PipelineService(TransformCatalog())

    for task, targets in [
        ("classification", ["image"]),
        ("object_detection", ["image", "bboxes"]),
        ("segmentation", ["image", "mask"]),
        ("ocr", ["image"]),
    ]:
        spec = recommend_pipeline(task=task, intensity="medium", targets=targets)
        report = service.validate_pipeline(spec, TargetSpec(targets=targets))

        assert report.valid, f"{task}: {report.errors}"
