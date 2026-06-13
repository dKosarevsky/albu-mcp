from pathlib import Path

from albumentationsx_mcp.models import TuningSessionSummary
from albumentationsx_mcp.tuning import TuningDecisionStore


def test_tuning_decision_store_records_and_lists_decisions(tmp_path: Path) -> None:
    store = TuningDecisionStore(tmp_path)

    decision = store.record_decision(_summary("candidate-a", accepted=True, quality_score=92.0), ["ship this"])
    listed = store.list_decisions()

    assert len(decision.decision_id) == 32
    assert decision.created_at.endswith("Z")
    assert decision.candidate_run_id == "candidate-a"
    assert decision.accepted is True
    assert decision.export_ready is True
    assert decision.quality_score == 92.0
    assert decision.reviewer_notes == ["ship this"]
    assert listed.total_count == 1
    assert listed.accepted_count == 1
    assert listed.decisions[0].decision_id == decision.decision_id
    assert (tmp_path / "tuning_decisions.json").exists()


def test_tuning_decision_store_filters_and_ranks_decisions(tmp_path: Path) -> None:
    store = TuningDecisionStore(tmp_path)
    store.record_decision(_summary("candidate-low", accepted=False, quality_score=35.0), [])
    store.record_decision(_summary("candidate-high", accepted=True, quality_score=88.0), [])
    store.record_decision(_summary("candidate-mid", accepted=True, quality_score=65.0), [])

    accepted = store.list_decisions(accepted_only=True)
    ranked = store.list_decisions(ranked=True)

    assert [decision.candidate_run_id for decision in accepted.decisions] == ["candidate-mid", "candidate-high"]
    assert [decision.candidate_run_id for decision in ranked.decisions] == [
        "candidate-high",
        "candidate-mid",
        "candidate-low",
    ]
    assert accepted.accepted_count == 2


def _summary(candidate_run_id: str, *, accepted: bool, quality_score: float) -> TuningSessionSummary:
    return TuningSessionSummary(
        baseline_run_id="baseline",
        candidate_run_id=candidate_run_id,
        feedback_tags=["too_noisy"],
        accepted=accepted,
        export_ready=accepted,
        recommended_next_tool="export_pipeline" if accepted else "adjust_pipeline",
        rationale="test",
        quality_score=quality_score,
        quality_risk="low",
    )
