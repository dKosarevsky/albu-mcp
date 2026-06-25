"""Review Agent workflow planning for preview-driven augmentation tuning."""

from __future__ import annotations

import re
from typing import Literal

from albumentationsx_mcp.models import (
    PreviewRunComparison,
    ReviewAgentPlan,
    ReviewFeedbackInterpretation,
    ReviewFeedbackSignal,
    TuningSessionSummary,
)
from albumentationsx_mcp.tuning import build_tuning_session_summary

ReviewDecision = Literal["collect_feedback", "revise_candidate", "rerender_candidate", "accept_candidate"]

_ACCEPTANCE_PATTERNS = (
    "looks good",
    "look good",
    "acceptable",
    "accepted",
    "ship it",
    "great",
    "thanks",
)
_HIGH_SEVERITY_PATTERNS = (
    "can't",
    "cannot",
    "cant",
    "unrecognizable",
    "unreadable",
    "illegible",
    "barely",
    "too ",
)
_LOW_SEVERITY_PATTERNS = ("maybe", "slightly", "a bit", "bit ", "minor")
_SIGNAL_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("too_noisy", ("noise", "noisy", "speckle", "speckled", "grain", "grainy")),
    ("too_blurry", ("blur", "blurry", "soft", "smeared")),
    ("too_distorted", ("distort", "distorted", "skew", "skewed", "warp", "warped", "bent")),
    (
        "object_unrecognizable",
        ("unrecognizable", "can't recognize", "cannot recognize", "cant recognize", "can't see", "cannot see"),
    ),
)


def build_review_agent_plan(
    comparison: PreviewRunComparison,
    *,
    feedback_tags: list[str],
    feedback_note: str | None = None,
    accepted: bool = False,
) -> ReviewAgentPlan:
    """Build a host-facing review workflow plan from comparison and user feedback."""
    interpreted = interpret_preview_feedback(feedback_note or "")
    effective_feedback_tags = feedback_tags or interpreted.feedback_tags
    effective_accepted = accepted or (interpreted.accepted and not effective_feedback_tags)
    tuning_summary = build_tuning_session_summary(
        comparison,
        feedback_tags=effective_feedback_tags,
        accepted=effective_accepted,
    )
    decision = _decision(tuning_summary)
    return ReviewAgentPlan(
        baseline_run_id=tuning_summary.baseline_run_id,
        candidate_run_id=tuning_summary.candidate_run_id,
        decision=decision,
        accepted=effective_accepted,
        feedback_tags=effective_feedback_tags,
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


def interpret_preview_feedback(feedback_note: str) -> ReviewFeedbackInterpretation:
    """Convert free-form preview feedback into deterministic structured tags."""
    normalized = _normalize_note(feedback_note)
    signals = [
        ReviewFeedbackSignal(
            feedback_tag=feedback_tag,
            severity=_severity(normalized),
            evidence=_signal_evidence(feedback_tag, normalized),
        )
        for feedback_tag, tokens in _SIGNAL_RULES
        if _matches_signal(feedback_tag, tokens, normalized)
    ]
    feedback_tags = [f"{signal.feedback_tag}:{signal.severity}" for signal in signals]
    accepted = bool(normalized) and not signals and any(pattern in normalized for pattern in _ACCEPTANCE_PATTERNS)
    if feedback_tags:
        decision_hint: Literal["accept", "revise", "clarify"] = "revise"
        recommended_next_tool: Literal["record_tuning_decision", "adjust_pipeline", "list_feedback_tags"] = (
            "adjust_pipeline"
        )
    elif accepted:
        decision_hint = "accept"
        recommended_next_tool = "record_tuning_decision"
    else:
        decision_hint = "clarify"
        recommended_next_tool = "list_feedback_tags"
    return ReviewFeedbackInterpretation(
        feedback_note=feedback_note,
        accepted=accepted,
        feedback_tags=feedback_tags,
        signals=signals,
        decision_hint=decision_hint,
        recommended_next_tool=recommended_next_tool,
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


def _normalize_note(feedback_note: str) -> str:
    return re.sub(r"\s+", " ", feedback_note.strip().lower())


def _severity(normalized_note: str) -> Literal["low", "medium", "high"]:
    if any(pattern in normalized_note for pattern in _HIGH_SEVERITY_PATTERNS):
        return "high"
    if any(pattern in normalized_note for pattern in _LOW_SEVERITY_PATTERNS):
        return "low"
    return "medium"


def _matches_signal(feedback_tag: str, tokens: tuple[str, ...], normalized_note: str) -> bool:
    if any(token in normalized_note for token in tokens):
        return True
    if feedback_tag == "object_unrecognizable" and "recognize" in normalized_note:
        return any(pattern in normalized_note for pattern in ("can't", "cannot", "cant"))
    return False


def _signal_evidence(feedback_tag: str, normalized_note: str) -> str:
    if not normalized_note:
        return feedback_tag
    return normalized_note[:160]
