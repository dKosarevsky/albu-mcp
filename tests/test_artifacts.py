from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from albumentationsx_mcp.models import ComposeSpec, PreviewRequest, TransformSpec
from albumentationsx_mcp.preview import ArtifactStore, PathPolicy, PreviewService


class IdentityPipelineService:
    def build_pipeline(self, pipeline: ComposeSpec) -> Any:
        _ = pipeline

        def transform(**kwargs: Any) -> dict[str, Any]:
            return kwargs

        return transform


def test_preview_rendering_records_queryable_run_index(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.fromarray(np.full((16, 16, 3), 128, dtype=np.uint8)).save(image_path)
    store = ArtifactStore(tmp_path / "artifacts")
    service = PreviewService(IdentityPipelineService(), PathPolicy([tmp_path]), store)

    result = service.render_preview(
        PreviewRequest(
            input_paths=[image_path],
            pipeline=ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)]),
            variants_per_image=2,
        ),
    )

    runs = store.list_runs()
    manifest = store.read_manifest(result.run_id)

    assert runs[0].run_id == result.run_id
    assert runs[0].artifact_count == len(result.artifacts)
    assert runs[0].input_count == 1
    assert manifest["run_id"] == result.run_id
    assert any(artifact["kind"] == "contact_sheet" for artifact in manifest["artifacts"])


def test_artifact_store_rejects_manifest_path_traversal(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")

    with pytest.raises(ValueError, match="Invalid preview run id"):
        store.read_manifest("../outside")
