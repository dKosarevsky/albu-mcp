from albumentationsx_mcp.models import (
    ImageQualityAggregate,
    PreviewManifestSummary,
    PreviewQualitySummary,
    PreviewRunComparison,
)
from albumentationsx_mcp.tuning import build_tuning_session_summary


def test_tuning_summary_marks_accepted_candidate_ready_for_export() -> None:
    comparison = _comparison(
        inputs_changed=False,
        quality_summary=PreviewQualitySummary(
            baseline=ImageQualityAggregate(image_count=1, brightness_mean=80.0),
            candidate=ImageQualityAggregate(image_count=1, brightness_mean=140.0),
            deltas={"brightness_mean": 60.0},
        ),
    )

    summary = build_tuning_session_summary(
        comparison,
        feedback_tags=["too_noisy:high"],
        accepted=True,
    )

    assert summary.baseline_run_id == "baseline"
    assert summary.candidate_run_id == "candidate"
    assert summary.feedback_tags == ["too_noisy:high"]
    assert summary.quality_deltas == {"brightness_mean": 60.0}
    assert summary.export_ready is True
    assert summary.recommended_next_tool == "export_pipeline"


def test_tuning_summary_blocks_export_when_inputs_changed() -> None:
    summary = build_tuning_session_summary(
        _comparison(inputs_changed=True),
        feedback_tags=[],
        accepted=True,
    )

    assert summary.export_ready is False
    assert summary.recommended_next_tool == "render_preview_batch"
    assert "same inputs" in summary.rationale


def _comparison(
    *,
    inputs_changed: bool,
    quality_summary: PreviewQualitySummary | None = None,
) -> PreviewRunComparison:
    return PreviewRunComparison(
        baseline=_manifest_summary("baseline"),
        candidate=_manifest_summary("candidate"),
        pipeline_changed=True,
        inputs_changed=inputs_changed,
        seed_changed=False,
        artifact_count_delta=0,
        review_notes=["Review both contact sheets"],
        suggested_feedback_tags=["too_noisy"],
        quality_summary=quality_summary,
    )


def _manifest_summary(run_id: str) -> PreviewManifestSummary:
    return PreviewManifestSummary(
        run_id=run_id,
        created_at="2026-06-13T12:00:00Z",
        input_count=1,
        transform_count=1,
        transform_names=["GaussNoise"],
    )
