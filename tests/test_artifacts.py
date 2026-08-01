import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from albumentationsx_mcp import preview_trace
from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.models import ComposeSpec, PreviewRequest, PreviewResult, TransformSpec
from albumentationsx_mcp.pipeline import PipelineService
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
            pipeline=ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip", p=1.0)], seed=31),
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
    assert manifest["summary"]["variant_trace_count"] == 2
    assert [trace["effective_seed"] for trace in manifest["variant_traces"]] == [31, 31]
    assert all(trace["applied_transforms"] == [] for trace in manifest["variant_traces"])
    assert any(artifact["kind"] == "contact_sheet" for artifact in manifest["artifacts"])


def test_preview_rendering_records_ordered_applied_transform_traces_and_request_seeds(tmp_path: Path) -> None:
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"
    image = np.arange(16 * 16 * 3, dtype=np.uint8).reshape((16, 16, 3))
    Image.fromarray(image).save(first_path)
    Image.fromarray(np.flip(image, axis=1).copy()).save(second_path)
    store = ArtifactStore(tmp_path / "artifacts")
    service = PreviewService(PipelineService(TransformCatalog()), PathPolicy([tmp_path]), store)

    result = service.render_preview(
        PreviewRequest(
            input_paths=[first_path, second_path],
            pipeline=ComposeSpec(
                transforms=[
                    TransformSpec(name="HorizontalFlip", p=1.0),
                    TransformSpec(name="GaussNoise", params={"std_range": (0.01, 0.02)}, p=1.0),
                ],
                seed=900,
            ),
            variants_per_image=2,
            seed=23,
        ),
    )
    manifest = store.read_manifest(result.run_id)
    traces = manifest["variant_traces"]
    image_artifacts = [artifact for artifact in manifest["artifacts"] if artifact["kind"] == "image"]

    assert manifest["summary"]["variant_trace_count"] == 4
    assert [(trace["image_index"], trace["variant_index"]) for trace in traces] == [
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
    ]
    assert [trace["effective_seed"] for trace in traces] == [23, 24, 23, 24]
    assert [trace["source_path"] for trace in traces] == [
        str(first_path.resolve()),
        str(first_path.resolve()),
        str(second_path.resolve()),
        str(second_path.resolve()),
    ]
    assert [trace["artifact_uri"] for trace in traces] == [artifact["uri"] for artifact in image_artifacts]
    assert [item["name"] for item in traces[0]["applied_transforms"]] == [
        "HorizontalFlip",
        "GaussNoise",
    ]


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


@pytest.mark.parametrize("content", [b"not a PNG payload", b"\x89PNG\r\n\x1a\nbroken"])
def test_artifact_store_rejects_coherently_tampered_non_png_payload(tmp_path: Path, content: bytes) -> None:
    store, result = _render_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = next(item for item in manifest["artifacts"] if item["kind"] == "image")
    artifact_path = Path(artifact["path"])
    artifact_path.write_bytes(content)
    artifact["size_bytes"] = len(content)
    artifact["sha256"] = hashlib.sha256(content).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="valid PNG"):
        store.read_image_artifact(result.run_id, artifact_path.name)


def test_artifact_store_rejects_symlinked_image_payload(tmp_path: Path) -> None:
    store, result = _render_preview_fixture(tmp_path)
    artifact = next(item for item in result.artifacts if item.kind == "image")
    artifact_path = Path(artifact.path)
    replacement_path = artifact_path.with_name("replacement.png")
    replacement_path.write_bytes(artifact_path.read_bytes())
    artifact_path.unlink()
    _symlink_or_skip(artifact_path, replacement_path)

    with pytest.raises(ValueError, match="regular stored file"):
        store.read_image_artifact(result.run_id, artifact_path.name)


def test_artifact_store_rejects_symlinked_manifest(tmp_path: Path) -> None:
    store, result = _render_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    replacement_path = tmp_path / "replacement-manifest.json"
    replacement_path.write_bytes(manifest_path.read_bytes())
    manifest_path.unlink()
    _symlink_or_skip(manifest_path, replacement_path)

    with pytest.raises(ValueError, match="regular stored file"):
        store.read_manifest(result.run_id)


