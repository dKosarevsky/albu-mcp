"""Preview tuning session summaries."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from albumentationsx_mcp.models import (
    PreviewRunComparison,
    QualityFinding,
    RiskLevel,
    TuningDecisionList,
    TuningDecisionRecord,
    TuningSessionSummary,
)

NextTuningTool = Literal["list_feedback_tags", "adjust_pipeline", "render_preview_batch", "export_pipeline"]
_DECISIONS_FILE = "tuning_decisions.json"
_FINDING_PENALTIES: dict[RiskLevel, float] = {"low": 5.0, "medium": 15.0, "high": 35.0}
_RISK_ORDER: dict[RiskLevel, int] = {"low": 0, "medium": 1, "high": 2}
_INPUTS_CHANGED_PENALTY = 25.0


def build_tuning_session_summary(
    comparison: PreviewRunComparison,
    *,
    feedback_tags: list[str],
    accepted: bool = False,
) -> TuningSessionSummary:
    """Build an agent-facing summary for one preview tuning comparison."""
    export_ready = accepted and not comparison.inputs_changed
    next_tool, rationale = _next_tool_and_rationale(comparison, feedback_tags=feedback_tags, export_ready=export_ready)
    quality_findings = _quality_findings(comparison)
    return TuningSessionSummary(
        baseline_run_id=comparison.baseline.run_id,
        candidate_run_id=comparison.candidate.run_id,
        feedback_tags=feedback_tags,
        accepted=accepted,
        export_ready=export_ready,
        recommended_next_tool=next_tool,
        rationale=rationale,
        suggested_feedback_tags=comparison.suggested_feedback_tags,
        quality_deltas=comparison.quality_summary.deltas if comparison.quality_summary else {},
        quality_score=_quality_score(comparison, quality_findings),
        quality_risk=_quality_risk(comparison, quality_findings),
        quality_findings=quality_findings,
        review_notes=[*comparison.review_notes, *comparison.quality_warnings],
    )


class TuningDecisionStore:
    """Small JSON-backed local journal for preview tuning decisions."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / _DECISIONS_FILE

    def record_decision(
        self,
        summary: TuningSessionSummary,
        reviewer_notes: list[str] | None = None,
    ) -> TuningDecisionRecord:
        """Persist one tuning decision and return the stored record."""
        decision = TuningDecisionRecord(
            decision_id=uuid.uuid4().hex,
            created_at=_utc_now(),
            baseline_run_id=summary.baseline_run_id,
            candidate_run_id=summary.candidate_run_id,
            feedback_tags=summary.feedback_tags,
            accepted=summary.accepted,
            export_ready=summary.export_ready,
            recommended_next_tool=summary.recommended_next_tool,
            quality_score=summary.quality_score,
            quality_risk=summary.quality_risk,
            reviewer_notes=reviewer_notes or [],
            summary=summary,
        )
        decisions = [decision, *self._read_decisions()]
        self._write_decisions(decisions)
        return decision

    def list_decisions(
        self,
        *,
        limit: int = 20,
        accepted_only: bool = False,
        ranked: bool = False,
    ) -> TuningDecisionList:
        """Return persisted tuning decisions, optionally filtered and score-ranked."""
        decisions = self._read_decisions()
        accepted_count = sum(decision.accepted for decision in decisions)
        if accepted_only:
            decisions = [decision for decision in decisions if decision.accepted]
        if ranked:
            decisions = sorted(
                decisions,
                key=lambda decision: (decision.quality_score, decision.accepted, decision.created_at),
                reverse=True,
            )
        bounded_limit = max(1, min(limit, 100))
        return TuningDecisionList(
            decisions=decisions[:bounded_limit],
            total_count=len(decisions),
            accepted_count=accepted_count,
            ranked=ranked,
        )

    def _read_decisions(self) -> list[TuningDecisionRecord]:
        if not self.index_path.exists():
            return []
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        return [TuningDecisionRecord.model_validate(item) for item in payload.get("decisions", [])]

    def _write_decisions(self, decisions: list[TuningDecisionRecord]) -> None:
        payload = {"decisions": [decision.model_dump(mode="json") for decision in decisions]}
        self.index_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _next_tool_and_rationale(
    comparison: PreviewRunComparison,
    *,
    feedback_tags: list[str],
    export_ready: bool,
) -> tuple[NextTuningTool, str]:
    if comparison.inputs_changed:
        return "render_preview_batch", "Re-render the candidate with the same inputs before deciding."
    if export_ready:
        return "export_pipeline", "The candidate is accepted and used the same inputs, so export is ready."
    if feedback_tags:
        return "adjust_pipeline", "Apply the selected feedback tags, validate, and render another candidate."
    return "list_feedback_tags", "Ask the user which suggested feedback tags match the reviewed contact sheets."


def _quality_findings(comparison: PreviewRunComparison) -> list[QualityFinding]:
    if comparison.quality_summary is None:
        return []
    return comparison.quality_summary.findings


def _quality_score(comparison: PreviewRunComparison, findings: list[QualityFinding]) -> float:
    penalty = sum(_FINDING_PENALTIES[finding.severity] for finding in findings)
    if comparison.inputs_changed:
        penalty += _INPUTS_CHANGED_PENALTY
    return round(max(0.0, 100.0 - penalty), 2)


def _quality_risk(comparison: PreviewRunComparison, findings: list[QualityFinding]) -> RiskLevel:
    risk: RiskLevel = "low"
    for finding in findings:
        if _RISK_ORDER[finding.severity] > _RISK_ORDER[risk]:
            risk = finding.severity
    if comparison.inputs_changed:
        return "high"
    return risk


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
