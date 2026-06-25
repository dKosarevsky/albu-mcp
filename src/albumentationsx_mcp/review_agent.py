"""Review Agent workflow planning for preview-driven augmentation tuning."""

from __future__ import annotations

from typing import Literal

from albumentationsx_mcp.models import PreviewRunComparison, ReviewAgentPlan, TuningSessionSummary
from albumentationsx_mcp.tuning import build_tuning_session_summary

ReviewDecision = Literal["collect_feedback", "revise_candidate", "rerender_candidate", "accept_candidate"]


def build_review_agent_plan(
    comparison: PreviewRunComparison,
    *,
    feedback_tags: list[str],
    accepted: bool = False,
) -> ReviewAgentPlan:
    """Build a host-facing review workflow plan from comparison and user feedback."""
    tuning_summary = build_tuning_session_summary(comparison, feedback_tags=feedback_tags, accepted=accepted)
    decision = _decision(tuning_summary)
    return ReviewAgentPlan(
        baseline_run_id=tuning_summary.baseline_run_id,
        candidate_run_id=tuning_summary.candidate_run_id,
        decision=decision,
        accepted=accepted,
        feedback_tags=feedback_tags,
        recommended_next_tool=_recommended_next_tool(decision),
        rationale=tuning_summary.rationale,
        review_checklist=_review_checklist(comparison),
        blockers=_blockers(decision),
        next_actions=_next_actions(decision),
        suggested_feedback_tags=tuning_summary.suggested_feedback_tags,
        quality_deltas=tuning_summary.quality_deltas,
        quality_score=tuning_summary.quality_score,
        quality_risk=tuning_summary.quality_risk,
        tuning_summary=tuning_summary,
    )


def _decision(summary: TuningSessionSummary) -> ReviewDecision:
    if summary.recommended_next_tool == "render_preview_batch":
        return "rerender_candidate"
    if summary.export_ready:
        return "accept_candidate"
    if summary.feedback_tags:
        return "revise_candidate"
    return "collect_feedback"


def _recommended_next_tool(
    decision: ReviewDecision,
) -> Literal["list_feedback_tags", "adjust_pipeline", "render_preview_batch", "record_tuning_decision"]:
    if decision == "rerender_candidate":
        return "render_preview_batch"
    if decision == "accept_candidate":
        return "record_tuning_decision"
    if decision == "revise_candidate":
        return "adjust_pipeline"
    return "list_feedback_tags"


def _review_checklist(comparison: PreviewRunComparison) -> list[str]:
    checklist = [
        "Open the baseline and candidate contact sheets side by side.",
        "Confirm the candidate preserves label and object readability before accepting.",
    ]
    checklist.extend(f"{guidance.feedback_tag}: {guidance.review_focus}" for guidance in comparison.review_guidance)
    if comparison.suggested_feedback_tags:
        checklist.append(
            "Ask the user which suggested feedback tags apply: " + ", ".join(comparison.suggested_feedback_tags) + "."
        )
    return checklist


def _blockers(decision: ReviewDecision) -> list[str]:
    if decision == "rerender_candidate":
        return ["candidate_inputs_changed"]
    return []


def _next_actions(decision: ReviewDecision) -> list[str]:
    if decision == "rerender_candidate":
        return ["Re-render the candidate with the same input paths before deciding."]
    if decision == "accept_candidate":
        return [
            "Record the accepted candidate with record_tuning_decision for local audit.",
            "Export the accepted pipeline with export_pipeline.",
        ]
    if decision == "revise_candidate":
        return [
            "Apply the selected feedback tags with adjust_pipeline.",
            "Render the adjusted candidate with render_preview_batch.",
        ]
    return ["Call list_feedback_tags and ask the user to choose concrete structured feedback tags."]
