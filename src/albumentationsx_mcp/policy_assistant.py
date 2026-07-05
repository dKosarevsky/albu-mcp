"""Preview-gated augmentation policy assistant."""

from __future__ import annotations

from typing import cast

from albumentationsx_mcp.advisor import MetadataCatalog, explain_pipeline
from albumentationsx_mcp.feedback import normalize_feedback_tags
from albumentationsx_mcp.models import (
    PolicyAssistantCandidate,
    PolicyAssistantCandidateSet,
    PolicyAssistantPlan,
    PolicyIterationPlan,
    TargetSpec,
)
from albumentationsx_mcp.presets import Intensity, adjust_pipeline, recommend_pipeline

_GATE_REASON = (
    "Policy recommendations are starter candidates; render and compare previews before accepting them for training."
)
_READABILITY_CRITICAL_TAGS = {"object_unrecognizable"}


def plan_augmentation_policy(  # noqa: PLR0913 - mirrors the MCP tool input contract.
    *,
    task: str,
    objective: str = "robustness",
    intensity: Intensity = "medium",
    targets: list[str] | None = None,
    feedback_tags: list[str] | None = None,
    catalog: MetadataCatalog | None = None,
) -> PolicyAssistantPlan:
    """Recommend a conservative augmentation policy while keeping preview acceptance gated."""
    selected_targets = targets or ["image"]
    pipeline = recommend_pipeline(task=task, intensity=intensity, targets=selected_targets)
    applied_feedback_tags = _canonical_feedback_tags(feedback_tags or [])
    if applied_feedback_tags:
        pipeline = adjust_pipeline(pipeline, applied_feedback_tags)

    target_spec = TargetSpec(targets=selected_targets)
    explanation = explain_pipeline(pipeline, target_spec, catalog=catalog)
    recommended_next_tool = "render_preview_batch"
    if applied_feedback_tags and explanation.risk_level == "high":
        recommended_next_tool = "adjust_pipeline"

    return PolicyAssistantPlan(
        task=task,
        objective=objective,
        intensity=intensity,
        targets=selected_targets,
        pipeline=pipeline,
        risk_level=explanation.risk_level,
        gate_status="preview_required" if recommended_next_tool == "render_preview_batch" else "feedback_required",
        gate_reason=_GATE_REASON,
        recommended_next_tool=recommended_next_tool,
        next_tools=_next_tools(recommended_next_tool),
        next_actions=_next_actions(objective=objective, recommended_next_tool=recommended_next_tool),
        review_checklist=_review_checklist(task=task, objective=objective, targets=selected_targets),
        suggested_feedback_tags=explanation.suggested_feedback_tags,
        applied_feedback_tags=applied_feedback_tags,
        rationale=_rationale(task=task, objective=objective, intensity=intensity, risk_level=explanation.risk_level),
    )


def plan_augmentation_policy_candidates(  # noqa: PLR0913 - mirrors the MCP tool input contract.
    *,
    task: str,
    objective: str = "robustness",
    targets: list[str] | None = None,
    feedback_tags: list[str] | None = None,
    candidate_count: int = 3,
    catalog: MetadataCatalog | None = None,
) -> PolicyAssistantCandidateSet:
    """Build 3-5 ranked preview-gated policy candidates for side-by-side review."""
    bounded_count = max(3, min(5, candidate_count))
    selected_targets = targets or ["image"]
    applied_feedback_tags = _canonical_feedback_tags(feedback_tags or [])
    candidate_profiles = _candidate_profiles(bounded_count=bounded_count, feedback_tags=applied_feedback_tags)
    candidates = [
        PolicyAssistantCandidate(
            rank=index,
            candidate_id=profile["candidate_id"],
            tradeoff=profile["tradeoff"],
            preview_request_hint={
                "variants_per_image": 4,
                "recommended_tool": "render_preview_batch",
                "review_focus": profile["review_focus"],
            },
            plan=plan_augmentation_policy(
                task=task,
                objective=objective,
                intensity=cast("Intensity", profile["intensity"]),
                targets=selected_targets,
                feedback_tags=applied_feedback_tags,
                catalog=catalog,
            ),
        )
        for index, profile in enumerate(candidate_profiles, start=1)
    ]
    return PolicyAssistantCandidateSet(
        task=task,
        objective=objective,
        targets=selected_targets,
        candidate_count=len(candidates),
        gate_status="preview_required",
        gate_reason=_GATE_REASON,
        recommended_next_tool="render_preview_batch",
        applied_feedback_tags=applied_feedback_tags,
        candidates=candidates,
        comparison_checklist=_comparison_checklist(applied_feedback_tags),
    )