def test_artifact_store_rejects_symlinked_run_directory(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    run_id = "0" * 32
    outside_run = tmp_path / "outside-run"
    outside_run.mkdir()
    (outside_run / "manifest.json").write_text("{}", encoding="utf-8")
    _symlink_or_skip(store.root / run_id, outside_run, target_is_directory=True)

    with pytest.raises(ValueError, match="regular stored directory"):
        store.read_manifest(run_id)


def test_artifact_store_missing_manifest_error_does_not_disclose_root(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "private-artifacts")

    with pytest.raises(FileNotFoundError) as exc_info:
        store.read_manifest("0" * 32)

    assert str(store.root) not in str(exc_info.value)


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


def test_get_preview_variant_trace_returns_matching_trace(tmp_path: Path) -> None:
    store, result = _render_real_preview_fixture(tmp_path)

    lookup = preview_trace.get_preview_variant_trace(store, result.run_id, image_index=0, variant_index=0)

    assert lookup.available is True
    assert lookup.message == "Applied transform trace is available."
    assert lookup.trace is not None
    assert lookup.trace.artifact_uri == next(artifact.uri for artifact in result.artifacts if artifact.kind == "image")
    assert [item.name for item in lookup.trace.applied_transforms] == ["HorizontalFlip", "GaussNoise"]


def test_get_preview_variant_trace_returns_legacy_unavailable(tmp_path: Path) -> None:
    store, result = _render_real_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("variant_traces")
    manifest["summary"].pop("variant_trace_count")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    lookup = preview_trace.get_preview_variant_trace(store, result.run_id, image_index=0, variant_index=0)

    assert lookup.available is False
    assert lookup.trace is None
    assert lookup.message == "Variant traces are unavailable for this legacy preview run."


def test_get_preview_variant_trace_rejects_non_list_metadata_without_path_leak(tmp_path: Path) -> None:
    store, result = _render_real_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    private_path = str(tmp_path / "private" / "customer.png")
    manifest["variant_traces"] = {"source_path": private_path}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match=r"^Preview manifest variant_traces must be a list$") as exc_info:
        preview_trace.get_preview_variant_trace(store, result.run_id, image_index=0, variant_index=0)

    assert str(exc_info.value) == "Preview manifest variant_traces must be a list"
    assert private_path not in str(exc_info.value)
    assert str(store.root) not in str(exc_info.value)


def test_get_preview_variant_trace_rejects_non_object_manifest_root_without_path_leak(tmp_path: Path) -> None:
    store, result = _render_real_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    private_path = str(tmp_path / "private" / "customer.png")
    manifest_path.write_text(json.dumps([private_path]), encoding="utf-8")

    with pytest.raises(ValueError, match=r"^Preview trace manifest is malformed$") as exc_info:
        preview_trace.get_preview_variant_trace(store, result.run_id, image_index=0, variant_index=0)

    assert private_path not in str(exc_info.value)
    assert str(store.root) not in str(exc_info.value)


def test_get_preview_variant_trace_rejects_malformed_entry_without_path_leak(tmp_path: Path) -> None:
    store, result = _render_real_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    private_path = str(tmp_path / "private" / "customer.png")
    manifest["variant_traces"] = [
        {
            "image_index": 0,
            "variant_index": 0,
            "source_path": private_path,
        }
    ]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"^Preview manifest variant_traces contain malformed entries$",
    ) as exc_info:
        preview_trace.get_preview_variant_trace(store, result.run_id, image_index=0, variant_index=0)

    assert str(exc_info.value) == "Preview manifest variant_traces contain malformed entries"
    assert private_path not in str(exc_info.value)
    assert str(store.root) not in str(exc_info.value)


def test_get_preview_variant_trace_rejects_malformed_nonmatching_entry(tmp_path: Path) -> None:
    store, result = _render_real_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    private_path = str(tmp_path / "private" / "nonmatching.png")
    manifest["variant_traces"].append(
        {
            "image_index": 9,
            "variant_index": 9,
            "source_path": private_path,
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"^Preview manifest variant_traces contain malformed entries$",
    ) as exc_info:
        preview_trace.get_preview_variant_trace(store, result.run_id, image_index=0, variant_index=0)

    assert private_path not in str(exc_info.value)
    assert str(store.root) not in str(exc_info.value)


def test_get_preview_variant_trace_rejects_coercible_numeric_string_in_nonmatching_entry(tmp_path: Path) -> None:
    store, result = _render_real_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    nonmatching = dict(manifest["variant_traces"][0])
    nonmatching["image_index"] = "9"
    nonmatching["variant_index"] = 9
    manifest["variant_traces"].append(nonmatching)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"^Preview manifest variant_traces contain malformed entries$",
    ):
        preview_trace.get_preview_variant_trace(store, result.run_id, image_index=0, variant_index=0)


@pytest.mark.parametrize(
    ("target", "value"),
    [
        ("image_index", "0"),
        ("variant_index", False),
        ("effective_seed", "17"),
        ("truncated_transform_count", "0"),
        ("parameters_truncated", "false"),
        ("source_path", 7),
        ("artifact_uri", 7),
        ("transform_name", 7),
        ("applied_transforms", {}),
        ("transform_params", []),
    ],
    ids=[
        "numeric-image-string",
        "boolean-variant",
        "numeric-seed-string",
        "numeric-count-string",
        "boolean-string",
        "numeric-source-path",
        "numeric-artifact-uri",
        "numeric-transform-name",
        "mapping-transform-container",
        "sequence-params-container",
    ],
)
def test_get_preview_variant_trace_rejects_coercive_manifest_fields(
    tmp_path: Path,
    target: str,
    value: Any,
) -> None:
    store, result = _render_real_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    trace = manifest["variant_traces"][0]
    if target == "transform_name":
        trace["applied_transforms"][0]["name"] = value
    elif target == "transform_params":
        trace["applied_transforms"][0]["params"] = value
    else:
        trace[target] = value
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"^Preview manifest variant_traces contain malformed entries$",
    ):
        preview_trace.get_preview_variant_trace(store, result.run_id, image_index=0, variant_index=0)


