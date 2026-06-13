"""Dataset-level preview candidate scoring."""

from __future__ import annotations

from collections import Counter

from albumentationsx_mcp.models import (
    DatasetFindingCount,
    DatasetMetricStats,
    DatasetPreviewScore,
    PreviewCandidateRanking,
    PreviewRunComparison,
    QualityProfileName,
    RiskLevel,
)
from albumentationsx_mcp.ranking import rank_preview_candidates

_METRIC_FIELDS = (
    "brightness_mean",
    "contrast_std",
    "sharpness_score",
    "saturation_mean",
    "colorfulness_score",
    "entropy_bits",
    "clipping_fraction",
)
_RISK_ORDER: dict[RiskLevel, int] = {"low": 0, "medium": 1, "high": 2}


def score_dataset_preview_candidates(
    comparisons: list[PreviewRunComparison],
    *,
    feedback_tags_by_candidate: dict[str, list[str]],
    accepted_candidate_ids: set[str],
    quality_profile: QualityProfileName = "balanced",
) -> DatasetPreviewScore:
    """Score several preview candidates as one dataset-level tuning set."""
    ranking = rank_preview_candidates(
        comparisons,
        feedback_tags_by_candidate=feedback_tags_by_candidate,
        accepted_candidate_ids=accepted_candidate_ids,
        quality_profile=quality_profile,
    )
    if not comparisons:
        return DatasetPreviewScore(
            baseline_run_id="",
            quality_profile=quality_profile,
            candidate_count=0,
            ranking=ranking,
            decision_guidance=["Render candidate previews before dataset scoring."],
        )

    return DatasetPreviewScore(
        baseline_run_id=comparisons[0].baseline.run_id,
        quality_profile=quality_profile,
        candidate_count=len(comparisons),
        best_candidate_run_id=ranking.best_candidate_run_id,
        ranking=ranking,
        metric_stats=_metric_stats(comparisons),
        finding_counts=_finding_counts(comparisons),
        decision_guidance=_decision_guidance(ranking),
    )


def _metric_stats(comparisons: list[PreviewRunComparison]) -> list[DatasetMetricStats]:
    stats: list[DatasetMetricStats] = []
    for metric in _METRIC_FIELDS:
        values = _candidate_metric_values(comparisons, metric)
        if values:
            stats.append(
                DatasetMetricStats(
                    metric=metric,
                    candidate_count=len(values),
                    min_value=round(min(values), 4),
                    max_value=round(max(values), 4),
                    mean_value=round(sum(values) / len(values), 4),
                ),
            )
    return stats


def _candidate_metric_values(comparisons: list[PreviewRunComparison], metric: str) -> list[float]:
    values: list[float] = []
    for comparison in comparisons:
        if comparison.quality_summary is None:
            continue
        value = getattr(comparison.quality_summary.candidate, metric)
        if value is not None:
            values.append(float(value))
    return values


def _finding_counts(comparisons: list[PreviewRunComparison]) -> list[DatasetFindingCount]:
    counter: Counter[tuple[str, RiskLevel]] = Counter()
    for comparison in comparisons:
        if comparison.quality_summary is None:
            continue
        for finding in comparison.quality_summary.findings:
            counter[(finding.code, finding.severity)] += 1

    return [
        DatasetFindingCount(code=code, severity=severity, count=count)
        for (code, severity), count in sorted(
            counter.items(),
            key=lambda item: (-item[1], -_RISK_ORDER[item[0][1]], item[0][0]),
        )
    ]


def _decision_guidance(ranking: PreviewCandidateRanking) -> list[str]:
    if ranking.best_candidate_run_id is None:
        return ["Render candidate previews before dataset scoring."]
    guidance = [
        f"Best dataset candidate is {ranking.best_candidate_run_id}.",
        *ranking.decision_guidance,
    ]
    if ranking.ranked_candidates and not ranking.ranked_candidates[0].export_ready:
        guidance.append("Record acceptance before exporting the final pipeline.")
    return guidance
