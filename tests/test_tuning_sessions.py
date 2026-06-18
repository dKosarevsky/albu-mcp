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


def test_interactive_tuning_session_store_closes_rejected_session(tmp_path: Path) -> None:
    store = InteractiveTuningSessionStore(tmp_path)
    session = store.start_session(task="classification", targets=["image"], baseline_run_id="baseline-a")
    store.record_step(session.session_id, summary=_summary(candidate_run_id="candidate-a", accepted=False))

    rejected = store.close_session(session.session_id, status="rejected", note="no candidate stayed readable")
    listed = store.list_sessions(status="rejected")
    markdown_report = store.export_session(session.session_id, output_format="markdown")

    assert rejected.status == "rejected"
    assert rejected.closed_at is not None
    assert rejected.archived_at is None
    assert rejected.status_note == "no candidate stayed readable"
    assert rejected.accepted_candidate_run_id is None
    assert rejected.next_actions == ["Session closed as rejected. Call `export_tuning_session` for audit."]
    assert listed.rejected_count == 1
    assert listed.sessions[0].session_id == session.session_id
    assert "no candidate stayed readable" in markdown_report.content


def test_interactive_tuning_session_store_archives_session(tmp_path: Path) -> None:
    store = InteractiveTuningSessionStore(tmp_path)
    session = store.start_session(task="classification", targets=["image"], baseline_run_id="baseline-a")

    archived = store.archive_session(session.session_id, note="superseded by a later dataset review")
    listed = store.list_sessions(status="archived")

    assert archived.status == "archived"
    assert archived.archived_at is not None
    assert archived.status_note == "superseded by a later dataset review"
    assert archived.next_actions == ["Session archived."]
    assert listed.archived_count == 1
    assert listed.sessions[0].session_id == session.session_id


def test_interactive_tuning_session_store_cleanup_preserves_active_sessions(tmp_path: Path) -> None:
    store = InteractiveTuningSessionStore(tmp_path)
    old_a = store.start_session(task="classification", targets=["image"], baseline_run_id="baseline-a")
    store.close_session(old_a.session_id, status="rejected", note="old rejected a")
    old_b = store.start_session(task="classification", targets=["image"], baseline_run_id="baseline-b")
    store.close_session(old_b.session_id, status="rejected", note="old rejected b")
    newest_closed = store.start_session(task="classification", targets=["image"], baseline_run_id="baseline-c")
    store.close_session(newest_closed.session_id, status="rejected", note="newest closed")
    active = store.start_session(task="classification", targets=["image"], baseline_run_id="baseline-active")

    cleanup = store.cleanup_sessions(keep_last=1, include_active=False)
    remaining = store.list_sessions(limit=10)
    remaining_ids = {session.session_id for session in remaining.sessions}

    assert cleanup.deleted_count == 2
    assert cleanup.protected_active_count == 1
    assert {session.session_id for session in cleanup.deleted_sessions} == {old_a.session_id, old_b.session_id}
    assert active.session_id in remaining_ids
    assert newest_closed.session_id in remaining_ids
    assert remaining.total_count == 2


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