def plan_policy_iteration(  # noqa: PLR0913 - mirrors the MCP tool input contract.
    *,
    task: str,
    objective: str = "robustness",
    targets: list[str] | None = None,
    feedback_tags: list[str] | None = None,
    rejected_candidate_ids: list[str] | None = None,
    accepted_candidate_id: str | None = None,
    iteration: int = 1,
    candidate_count: int = 3,
    catalog: MetadataCatalog | None = None,
) -> PolicyIterationPlan:
    """Plan the next feedback-aware policy iteration while keeping export review gated."""
    selected_targets = targets or ["image"]
    applied_feedback_tags = _canonical_feedback_tags(feedback_tags or [])
    rejected_ids = rejected_candidate_ids or []
    candidate_set = plan_augmentation_policy_candidates(
        task=task,
        objective=objective,
        targets=selected_targets,
        feedback_tags=applied_feedback_tags,
        candidate_count=candidate_count,
        catalog=catalog,
    )
    accepted = accepted_candidate_id is not None
    return PolicyIterationPlan(
        task=task,
        objective=objective,
        targets=selected_targets,
        iteration=max(1, iteration),
        iteration_status="accepted_for_export_review" if accepted else "needs_preview",
        acceptance_status="candidate_selected" if accepted else "not_accepted",
        rejected_candidate_ids=rejected_ids,
        accepted_candidate_id=accepted_candidate_id,
        feedback_tags=applied_feedback_tags,
        candidate_set=candidate_set,
        next_actions=_iteration_next_actions(accepted=accepted, feedback_tags=applied_feedback_tags),
    )


def _canonical_feedback_tags(feedback_tags: list[str]) -> list[str]:
    normalized = normalize_feedback_tags(feedback_tags)
    canonical: list[str] = []
    for tag_name, severity in sorted(normalized.items()):
        if severity == "medium":
            canonical.append(tag_name)
        else:
            canonical.append(f"{tag_name}:{severity}")
    return canonical


def _candidate_profiles(*, bounded_count: int, feedback_tags: list[str]) -> list[dict[str, str]]:
    if _is_readability_recovery_feedback(feedback_tags):
        return _readability_recovery_candidate_profiles()[:bounded_count]

    suffix = " with feedback-aware softening" if feedback_tags else ""
    profiles = [
        {
            "candidate_id": "conservative",
            "intensity": "low",
            "tradeoff": f"Lowest destructive risk; best first preview candidate{suffix}.",
            "review_focus": "Check that weak augmentation still covers expected deployment variation.",
        },
        {
            "candidate_id": "balanced",
            "intensity": "medium",
            "tradeoff": f"Balanced robustness and recognizability for normal review loops{suffix}.",
            "review_focus": "Compare object recognizability against baseline examples.",
        },
        {
            "candidate_id": "aggressive",
            "intensity": "high",
            "tradeoff": f"Highest robustness pressure; most likely to need rejection tags{suffix}.",
            "review_focus": "Look for object loss, mask drift, over-noise, and excessive blur.",
        },
        {
            "candidate_id": "review_safe",
            "intensity": "medium",
            "tradeoff": f"Same intensity as balanced, but ranked for reviewer-focused safety checks{suffix}.",
            "review_focus": "Use when the reviewer needs a second medium candidate before export.",
        },
        {
            "candidate_id": "minimal_change",
            "intensity": "low",
            "tradeoff": f"Minimal-change fallback for sensitive datasets or uncertain labels{suffix}.",
            "review_focus": "Confirm annotations stay aligned and labels remain obvious.",
        },
    ]
    return profiles[:bounded_count]


