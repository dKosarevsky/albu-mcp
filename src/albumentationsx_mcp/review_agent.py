"""Review Agent workflow planning for preview-driven augmentation tuning."""

from __future__ import annotations

import re
from collections.abc import Iterable
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
    "washed out",
    "overexposed",
    "underexposed",
    "too ",
)
_LOW_SEVERITY_PATTERNS = ("maybe", "slightly", "a bit", "bit ", "minor")
_SIGNAL_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("too_noisy", ("noise", "noisy", "speckle", "speckled", "grain", "grainy")),
    ("too_blurry", ("blur", "blurry", "soft", "smeared")),
    ("too_distorted", ("distort", "distorted", "skew", "skewed", "warp", "warped", "bent")),
    ("too_dark", ("too dark", "dark", "underexposed", "dim", "shadow")),
    ("too_bright", ("too bright", "bright", "overexposed", "washed out", "blown out")),
    (
        "color_shift",
        (
            "color shift",
            "color shifted",
            "colors look off",
            "colors off",
            "hue",
            "saturation",
            "tint",
            "weird color",
            "color cast",
        ),
    ),
    (
        "object_unrecognizable",
        ("unrecognizable", "can't recognize", "cannot recognize", "cant recognize", "can't see", "cannot see"),
    ),
)
_INTENT_BY_TAG = {
    "too_noisy": "reduce_noise",
    "too_blurry": "reduce_blur",
    "too_distorted": "reduce_geometric_distortion",
    "too_dark": "fix_exposure",
    "too_bright": "fix_exposure",
    "color_shift": "reduce_color_shift",
    "object_unrecognizable": "protect_object_readability",
}
_TRANSFORM_GUIDANCE_BY_TAG = {
    "too_noisy": "Reduce noise transform probability or numeric ranges.",
    "too_blurry": "Reduce blur transform probability, kernel, or sigma ranges.",
    "too_distorted": "Reduce affine, perspective, rotation, or distortion strength.",
    "too_dark": "Reduce brightness/contrast transform probability or numeric ranges.",
    "too_bright": "Reduce brightness/contrast transform probability or numeric ranges.",
    "color_shift": "Reduce hue, saturation, RGB shift, or color jitter strength.",
    "object_unrecognizable": "Reduce destructive transforms until labeled objects remain readable.",
}
_ADJUSTMENT_STRATEGY_BY_TAG = {
    "too_noisy": "Lower noise probability or numeric ranges, then rerender the same reviewed inputs.",
    "too_blurry": "Reduce blur strength and verify boundary detail before changing other transforms.",
    "too_distorted": "Reduce geometric distortion strength before adding more spatial transforms.",
    "too_dark": "Move exposure settings toward the baseline before changing color transforms.",
    "too_bright": "Move exposure settings toward the baseline before changing color transforms.",
    "color_shift": "Reduce color-shift transforms before changing geometric or noise transforms.",
    "object_unrecognizable": "Prioritize object readability before adding more augmentation variety.",
}
_SAFETY_CHECKS_BY_TAG = {
    "too_noisy": "Confirm the same object remains recognizable in the next contact sheet.",
    "too_blurry": "Confirm object boundaries or text remain inspectable after the next render.",
    "too_distorted": "Confirm labels still match the visible object geometry after the next render.",
    "too_dark": "Confirm low-light regions still expose the target object after the next render.",
    "too_bright": "Confirm highlights do not hide the target object after the next render.",
    "color_shift": "Confirm class or label evidence is not changed by color after the next render.",
    "object_unrecognizable": "Do not add additional destructive transforms until readability is restored.",
}


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
    base_feedback_tags = [_base_tag(tag) for tag in effective_feedback_tags]
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
        adjustment_strategy=_adjustment_strategy(base_feedback_tags),
        safety_checks=_safety_checks(base_feedback_tags),
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
    feedback_intents = _unique(_INTENT_BY_TAG[signal.feedback_tag] for signal in signals)
    transform_guidance = _unique(_TRANSFORM_GUIDANCE_BY_TAG[signal.feedback_tag] for signal in signals)
    base_feedback_tags = [signal.feedback_tag for signal in signals]
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
        feedback_intents=feedback_intents,
        transform_guidance=transform_guidance,
        adjustment_strategy=_adjustment_strategy(base_feedback_tags),
        safety_checks=_safety_checks(base_feedback_tags),
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


def _base_tag(feedback_tag: str) -> str:
    return feedback_tag.split(":", maxsplit=1)[0]


def _adjustment_strategy(feedback_tags: Iterable[str]) -> list[str]:
    return _unique(_ADJUSTMENT_STRATEGY_BY_TAG[tag] for tag in feedback_tags if tag in _ADJUSTMENT_STRATEGY_BY_TAG)


def _safety_checks(feedback_tags: Iterable[str]) -> list[str]:
    return _unique(_SAFETY_CHECKS_BY_TAG[tag] for tag in feedback_tags if tag in _SAFETY_CHECKS_BY_TAG)


def _unique(items: Iterable[str]) -> list[str]:
    unique_items: list[str] = []
    for item in items:
        if item not in unique_items:
            unique_items.append(item)
    return unique_items
