import pytest
from pydantic import ValidationError

from albumentationsx_mcp import models, preview_trace
from albumentationsx_mcp.preview_analysis import compare_preview_manifests, summarize_preview_manifest


def preview_manifest(*, run_id: str, transform_name: str, seed: int | None = None) -> dict:
    return {
        "run_id": run_id,
        "created_at": "2026-06-13T12:00:00Z",
        "inputs": ["/images/example.png"],
        "pipeline": {
            "transforms": [{"name": transform_name, "p": 1.0}],
            "seed": seed,
        },
        "summary": {
            "input_count": 1,
            "variants_per_image": 2,
            "seed": seed,
            "effective_seeds": [seed, seed + 1] if seed is not None else [],
            "max_side": 128,
            "transform_count": 1,
            "transform_names": [transform_name],
            "artifact_counts": {"image": 2, "contact_sheet": 1},
            "contact_sheet_paths": [f"/artifacts/{run_id}/contact_sheet.png"],
            "warnings": [],
            "variant_trace_count": 2,
        },
        "artifacts": [
            {"kind": "image", "path": f"/artifacts/{run_id}/000-000.png"},
            {"kind": "image", "path": f"/artifacts/{run_id}/000-001.png"},
            {"kind": "contact_sheet", "path": f"/artifacts/{run_id}/contact_sheet.png"},
        ],
    }


def test_preview_manifest_summary_is_agent_legible() -> None:
    summary = summarize_preview_manifest(preview_manifest(run_id="baseline", transform_name="HorizontalFlip", seed=10))

    assert summary.run_id == "baseline"
    assert summary.input_count == 1
    assert summary.variants_per_image == 2
    assert summary.effective_seeds == [10, 11]
    assert summary.transform_names == ["HorizontalFlip"]
    assert summary.artifact_counts == {"image": 2, "contact_sheet": 1}
    assert summary.contact_sheet_paths == ["/artifacts/baseline/contact_sheet.png"]
    assert summary.variant_trace_count == 2


def test_preview_manifest_summary_defaults_legacy_variant_trace_count_to_zero() -> None:
    manifest = preview_manifest(run_id="legacy", transform_name="HorizontalFlip", seed=10)
    manifest["summary"].pop("variant_trace_count")

    summary = summarize_preview_manifest(manifest)

    assert summary.variant_trace_count == 0


@pytest.mark.parametrize("value", [True, "1", 1.0], ids=["boolean", "string", "float"])
def test_preview_manifest_summary_rejects_coercive_variant_trace_count(value: object) -> None:
    manifest = preview_manifest(run_id="invalid", transform_name="HorizontalFlip", seed=10)
    manifest["summary"]["variant_trace_count"] = value

    with pytest.raises(ValidationError):
        summarize_preview_manifest(manifest)


def test_preview_manifest_summary_accepts_signed64_variant_trace_count_boundary() -> None:
    manifest = preview_manifest(run_id="boundary", transform_name="HorizontalFlip", seed=10)
    manifest["summary"]["variant_trace_count"] = (1 << 63) - 1

    summary = summarize_preview_manifest(manifest)

    assert summary.variant_trace_count == (1 << 63) - 1


def test_preview_trace_uses_shared_signed64_bound() -> None:
    assert models.MAX_SIGNED_64 == (1 << 63) - 1
    assert preview_trace.MAX_TRACE_INDEX == models.MAX_SIGNED_64


def test_compare_preview_manifests_reports_reproducibility_differences() -> None:
    comparison = compare_preview_manifests(
        preview_manifest(run_id="baseline", transform_name="HorizontalFlip", seed=10),
        preview_manifest(run_id="candidate", transform_name="GaussNoise", seed=20),
    )

    assert comparison.baseline.run_id == "baseline"
    assert comparison.candidate.run_id == "candidate"
    assert comparison.pipeline_changed is True
    assert comparison.seed_changed is True
    assert comparison.inputs_changed is False
    assert comparison.artifact_count_delta == 0
    assert "Review both contact sheets" in comparison.review_notes


def test_compare_preview_manifests_suggests_feedback_tags_for_candidate_transforms() -> None:
    comparison = compare_preview_manifests(
        preview_manifest(run_id="baseline", transform_name="HorizontalFlip", seed=10),
        preview_manifest(run_id="candidate", transform_name="GaussNoise", seed=10),
    )

    assert comparison.suggested_feedback_tags == ["too_noisy"]
    assert any("Suggested feedback tags are review candidates" in note for note in comparison.review_notes)
    assert comparison.review_guidance[0].feedback_tag == "too_noisy"
    assert comparison.review_guidance[0].suggested_action == "reduce_noise_intensity"
    assert "speckle" in comparison.review_guidance[0].review_focus
