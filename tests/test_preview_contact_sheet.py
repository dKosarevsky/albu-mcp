from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from albumentationsx_mcp.models import ComposeSpec, PreviewRequest, TransformSpec
from albumentationsx_mcp.preview import ArtifactStore, PathPolicy, PreviewService


class IdentityPipelineService:
    def build_pipeline(self, pipeline: ComposeSpec) -> Any:
        _ = pipeline

        def transform(**kwargs: Any) -> dict[str, Any]:
            return kwargs

        return transform


def test_render_preview_writes_contact_sheet_artifact(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.fromarray(np.full((16, 16, 3), 128, dtype=np.uint8)).save(image_path)
    service = PreviewService(
        IdentityPipelineService(),
        PathPolicy([tmp_path]),
        ArtifactStore(tmp_path / "artifacts"),
    )
    request = PreviewRequest(
        input_paths=[image_path],
        pipeline=ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)]),
        variants_per_image=3,
    )

    result = service.render_preview(request)

    contact_sheets = [artifact for artifact in result.artifacts if artifact.kind == "contact_sheet"]
    assert len(contact_sheets) == 1
    assert Path(contact_sheets[0].path).exists()
    assert contact_sheets[0].mime_type == "image/png"
