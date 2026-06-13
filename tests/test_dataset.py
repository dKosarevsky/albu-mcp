from albumentationsx_mcp.dataset import score_dataset_preview_candidates
from albumentationsx_mcp.models import (
    ImageQualityAggregate,
    PreviewManifestSummary,
    PreviewQualitySummary,
    PreviewRunComparison,
    QualityFinding,
    RiskLevel,
)


def test_score_dataset_preview_candidates_aggregates_metrics_and_findings() -> None:
    score = score_dataset_preview_candidates(
        [
            _comparison("candidate-b", brightness=90.0, clipping=0.15, findings=[_finding("candidate_high_clipping")]),
            _comparison("candidate-a", brightness=130.0, clipping=0.02, findings=[]),
        ],
        feedback_tags_by_candidate={"candidate-b": ["too_noisy:low"]},
        accepted_candidate_ids={"candidate-a"},
        quality_profile="ocr",
    )

    assert score.baseline_run_id == "baseline"
    assert score.quality_profile == "ocr"
    assert score.candidate_count == 2
    assert score.best_candidate_run_id == "candidate-a"
    assert [candidate.candidate_run_id for candidate in score.ranking.ranked_candidates] == [
        "candidate-a",
        "candidate-b",
    ]
    assert score.ranking.ranked_candidates[1].feedback_tags == ["too_noisy:low"]
    assert "candidate-a" in score.decision_guidance[0]

    stats = {item.metric: item for item in score.metric_stats}
    assert stats["brightness_mean"].candidate_count == 2
    assert stats["brightness_mean"].min_value == 90.0
    assert stats["brightness_mean"].max_value == 130.0
    assert stats["brightness_mean"].mean_value == 110.0
    assert stats["clipping_fraction"].mean_value == 0.085

    assert score.finding_counts[0].code == "candidate_high_clipping"
    assert score.finding_counts[0].severity == "medium"
    assert score.finding_counts[0].count == 1


def test_score_dataset_preview_candidates_handles_empty_input() -> None:
    score = score_dataset_preview_candidates(
        [],
        feedback_tags_by_candidate={},
        accepted_candidate_ids=set(),
        quality_profile="balanced",
    )

    assert score.baseline_run_id == ""
    assert score.candidate_count == 0
    assert score.best_candidate_run_id is None
    assert score.metric_stats == []
    assert score.finding_counts == []
    assert score.decision_guidance == ["Render candidate previews before dataset scoring."]


def _comparison(
    candidate_run_id: str,
    *,
    brightness: float,
    clipping: float,
    findings: list[QualityFinding],
) -> PreviewRunComparison:
    return PreviewRunComparison(
        baseline=_manifest_summary("baseline"),
        candidate=_manifest_summary(candidate_run_id),
        pipeline_changed=True,
        inputs_changed=False,
        seed_changed=False,
        artifact_count_delta=0,
        review_notes=["Review contact sheets"],
        suggested_feedback_tags=["too_noisy"],
        quality_summary=PreviewQualitySummary(
            quality_profile="balanced",
            baseline=ImageQualityAggregate(
                image_count=2,
                brightness_mean=120.0,
                clipping_fraction=0.01,
            ),
            candidate=ImageQualityAggregate(
                image_count=2,
                brightness_mean=brightness,
                clipping_fraction=clipping,
            ),
            deltas={
                "brightness_mean": round(brightness - 120.0, 4),
                "clipping_fraction": round(clipping - 0.01, 4),
            },
            findings=findings,
        ),
    )


def _manifest_summary(run_id: str) -> PreviewManifestSummary:
    return PreviewManifestSummary(
        run_id=run_id,
        created_at="2026-06-13T12:00:00Z",
        input_count=2,
        transform_count=1,
        transform_names=["GaussNoise"],
    )


def _finding(code: str, severity: RiskLevel = "medium") -> QualityFinding:
    return QualityFinding(
        code=code,
        severity=severity,
        message=code,
        metric="clipping_fraction",
        value=0.15,
        baseline_value=0.01,
    )