def _readability_recovery_candidate_profiles() -> list[dict[str, str]]:
    return [
        {
            "candidate_id": "minimal_change",
            "intensity": "low",
            "tradeoff": "Readability recovery fallback; smallest change before adding more augmentation variety.",
            "review_focus": "Confirm the object is recognizable before adding more augmentation variety.",
        },
        {
            "candidate_id": "conservative",
            "intensity": "low",
            "tradeoff": "Readability recovery candidate with low destructive risk and softened noise.",
            "review_focus": "Check that the object remains readable across the reviewed examples.",
        },
        {
            "candidate_id": "review_safe",
            "intensity": "medium",
            "tradeoff": "Readability recovery medium candidate for reviewer-focused safety checks.",
            "review_focus": "Compare object recognizability before accepting any extra robustness pressure.",
        },
        {
            "candidate_id": "balanced",
            "intensity": "medium",
            "tradeoff": "Readability recovery recheck once minimal and conservative candidates remain recognizable.",
            "review_focus": "Use only if lower-risk candidates preserve the target object clearly.",
        },
        {
            "candidate_id": "annotation_safe",
            "intensity": "low",
            "tradeoff": "Readability recovery candidate for annotation-sensitive datasets.",
            "review_focus": "Confirm labels, masks, or boxes still match the visible object.",
        },
    ]


def _comparison_checklist(feedback_tags: list[str]) -> list[str]:
    checklist = [
        "Render all candidates on the same image sample and seed.",
        "Compare contact sheets before accepting any candidate.",
        "Record concrete feedback tags for rejected candidates.",
    ]
    if _is_readability_recovery_feedback(feedback_tags):
        checklist.insert(1, "Do not reintroduce aggressive candidates until object readability is restored.")
    return checklist


def _is_readability_recovery_feedback(feedback_tags: list[str]) -> bool:
    for feedback_tag in feedback_tags:
        base_tag, _, _ = feedback_tag.partition(":")
        if base_tag in _READABILITY_CRITICAL_TAGS:
            return True
    return False


def _next_tools(recommended_next_tool: str) -> list[str]:
    if recommended_next_tool == "adjust_pipeline":
        return ["adjust_pipeline", "render_preview_batch", "compare_preview_runs", "record_preview_feedback"]
    return ["render_preview_batch", "compare_preview_runs", "interpret_preview_feedback", "record_preview_feedback"]


def _next_actions(*, objective: str, recommended_next_tool: str) -> list[str]:
    if recommended_next_tool == "adjust_pipeline":
        return [
            "Reduce destructive transform strength before rendering another candidate.",
            "Render a new candidate preview after adjustment.",
            "Record reviewer feedback before exporting a training pipeline.",
        ]
    return [
        f"Render a baseline and candidate preview for the {objective} objective.",
        "Compare the preview runs with task-aware quality checks.",
        "Record feedback tags before accepting or exporting the policy.",
    ]


def _review_checklist(*, task: str, objective: str, targets: list[str]) -> list[str]:
    checklist = [
        f"Confirm augmented examples still preserve the task signal for {task}.",
        f"Reject variants that overfit the {objective} objective at the cost of recognizability.",
        "Check at least one baseline-to-candidate contact sheet before export.",
    ]
    target_set = set(targets)
    if "mask" in target_set or "bboxes" in target_set or "keypoints" in target_set:
        checklist.append("Verify annotation alignment after every geometric transform.")
    if "mask" in target_set:
        checklist.append("Inspect mask boundaries for erosion, drift, or label loss.")
    return checklist


def _rationale(*, task: str, objective: str, intensity: Intensity, risk_level: str) -> str:
    return (
        f"Selected a {intensity} starter policy for {task} / {objective}; "
        f"current static risk is {risk_level}, so preview evidence is required before acceptance."
    )


def _iteration_next_actions(*, accepted: bool, feedback_tags: list[str]) -> list[str]:
    if accepted:
        return [
            "Export only after confirming the accepted candidate preview artifacts.",
            "Record the accepted candidate id, feedback tags, and report artifact references.",
        ]
    if _is_readability_recovery_feedback(feedback_tags):
        return [
            "Restore object readability before exploring more augmentation variety.",
            "Render the recovery candidate set on the same reviewed inputs and seed.",
            "Reject any candidate where the target object is still hard to recognize.",
        ]
    return [
        "Render the next candidate set before accepting a training policy.",
        "Reject candidates with concrete feedback tags, then rerun plan_policy_iteration.",
    ]
