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


class BrightnessPipelineService:
    def build_pipeline(self, pipeline: ComposeSpec) -> Any:
        should_brighten = any(transform.name == "Brighten" for transform in pipeline.transforms)

        def transform(**kwargs: Any) -> dict[str, Any]:
            if not should_brighten:
                return kwargs
            image = kwargs["image"]
            return {**kwargs, "image": np.clip(image + 60, 0, 255).astype(np.uint8)}

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
    assert manifest["summary"]["input_count"] == 1
    assert manifest["summary"]["variants_per_image"] == 2
    assert manifest["summary"]["transform_names"] == ["HorizontalFlip"]
    assert manifest["summary"]["artifact_counts"]["image"] == 2
    assert any(artifact["kind"] == "contact_sheet" for artifact in manifest["artifacts"])


def test_preview_rendering_cleans_up_unindexed_run_dir_on_path_failure(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside" / "input.png"
    allowed.mkdir()
    outside.parent.mkdir(parents=True)
    Image.fromarray(np.full((16, 16, 3), 128, dtype=np.uint8)).save(outside)
    store = ArtifactStore(tmp_path / "artifacts")
    service = PreviewService(IdentityPipelineService(), PathPolicy([allowed]), store)

    with pytest.raises(ValueError, match="outside allowed roots"):
        service.render_preview(
            PreviewRequest(
                input_paths=[outside],
                pipeline=ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)]),
            ),
        )

    assert store.list_runs() == []
    expected_artifacts = ["index.json"] if store.index_path.exists() else []
    assert [path.name for path in store.root.iterdir()] == expected_artifacts


def test_artifact_store_rejects_manifest_path_traversal(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")

    with pytest.raises(ValueError, match="Invalid preview run id"):
        store.read_manifest("../outside")


def test_artifact_store_can_delete_preview_run_and_update_index(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.fromarray(np.full((16, 16, 3), 128, dtype=np.uint8)).save(image_path)
    store = ArtifactStore(tmp_path / "artifacts")
    service = PreviewService(IdentityPipelineService(), PathPolicy([tmp_path]), store)
    result = service.render_preview(
        PreviewRequest(
            input_paths=[image_path],
            pipeline=ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)]),
        ),
    )

    deleted = store.delete_run(result.run_id)

    assert deleted.run_id == result.run_id
    assert not Path(deleted.manifest_path).parent.exists()
    assert store.list_runs() == []


def test_artifact_store_prunes_runs_beyond_retention_limit(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.fromarray(np.full((16, 16, 3), 128, dtype=np.uint8)).save(image_path)
    store = ArtifactStore(tmp_path / "artifacts", max_runs=1)
    service = PreviewService(IdentityPipelineService(), PathPolicy([tmp_path]), store)

    first = service.render_preview(
        PreviewRequest(
            input_paths=[image_path],
            pipeline=ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)]),
        ),
    )
    second = service.render_preview(
        PreviewRequest(
            input_paths=[image_path],
            pipeline=ComposeSpec(transforms=[TransformSpec(name="VerticalFlip", p=1.0)]),
        ),
    )

    runs = store.list_runs()
    assert [run.run_id for run in runs] == [second.run_id]
    assert not (store.root / first.run_id).exists()


def test_preview_service_compares_two_recorded_runs(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.fromarray(np.full((16, 16, 3), 128, dtype=np.uint8)).save(image_path)
    store = ArtifactStore(tmp_path / "artifacts")
    service = PreviewService(IdentityPipelineService(), PathPolicy([tmp_path]), store)
    baseline = service.render_preview(
        PreviewRequest(
            input_paths=[image_path],
            pipeline=ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)], seed=10),
            variants_per_image=1,
            seed=10,
        ),
    )
    candidate = service.render_preview(
        PreviewRequest(
            input_paths=[image_path],
            pipeline=ComposeSpec(transforms=[TransformSpec(name="VerticalFlip", p=1.0)], seed=20),
            variants_per_image=1,
            seed=20,
        ),
    )

    comparison = service.compare_preview_runs(baseline.run_id, candidate.run_id)

    assert comparison.baseline.run_id == baseline.run_id
    assert comparison.candidate.run_id == candidate.run_id
    assert comparison.pipeline_changed is True
    assert comparison.seed_changed is True


def test_preview_service_compare_includes_quality_summary(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.fromarray(np.full((16, 16, 3), 80, dtype=np.uint8)).save(image_path)
    store = ArtifactStore(tmp_path / "artifacts")
    service = PreviewService(BrightnessPipelineService(), PathPolicy([tmp_path]), store)
    baseline = service.render_preview(
        PreviewRequest(
            input_paths=[image_path],
            pipeline=ComposeSpec(transforms=[TransformSpec(name="Identity", p=1.0)], seed=10),
            variants_per_image=1,
            seed=10,
        ),
    )
    candidate = service.render_preview(
        PreviewRequest(
            input_paths=[image_path],
            pipeline=ComposeSpec(transforms=[TransformSpec(name="Brighten", p=1.0)], seed=10),
            variants_per_image=1,
            seed=10,
        ),
    )

    comparison = service.compare_preview_runs(baseline.run_id, candidate.run_id)

    assert comparison.quality_summary is not None
    assert comparison.quality_summary.baseline.image_count == 1
    assert comparison.quality_summary.candidate.image_count == 1
    assert comparison.quality_summary.deltas["brightness_mean"] == 60.0
    assert comparison.quality_warnings == []
