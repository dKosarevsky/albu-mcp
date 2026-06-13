"""Prompt builders for common AlbumentationsX MCP workflows."""

from __future__ import annotations


def build_robustness_augmentation_session(task: str, targets: str = "image") -> str:
    """Guide preview-driven augmentation tuning for a robustness dataset pass."""
    return (
        "Use AlbumentationsX MCP to recommend a conservative pipeline for "
        f"{task} with targets {targets}. Validate it, explain likely preview risks, "
        "render a small deterministic preview set, ask the user for structured feedback tags, "
        "then adjust and re-render until the preview set is accepted. Keep the exported pipeline "
        "and manifest run id reproducible."
    )


def compare_preview_runs_for_feedback(baseline_run_id: str, candidate_run_id: str) -> str:
    """Guide an assistant through comparing two preview manifests."""
    return (
        "Compare two AlbumentationsX preview runs before changing the pipeline. "
        f"Use get_preview_manifest for baseline run {baseline_run_id} and candidate run {candidate_run_id}; "
        "inspect contact sheets and artifact counts, summarize what changed, then ask the user for one or more "
        "structured feedback tags before calling adjust_pipeline."
    )


def tune_pipeline_from_preview_feedback(task: str, run_id: str, feedback_tags: str) -> str:
    """Guide adjustment from a concrete preview run and user feedback tags."""
    return (
        f"For the {task} pipeline, read preview manifest {run_id}, preserve its reproducibility context, "
        f"apply feedback tags [{feedback_tags}] with adjust_pipeline, validate the adjusted pipeline, "
        "and render a new preview with the same input set and deterministic seed policy."
    )


def export_reproducible_pipeline(run_id: str, output_format: str = "python") -> str:
    """Guide final export after a preview run has been accepted."""
    return (
        f"Use get_preview_manifest for accepted run {run_id}, validate the manifest pipeline, "
        f"then call export_pipeline with output_format={output_format!r}. Include the run id, seed, "
        "and artifact manifest path in the final answer so the pipeline can be reproduced."
    )
