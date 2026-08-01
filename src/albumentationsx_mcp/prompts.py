"""Prompt builders for common AlbumentationsX MCP workflows."""

from __future__ import annotations

from collections.abc import Collection

_DEFAULT_FIRST_PREVIEW_TOOLS = frozenset(
    {
        "adjust_pipeline",
        "compare_preview_runs",
        "export_pipeline",
        "render_preview_batch",
        "run_first_preview",
        "run_host_smoke_check",
        "trace_preview_variant",
        "validate_preview_request",
    }
)


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


def run_first_preview_review(
    task: str = "classification",
    input_path: str = "/absolute/path/to/images/sample.jpg",
    targets: str = "image",
    *,
    available_tools: Collection[str] | None = None,
) -> str:
    """Guide an assistant through the active profile's first-preview path."""
    tools = _DEFAULT_FIRST_PREVIEW_TOOLS if available_tools is None else frozenset(available_tools)
    parts = [
        "Use AlbumentationsX MCP to run the first local preview safely. "
        "Read albumentationsx://examples/client-smoke when the host exposes resource reads; if resource reads are "
        'unavailable, call get_workflow_example with example_id="client-smoke". Then call run_host_smoke_check '
        f"for task {task!r} with targets {targets!r}. Continue only when preview_ready is true. "
    ]
    if "run_first_preview" in tools:
        parts.append(
            "Call run_first_preview with "
            f"dataset_path={input_path!r}, task={task!r}, intensity='low', targets={targets!r}, and max_images=8. "
            "Show the returned contact sheet. "
        )
    elif {"validate_preview_request", "render_preview_batch"} <= tools:
        parts.append(
            "Copy preview_request_template.request, replace its input_paths value with "
            f"{input_path!r}, call validate_preview_request, and call render_preview_batch only when "
            "the validation report has valid=true. Show the contact sheet. "
        )
    else:
        parts.append("Follow the smoke report's remediation actions before attempting a local preview. ")

    if "trace_preview_variant" in tools:
        parts.append(
            "When the user selects a contact sheet result, call trace_preview_variant with the returned run id and "
            "zero-based image_index and variant_index before adjusting the pipeline. "
        )
    if "adjust_pipeline" in tools:
        parts.append(
            "After trace evidence and human feedback are available, call adjust_pipeline and render a candidate. "
        )
    if "compare_preview_runs" in tools:
        parts.append("Call compare_preview_runs before asking the user to accept the candidate. ")
    if "export_pipeline" in tools:
        parts.append("Call export_pipeline only after the user accepts the comparison.")
    return "".join(parts)


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
