from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from albumentationsx_mcp.models import ComposeSpec, ImageAnnotations, PreviewRequest, TransformSpec
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
