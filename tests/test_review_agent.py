from __future__ import annotations

from albumentationsx_mcp.models import (
    ImageQualityAggregate,
    PreviewManifestSummary,
    PreviewQualitySummary,
    PreviewReviewGuidance,
    PreviewRunComparison,
    QualityFinding,
)
from albumentationsx_mcp.review_agent import build_review_agent_plan, interpret_preview_feedback


def test_review_agent_interprets_free_form_negative_feedback() -> None:
    interpretation = interpret_preview_feedback("Example 8 is maybe too noisy; I can't even recognize the objects.")

    assert interpretation.accepted is False
    assert interpretation.decision_hint == "revise"
    assert interpretation.recommended_next_tool == "adjust_pipeline"
    assert interpretation.feedback_tags == ["too_noisy:high", "object_unrecognizable:high"]
    assert {signal.feedback_tag for signal in interpretation.signals} == {
        "too_noisy",
        "object_unrecognizable",
    }


def test_review_agent_interprets_acceptance_feedback() -> None:
    interpretation = interpret_preview_feedback("That set looks good, thanks.")

    assert interpretation.accepted is True
    assert interpretation.decision_hint == "accept"
    assert interpretation.recommended_next_tool == "record_tuning_decision"
    assert interpretation.feedback_tags == []


def test_review_agent_collects_structured_feedback_before_adjusting() -> None:
    plan = build_review_agent_plan(_comparison(), feedback_tags=[], accepted=False)

    assert plan.decision == "collect_feedback"
    assert plan.recommended_next_tool == "list_feedback_tags"
    assert plan.suggested_feedback_tags == ["too_noisy"]
    assert any("too_noisy" in item for item in plan.review_checklist)
    assert plan.tuning_summary.recommended_next_tool == "list_feedback_tags"


def test_review_agent_routes_negative_feedback_to_pipeline_adjustment() -> None:
    plan = build_review_agent_plan(_comparison(), feedback_tags=["too_noisy:high"], accepted=False)

    assert plan.decision == "revise_candidate"
    assert plan.recommended_next_tool == "adjust_pipeline"
    assert plan.feedback_tags == ["too_noisy:high"]
    assert any("render_preview_batch" in action for action in plan.next_actions)


def test_review_agent_uses_free_form_feedback_note_for_plan() -> None:
    plan = build_review_agent_plan(
        _comparison(),
        feedback_tags=[],
        feedback_note="example 8 is too noisy and object is unrecognizable",
        accepted=False,
    )

    assert plan.decision == "revise_candidate"
    assert plan.recommended_next_tool == "adjust_pipeline"
    assert plan.feedback_tags == ["too_noisy:high", "object_unrecognizable:high"]


def test_review_agent_accepts_candidate_through_audit_decision() -> None:
    plan = build_review_agent_plan(_comparison(), feedback_tags=[], accepted=True)

    assert plan.decision == "accept_candidate"
    assert plan.recommended_next_tool == "record_tuning_decision"
    assert plan.tuning_summary.export_ready is True
    assert any("record_tuning_decision" in action for action in plan.next_actions)
    assert any("export_pipeline" in action for action in plan.next_actions)


def test_review_agent_blocks_acceptance_when_inputs_changed() -> None:
    plan = build_review_agent_plan(_comparison(inputs_changed=True), feedback_tags=[], accepted=True)

    assert plan.decision == "rerender_candidate"
    assert plan.recommended_next_tool == "render_preview_batch"
    assert plan.tuning_summary.export_ready is False
    assert plan.blockers == ["candidate_inputs_changed"]


def _comparison(*, inputs_changed: bool = False) -> PreviewRunComparison:
    return PreviewRunComparison(
        baseline=_summary("baseline"),
        candidate=_summary("candidate"),
        pipeline_changed=True,
        inputs_changed=inputs_changed,
        seed_changed=False,
        artifact_count_delta=0,
        review_notes=["Pipeline changed; compare contact sheets before accepting."],
        suggested_feedback_tags=["too_noisy"],
        review_guidance=[
            PreviewReviewGuidance(
                feedback_tag="too_noisy",
                review_focus="Check whether noise hides object boundaries.",
                rationale="Candidate uses a noise transform.",
                suggested_action="reduce_noise_intensity",
            )
        ],
        quality_summary=PreviewQualitySummary(
            baseline=ImageQualityAggregate(image_count=1, brightness_mean=80.0),
            candidate=ImageQualityAggregate(image_count=1, brightness_mean=120.0),
            deltas={"brightness_mean": 40.0},
            findings=[
                QualityFinding(
                    code="candidate_high_brightness_shift",
                    severity="medium",
                    message="Candidate brightness changed more than expected.",
                    metric="brightness_mean",
                    value=40.0,
                    baseline_value=80.0,
                )
            ],
        ),
    )


def _summary(run_id: str) -> PreviewManifestSummary:
    return PreviewManifestSummary(
        run_id=run_id,
        created_at="2026-01-01T00:00:00Z",
        input_count=1,
        variants_per_image=1,
        seed=0,
        transform_count=1,
        transform_names=["GaussNoise"],
        artifact_counts={"image": 1},
        contact_sheet_paths=[f"/artifacts/{run_id}/contact-sheet.png"],
    )
