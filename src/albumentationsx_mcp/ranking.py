"""Preview candidate ranking helpers."""

from __future__ import annotations

from albumentationsx_mcp.models import (
    PreviewCandidateRanking,
    PreviewRunComparison,
    QualityFinding,
    QualityProfileName,
    RankedPreviewCandidate,
    RiskLevel,
    TuningSessionSummary,
)
from albumentationsx_mcp.tuning import build_tuning_session_summary

_RISK_ORDER: dict[RiskLevel, int] = {"low": 0, "medium": 1, "high": 2}
_TOP_FINDING_LIMIT = 3


def rank_preview_candidates(
    comparisons: list[PreviewRunComparison],
    *,
    feedback_tags_by_candidate: dict[str, list[str]],
    accepted_candidate_ids: set[str],
    quality_profile: QualityProfileName = "balanced",
) -> PreviewCandidateRanking:
    """Rank multiple candidate preview comparisons against one baseline."""
    if not comparisons:
        return PreviewCandidateRanking(
            baseline_run_id="",
            quality_profile=quality_profile,
            candidate_count=0,
            decision_guidance=["Render at least one candidate preview before ranking."],
        )

    summaries = [
        build_tuning_session_summary(
            comparison,
            feedback_tags=feedback_tags_by_candidate.get(comparison.candidate.run_id, []),
            accepted=comparison.candidate.run_id in accepted_candidate_ids,
        )
        for comparison in comparisons
    ]
    ranked_summaries = sorted(summaries, key=_ranking_key)
    ranked_candidates = [
        _ranked_candidate(rank=index + 1, summary=summary) for index, summary in enumerate(ranked_summaries)
    ]
    best_candidate = ranked_candidates[0] if ranked_candidates else None
    return PreviewCandidateRanking(
        baseline_run_id=comparisons[0].baseline.run_id,
        quality_profile=quality_profile,
        candidate_count=len(comparisons),
        best_candidate_run_id=best_candidate.candidate_run_id if best_candidate else None,
        ranked_candidates=ranked_candidates,
        decision_guidance=_decision_guidance(best_candidate),
    )


def _ranking_key(summary: TuningSessionSummary) -> tuple[float, int, int, str]:
    return (
        -summary.quality_score,
        _RISK_ORDER[summary.quality_risk],
        0 if summary.export_ready else 1,
        summary.candidate_run_id,
    )


def _ranked_candidate(*, rank: int, summary: TuningSessionSummary) -> RankedPreviewCandidate:
    return RankedPreviewCandidate(
        rank=rank,
        candidate_run_id=summary.candidate_run_id,
        quality_score=summary.quality_score,
        quality_risk=summary.quality_risk,
        export_ready=summary.export_ready,
        recommended_next_tool=summary.recommended_next_tool,
        feedback_tags=summary.feedback_tags,
        top_findings=_top_findings(summary.quality_findings),
        summary=summary,
    )


def _top_findings(findings: list[QualityFinding]) -> list[QualityFinding]:
    return sorted(findings, key=lambda finding: (_RISK_ORDER[finding.severity], finding.code), reverse=True)[
        :_TOP_FINDING_LIMIT
    ]


def _decision_guidance(best_candidate: RankedPreviewCandidate | None) -> list[str]:
    if best_candidate is None:
        return ["Render at least one candidate preview before ranking."]
    guidance = [
        f"Best candidate is {best_candidate.candidate_run_id} with score {best_candidate.quality_score:.1f}.",
    ]
    if best_candidate.top_findings:
        guidance.append("Review top findings before accepting the candidate.")
    if best_candidate.export_ready:
        guidance.append("The best candidate is marked export-ready.")
    else:
        guidance.append("Record user acceptance before exporting this candidate.")
    return guidance
