from albumentationsx_mcp.models import (
    ImageQualityAggregate,
    PreviewManifestSummary,
    PreviewQualitySummary,
    PreviewRunComparison,
    QualityFinding,
    RiskLevel,
)
from albumentationsx_mcp.ranking import rank_preview_candidates


def test_rank_preview_candidates_orders_by_score_and_reports_best() -> None:
    ranking = rank_preview_candidates(
        [
            _comparison("candidate-high-risk", _finding("candidate_too_dark", "high")),
            _comparison("candidate-clean"),
            _comparison("candidate-medium-risk", _finding("candidate_high_clipping", "medium")),
        ],
        feedback_tags_by_candidate={
            "candidate-high-risk": ["too_noisy:high"],
            "candidate-clean": ["too_noisy:low"],
        },
        accepted_candidate_ids={"candidate-clean"},
        quality_profile="ocr",
    )

    assert ranking.baseline_run_id == "baseline"
    assert ranking.quality_profile == "ocr"
    assert ranking.candidate_count == 3
    assert ranking.best_candidate_run_id == "candidate-clean"
    assert [candidate.candidate_run_id for candidate in ranking.ranked_candidates] == [
        "candidate-clean",
        "candidate-medium-risk",
        "candidate-high-risk",
    ]
    assert ranking.ranked_candidates[0].rank == 1
    assert ranking.ranked_candidates[0].quality_score == 100.0
    assert ranking.ranked_candidates[0].feedback_tags == ["too_noisy:low"]
    assert ranking.ranked_candidates[0].export_ready is True
    assert ranking.ranked_candidates[1].quality_score == 85.0
    assert ranking.ranked_candidates[2].top_findings[0].code == "candidate_too_dark"
    assert "candidate-clean" in ranking.decision_guidance[0]


def test_rank_preview_candidates_is_stable_for_equal_scores() -> None:
    ranking = rank_preview_candidates(
        [
            _comparison("candidate-b"),
            _comparison("candidate-a"),
        ],
        feedback_tags_by_candidate={},
        accepted_candidate_ids=set(),
        quality_profile="balanced",
    )

    assert [candidate.candidate_run_id for candidate in ranking.ranked_candidates] == [
        "candidate-a",
        "candidate-b",
    ]


def _comparison(candidate_run_id: str, *findings: QualityFinding) -> PreviewRunComparison:
    return PreviewRunComparison(
        baseline=_manifest_summary("baseline"),
        candidate=_manifest_summary(candidate_run_id),
        pipeline_changed=True,
        inputs_changed=False,
        seed_changed=False,
        artifact_count_delta=0,
        review_notes=["Review both contact sheets"],
        suggested_feedback_tags=["too_noisy"],
        quality_summary=PreviewQualitySummary(
            quality_profile="balanced",
            baseline=ImageQualityAggregate(image_count=1, brightness_mean=128.0),
            candidate=ImageQualityAggregate(image_count=1, brightness_mean=128.0),
            findings=list(findings),
        ),
    )


def _manifest_summary(run_id: str) -> PreviewManifestSummary:
    return PreviewManifestSummary(
        run_id=run_id,
        created_at="2026-06-13T12:00:00Z",
        input_count=1,
        transform_count=1,
        transform_names=["GaussNoise"],
    )


def _finding(code: str, severity: RiskLevel) -> QualityFinding:
    return QualityFinding(
        code=code,
        severity=severity,
        message=code,
        metric="brightness_mean",
        value=0.0,
        baseline_value=128.0,
    )
