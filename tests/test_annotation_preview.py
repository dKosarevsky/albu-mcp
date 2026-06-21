from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from albumentationsx_mcp.annotations import render_overlay
from albumentationsx_mcp.models import ComposeSpec, ImageAnnotations, MaskRLE, PreviewRequest, TransformSpec
from albumentationsx_mcp.preview import ArtifactStore, PathPolicy, PreviewService


class IdentityPipelineService:
    def build_pipeline(self, pipeline: ComposeSpec) -> Any:
        _ = pipeline

        def transform(**kwargs: Any) -> dict[str, Any]:
            return kwargs

        return transform


def test_render_preview_writes_overlay_artifacts_for_annotations(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    mask_path = tmp_path / "mask.png"
    Image.fromarray(np.full((32, 32, 3), 220, dtype=np.uint8)).save(image_path)
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[8:24, 8:24] = 255
    Image.fromarray(mask).save(mask_path)
    service = PreviewService(
        IdentityPipelineService(),
        PathPolicy([tmp_path]),
        ArtifactStore(tmp_path / "artifacts"),
    )
    request = PreviewRequest(
        input_paths=[image_path],
        annotations=[
            ImageAnnotations(
                bboxes=[[4, 5, 20, 24]],
                bbox_labels=["object"],
                keypoints=[[12, 14]],
                mask_path=mask_path,
            ),
        ],
        pipeline=ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)]),
        variants_per_image=2,
    )

    result = service.render_preview(request)

    overlays = [artifact for artifact in result.artifacts if artifact.kind == "overlay"]
    overlay_sheets = [artifact for artifact in result.artifacts if artifact.kind == "overlay_contact_sheet"]
    assert len(overlays) == 2
    assert len(overlay_sheets) == 1
    assert all(Path(artifact.path).exists() for artifact in [*overlays, *overlay_sheets])


def test_render_preview_records_annotation_observations(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    mask_path = tmp_path / "mask.png"
    Image.fromarray(np.full((32, 32, 3), 220, dtype=np.uint8)).save(image_path)
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[8:24, 8:24] = 255
    Image.fromarray(mask).save(mask_path)
    service = PreviewService(
        IdentityPipelineService(),
        PathPolicy([tmp_path]),
        ArtifactStore(tmp_path / "artifacts"),
    )
    request = PreviewRequest(
        input_paths=[image_path],
        annotations=[
            ImageAnnotations(
                bboxes=[[4, 5, 20, 24]],
                bbox_labels=["object"],
                keypoints=[[12, 14]],
                mask_path=mask_path,
            ),
        ],
        pipeline=ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)]),
        variants_per_image=1,
    )

    result = service.render_preview(request)
    manifest = service.artifact_store.read_manifest(result.run_id)

    assert manifest["summary"]["annotation_observation_count"] == 1
    assert manifest["annotation_observations"] == [
        {
            "image_index": 0,
            "variant_index": 0,
            "input_bbox_count": 1,
            "output_bbox_count": 1,
            "input_keypoint_count": 1,
            "output_keypoint_count": 1,
            "input_mask_coverage": 0.25,
            "output_mask_coverage": 0.25,
        }
    ]


def test_render_preview_rasterizes_polygon_masks_for_overlay_observations(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.fromarray(np.full((32, 32, 3), 220, dtype=np.uint8)).save(image_path)
    service = PreviewService(
        IdentityPipelineService(),
        PathPolicy([tmp_path]),
        ArtifactStore(tmp_path / "artifacts"),
    )
    request = PreviewRequest(
        input_paths=[image_path],
        annotations=[
            ImageAnnotations(
                bboxes=[[8, 8, 24, 24]],
                bbox_labels=["object"],
                mask_polygons=[[[8, 8, 24, 8, 24, 24, 8, 24]]],
            ),
        ],
        pipeline=ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)]),
        variants_per_image=1,
    )

    result = service.render_preview(request)
    manifest = service.artifact_store.read_manifest(result.run_id)

    assert any(artifact.kind == "overlay_contact_sheet" for artifact in result.artifacts)
    assert manifest["annotation_observations"][0]["input_mask_coverage"] > 0.2
    assert manifest["annotation_observations"][0]["output_mask_coverage"] > 0.2


def test_render_preview_decodes_compressed_rle_masks_for_overlay_observations(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.fromarray(np.full((4, 4, 3), 220, dtype=np.uint8)).save(image_path)
    service = PreviewService(
        IdentityPipelineService(),
        PathPolicy([tmp_path]),
        ArtifactStore(tmp_path / "artifacts"),
    )
    request = PreviewRequest(
        input_paths=[image_path],
        annotations=[
            ImageAnnotations(
                bbox_labels=["object"],
                mask_rles=[MaskRLE(counts="52203", size=[4, 4])],
            ),
        ],
        pipeline=ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)]),
        variants_per_image=1,
    )

    result = service.render_preview(request)
    manifest = service.artifact_store.read_manifest(result.run_id)

    assert any(artifact.kind == "overlay_contact_sheet" for artifact in result.artifacts)
    assert manifest["annotation_observations"][0]["input_mask_coverage"] == 0.25
    assert manifest["annotation_observations"][0]["output_mask_coverage"] == 0.25


def test_preview_request_requires_annotation_count_to_match_inputs(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.fromarray(np.full((16, 16, 3), 128, dtype=np.uint8)).save(image_path)
    service = PreviewService(
        IdentityPipelineService(),
        PathPolicy([tmp_path]),
        ArtifactStore(tmp_path / "artifacts"),
    )
    request = PreviewRequest(
        input_paths=[image_path],
        annotations=[ImageAnnotations(), ImageAnnotations()],
        pipeline=ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)]),
    )

    with pytest.raises(ValueError, match="annotations length must match input_paths length"):
        service.render_preview(request)


def test_render_overlay_accepts_numpy_bbox_arrays() -> None:
    image = np.full((24, 24, 3), 200, dtype=np.uint8)

    overlay = render_overlay(
        {
            "image": image,
            "bboxes": np.asarray([[4.0, 5.0, 18.0, 19.0]], dtype=np.float32),
            "labels": np.asarray(["object"]),
        }
    )

    assert overlay.mode == "RGB"
    assert overlay.size == (24, 24)
