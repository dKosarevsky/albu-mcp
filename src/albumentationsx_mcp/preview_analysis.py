"""Pure preview manifest summary and comparison logic."""

from __future__ import annotations

from collections import Counter
from typing import Any

from albumentationsx_mcp.feedback import suggested_feedback_tags_for_transform_names
from albumentationsx_mcp.models import PreviewManifestSummary, PreviewRunComparison

_CONTACT_SHEET_KINDS = {"contact_sheet", "overlay_contact_sheet"}


def summarize_preview_manifest(manifest: dict[str, Any]) -> PreviewManifestSummary:
    """Return an agent-legible summary for a preview manifest."""
    summary = manifest.get("summary")
    if isinstance(summary, dict):
        return PreviewManifestSummary.model_validate(
            {
                "run_id": manifest["run_id"],
                "created_at": manifest["created_at"],
                **summary,
            },
        )

    artifacts = list(manifest.get("artifacts", []))
    artifact_counts = Counter(str(artifact.get("kind", "unknown")) for artifact in artifacts)
    pipeline = dict(manifest.get("pipeline", {}))
    transforms = list(pipeline.get("transforms", []))
    contact_sheet_paths = [
        str(artifact["path"]) for artifact in artifacts if artifact.get("kind") in _CONTACT_SHEET_KINDS
    ]
    seed = pipeline.get("seed")
    return PreviewManifestSummary(
        run_id=str(manifest["run_id"]),
        created_at=str(manifest["created_at"]),
        input_count=len(manifest.get("inputs", [])),
        variants_per_image=None,
        seed=seed if isinstance(seed, int) else None,
        effective_seeds=[seed] if isinstance(seed, int) else [],
        max_side=None,
        transform_count=len(transforms),
        transform_names=[str(transform.get("name", "unknown")) for transform in transforms],
        artifact_counts=dict(artifact_counts),
        contact_sheet_paths=contact_sheet_paths,
        warnings=[],
    )


def compare_preview_manifests(
    baseline_manifest: dict[str, Any], candidate_manifest: dict[str, Any]
) -> PreviewRunComparison:
    """Compare two preview manifests for reproducibility and review planning."""
    baseline = summarize_preview_manifest(baseline_manifest)
    candidate = summarize_preview_manifest(candidate_manifest)
    pipeline_changed = baseline_manifest.get("pipeline") != candidate_manifest.get("pipeline")
    inputs_changed = baseline_manifest.get("inputs", []) != candidate_manifest.get("inputs", [])
    seed_changed = baseline.effective_seeds != candidate.effective_seeds
    artifact_count_delta = sum(candidate.artifact_counts.values()) - sum(baseline.artifact_counts.values())
    suggested_feedback_tags = suggested_feedback_tags_for_transform_names(
        candidate.transform_names,
        baseline.transform_names,
    )
    review_notes = ["Review both contact sheets", "Select structured feedback tags only after visual comparison."]
    if pipeline_changed:
        review_notes.append("Pipeline definitions differ; compare transform effects, not only artifact counts.")
    if inputs_changed:
        review_notes.append(
            "Input path sets differ; visual comparison may mix dataset changes with augmentation changes.",
        )
    if seed_changed:
        review_notes.append("Seed policy differs; reproduce any accepted variant with the candidate manifest seeds.")
    if artifact_count_delta != 0:
        review_notes.append(f"Candidate produced {artifact_count_delta:+d} artifacts relative to baseline.")
    if baseline.transform_names != candidate.transform_names:
        review_notes.append("Transform order or transform names changed between runs.")
    if suggested_feedback_tags:
        review_notes.append("Suggested feedback tags are review candidates, not an automatic verdict.")
    return PreviewRunComparison(
        baseline=baseline,
        candidate=candidate,
        pipeline_changed=pipeline_changed,
        inputs_changed=inputs_changed,
        seed_changed=seed_changed,
        artifact_count_delta=artifact_count_delta,
        review_notes=review_notes,
        suggested_feedback_tags=suggested_feedback_tags,
    )