@pytest.mark.parametrize(
    "target",
    ["applied_transforms", "truncated_transform_count"],
    ids=["too-many-applied-transforms", "oversized-truncated-count"],
)
def test_get_preview_variant_trace_rejects_out_of_bounds_trace_fields(tmp_path: Path, target: str) -> None:
    store, result = _render_real_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    trace = manifest["variant_traces"][0]
    if target == "applied_transforms":
        trace[target] = [
            {"name": f"Transform{index:02d}", "params": {}} for index in range(preview_trace.MAX_APPLIED_TRANSFORMS + 1)
        ]
    else:
        trace[target] = preview_trace.MAX_TRACE_INDEX + 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"^Preview manifest variant_traces contain malformed entries$",
    ) as exc_info:
        preview_trace.get_preview_variant_trace(store, result.run_id, image_index=0, variant_index=0)

    assert str(store.root) not in str(exc_info.value)


def test_get_preview_variant_trace_rejects_duplicate_matching_entries(tmp_path: Path) -> None:
    store, result = _render_real_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["variant_traces"].append(dict(manifest["variant_traces"][0]))
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"^Preview manifest contains multiple traces for the requested image and variant$",
    ) as exc_info:
        preview_trace.get_preview_variant_trace(store, result.run_id, image_index=0, variant_index=0)

    assert str(store.root) not in str(exc_info.value)


def test_get_preview_variant_trace_rejects_unknown_pair(tmp_path: Path) -> None:
    store, result = _render_real_preview_fixture(tmp_path)

    with pytest.raises(
        ValueError,
        match=r"^Preview variant trace is unavailable for image 2, variant 3$",
    ):
        preview_trace.get_preview_variant_trace(store, result.run_id, image_index=2, variant_index=3)


@pytest.mark.parametrize(("image_index", "variant_index"), [(-1, 0), (0, -1)])
def test_get_preview_variant_trace_rejects_negative_indexes_before_manifest_read(
    tmp_path: Path,
    image_index: int,
    variant_index: int,
) -> None:
    store = ArtifactStore(tmp_path / "private-artifacts")

    with pytest.raises(
        ValueError,
        match=r"^image_index and variant_index must be non-negative$",
    ):
        preview_trace.get_preview_variant_trace(
            store,
            "0" * 32,
            image_index=image_index,
            variant_index=variant_index,
        )


@pytest.mark.parametrize("field", ["image_index", "variant_index"])
@pytest.mark.parametrize(
    "invalid_value",
    ["0", 0.0, True, 10**5000],
    ids=["string", "float", "bool", "huge-int"],
)
def test_get_preview_variant_trace_rejects_invalid_index_types_before_manifest_read(
    tmp_path: Path,
    field: str,
    invalid_value: Any,
) -> None:
    store = ArtifactStore(tmp_path / "private-artifacts")
    expected_message = f"{field} must be an integer between 0 and {(1 << 63) - 1}"

    with pytest.raises(ValueError, match=re.escape(expected_message)) as exc_info:
        preview_trace.get_preview_variant_trace(
            store,
            "0" * 32,
            image_index=invalid_value if field == "image_index" else 0,
            variant_index=invalid_value if field == "variant_index" else 0,
        )

    assert str(exc_info.value) == expected_message
    assert str(store.root) not in str(exc_info.value)
    assert len(str(exc_info.value)) < 128


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


def _render_real_preview_fixture(tmp_path: Path) -> tuple[ArtifactStore, PreviewResult]:
    image_path = tmp_path / "input.png"
    image = np.arange(16 * 16 * 3, dtype=np.uint8).reshape((16, 16, 3))
    Image.fromarray(image).save(image_path)
    store = ArtifactStore(tmp_path / "artifacts")
    service = PreviewService(PipelineService(TransformCatalog()), PathPolicy([tmp_path]), store)
    result = service.render_preview(
        PreviewRequest(
            input_paths=[image_path],
            pipeline=ComposeSpec(
                transforms=[
                    TransformSpec(name="HorizontalFlip", p=1.0),
                    TransformSpec(name="GaussNoise", params={"std_range": (0.01, 0.02)}, p=1.0),
                ],
                seed=17,
            ),
            variants_per_image=1,
        ),
    )
    return store, result


def _symlink_or_skip(link: Path, target: Path, *, target_is_directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")
