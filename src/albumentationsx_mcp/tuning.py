"""Preview tuning session summaries."""

from __future__ import annotations

from typing import Literal

from albumentationsx_mcp.models import PreviewRunComparison, TuningSessionSummary

NextTuningTool = Literal["list_feedback_tags", "adjust_pipeline", "render_preview_batch", "export_pipeline"]


def build_tuning_session_summary(
    comparison: PreviewRunComparison,
    *,
    feedback_tags: list[str],
    accepted: bool = False,
) -> TuningSessionSummary:
    """Build an agent-facing summary for one preview tuning comparison."""
    export_ready = accepted and not comparison.inputs_changed
    next_tool, rationale = _next_tool_and_rationale(comparison, feedback_tags=feedback_tags, export_ready=export_ready)
    return TuningSessionSummary(
        baseline_run_id=comparison.baseline.run_id,
        candidate_run_id=comparison.candidate.run_id,
        feedback_tags=feedback_tags,
        accepted=accepted,
        export_ready=export_ready,
        recommended_next_tool=next_tool,
        rationale=rationale,
        suggested_feedback_tags=comparison.suggested_feedback_tags,
        quality_deltas=comparison.quality_summary.deltas if comparison.quality_summary else {},
        review_notes=[*comparison.review_notes, *comparison.quality_warnings],
    )


def _next_tool_and_rationale(
    comparison: PreviewRunComparison,
    *,
    feedback_tags: list[str],
    export_ready: bool,
) -> tuple[NextTuningTool, str]:
    if comparison.inputs_changed:
        return "render_preview_batch", "Re-render the candidate with the same inputs before deciding."
    if export_ready:
        return "export_pipeline", "The candidate is accepted and used the same inputs, so export is ready."
    if feedback_tags:
        return "adjust_pipeline", "Apply the selected feedback tags, validate, and render another candidate."
    return "list_feedback_tags", "Ask the user which suggested feedback tags match the reviewed contact sheets."
