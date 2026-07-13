import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from albumentationsx_mcp.models import ComposeSpec, PreviewRequest, PreviewResult, TransformSpec
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


@pytest.mark.parametrize("artifact_kind", ["image", "contact_sheet"])
def test_artifact_store_reads_verified_preview_images(tmp_path: Path, artifact_kind: str) -> None:
    store, result = _render_preview_fixture(tmp_path)
    artifact = next(item for item in result.artifacts if item.kind == artifact_kind)

    content = store.read_image_artifact(result.run_id, Path(artifact.path).name)

    assert content.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(content) == artifact.size_bytes


@pytest.mark.parametrize("filename", ["../input.png", "sub/input.png", "/outside/input.png", ".."])
def test_artifact_store_rejects_invalid_image_filenames(tmp_path: Path, filename: str) -> None:
    store, result = _render_preview_fixture(tmp_path)

    with pytest.raises(ValueError, match="Invalid artifact filename"):
        store.read_image_artifact(result.run_id, filename)


def test_artifact_store_rejects_unrecorded_image_artifacts(tmp_path: Path) -> None:
    store, result = _render_preview_fixture(tmp_path)

    with pytest.raises(FileNotFoundError, match="not recorded"):
        store.read_image_artifact(result.run_id, "unknown.png")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("kind", "manifest", "not a readable preview image"),
        ("mime_type", "application/json", "not a readable preview image"),
        ("path", "/outside/unrelated.png", "path does not match"),
        ("size_bytes", 1, "size does not match"),
        ("sha256", "0" * 64, "digest does not match"),
    ],
)
def test_artifact_store_rejects_tampered_image_manifest_entries(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    store, result = _render_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = next(item for item in manifest["artifacts"] if item["kind"] == "image")
    filename = Path(artifact["path"]).name
    artifact[field] = value
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        store.read_image_artifact(result.run_id, filename)


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
            pipeline=ComposeSpec(transforms=[TransformSpec(name="GaussNoise", p=1.0)], seed=20),
            variants_per_image=1,
            seed=20,
        ),
    )

    comparison = service.compare_preview_runs(baseline.run_id, candidate.run_id)

    assert comparison.baseline.run_id == baseline.run_id
    assert comparison.candidate.run_id == candidate.run_id
    assert comparison.pipeline_changed is True
    assert comparison.seed_changed is True
    assert comparison.review_guidance[0].feedback_tag == "too_noisy"
    assert comparison.review_guidance[0].suggested_action == "reduce_noise_intensity"


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


def _render_preview_fixture(tmp_path: Path) -> tuple[ArtifactStore, PreviewResult]:
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
    return store, result
