import json
from pathlib import Path

import pytest

from albumentationsx_mcp.models import TuningSessionSummary
from albumentationsx_mcp.sessions import InteractiveTuningSessionStore


def test_interactive_tuning_session_store_starts_and_lists_sessions(tmp_path: Path) -> None:
    store = InteractiveTuningSessionStore(tmp_path)

    session = store.start_session(
        task="classification",
        targets=["image"],
        baseline_run_id="baseline-a",
        quality_profile="balanced",
    )
    listed = store.list_sessions()

    assert len(session.session_id) == 32
    assert session.status == "active"
    assert session.baseline_run_id == "baseline-a"
    assert session.accepted_candidate_run_id is None
    assert session.step_count == 0
    assert session.model_dump(mode="json")["step_count"] == 0
    assert session.next_actions == ["Render a candidate preview and call `record_tuning_session_step`."]
    assert listed.total_count == 1
    assert listed.sessions[0].session_id == session.session_id
    assert (tmp_path / "tuning_sessions.json").exists()


def test_interactive_tuning_session_store_records_feedback_step(tmp_path: Path) -> None:
    store = InteractiveTuningSessionStore(tmp_path)
    session = store.start_session(task="classification", targets=["image"], baseline_run_id="baseline-a")

    updated = store.record_step(
        session.session_id,
        summary=_summary(candidate_run_id="candidate-a", accepted=False),
        reviewer_notes=["example 8 is too noisy"],
    )

    assert updated.status == "active"
    assert updated.step_count == 1
    assert updated.accepted_candidate_run_id is None
    assert updated.steps[0].candidate_run_id == "candidate-a"
    assert updated.steps[0].feedback_tags == ["too_noisy:high"]
    assert updated.steps[0].reviewer_notes == ["example 8 is too noisy"]
    assert updated.next_actions == ["Call `adjust_pipeline`, validate, and render the next candidate."]


def test_interactive_tuning_session_store_closes_on_accepted_step(tmp_path: Path) -> None:
    store = InteractiveTuningSessionStore(tmp_path)
    session = store.start_session(task="classification", targets=["image"], baseline_run_id="baseline-a")

    updated = store.record_step(
        session.session_id,
        summary=_summary(candidate_run_id="candidate-good", accepted=True),
        reviewer_notes=["candidate keeps object readable"],
    )

    assert updated.status == "accepted"
    assert updated.step_count == 1
    assert updated.accepted_candidate_run_id == "candidate-good"
    assert updated.next_actions == ["Call `export_pipeline` or `export_tuning_session` for handoff."]


def test_interactive_tuning_session_store_rejects_baseline_mismatch(tmp_path: Path) -> None:
    store = InteractiveTuningSessionStore(tmp_path)
    session = store.start_session(task="classification", targets=["image"], baseline_run_id="baseline-a")

    with pytest.raises(ValueError, match="baseline_run_id"):
        store.record_step(
            session.session_id,
            summary=_summary(baseline_run_id="other-baseline", candidate_run_id="candidate-a", accepted=False),
            reviewer_notes=[],
        )


def test_interactive_tuning_session_store_exports_markdown_and_json(tmp_path: Path) -> None:
    store = InteractiveTuningSessionStore(tmp_path)
    session = store.start_session(task="classification", targets=["image"], baseline_run_id="baseline-a")
    store.record_step(session.session_id, summary=_summary(candidate_run_id="candidate-a", accepted=False))
    store.record_step(session.session_id, summary=_summary(candidate_run_id="candidate-good", accepted=True))

    markdown_report = store.export_session(session.session_id, output_format="markdown")
    json_report = store.export_session(session.session_id, output_format="json")
    payload = json.loads(json_report.content)

    assert markdown_report.format == "markdown"
    assert "# Interactive Tuning Session" in markdown_report.content
    assert "candidate-good" in markdown_report.content
    assert markdown_report.step_count == 2
    assert payload["accepted_candidate_run_id"] == "candidate-good"
    assert payload["step_count"] == 2


def _summary(
    *,
    baseline_run_id: str = "baseline-a",
    candidate_run_id: str,
    accepted: bool,
) -> TuningSessionSummary:
    return TuningSessionSummary(
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        feedback_tags=["too_noisy:high"],
        accepted=accepted,
        export_ready=accepted,
        recommended_next_tool="export_pipeline" if accepted else "adjust_pipeline",
        rationale="test rationale",
        suggested_feedback_tags=["too_noisy"],
        quality_score=90.0 if accepted else 68.0,
        quality_risk="low" if accepted else "medium",
    )
