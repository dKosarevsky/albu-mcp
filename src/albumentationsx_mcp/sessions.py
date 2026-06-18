"""JSON-backed interactive tuning session store."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from albumentationsx_mcp.models import (
    InteractiveTuningSession,
    InteractiveTuningSessionExport,
    InteractiveTuningSessionList,
    InteractiveTuningStep,
    QualityProfileName,
    TuningSessionStatus,
    TuningSessionSummary,
)

_SESSIONS_FILE = "tuning_sessions.json"


class InteractiveTuningSessionStore:
    """Small JSON-backed journal for multi-step preview tuning sessions."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / _SESSIONS_FILE

    def start_session(
        self,
        *,
        task: str,
        targets: list[str],
        baseline_run_id: str | None = None,
        quality_profile: QualityProfileName = "balanced",
    ) -> InteractiveTuningSession:
        """Create a new active interactive tuning session."""
        now = _utc_now()
        session = InteractiveTuningSession(
            session_id=uuid.uuid4().hex,
            created_at=now,
            updated_at=now,
            task=task.strip() or "classification",
            targets=_normalize_targets(targets),
            quality_profile=quality_profile,
            baseline_run_id=baseline_run_id,
            next_actions=["Render a candidate preview and call `record_tuning_session_step`."],
        )
        sessions = [session, *self._read_sessions()]
        self._write_sessions(sessions)
        return session

    def record_step(
        self,
        session_id: str,
        *,
        summary: TuningSessionSummary,
        reviewer_notes: list[str] | None = None,
    ) -> InteractiveTuningSession:
        """Append one baseline-to-candidate tuning step to a session."""
        sessions = self._read_sessions()
        session_index, session = self._find_session(sessions, session_id)
        if session.baseline_run_id is not None and session.baseline_run_id != summary.baseline_run_id:
            msg = f"summary baseline_run_id {summary.baseline_run_id!r} does not match session baseline_run_id"
            raise ValueError(msg)
        step = InteractiveTuningStep(
            step_id=uuid.uuid4().hex,
            created_at=_utc_now(),
            baseline_run_id=summary.baseline_run_id,
            candidate_run_id=summary.candidate_run_id,
            feedback_tags=summary.feedback_tags,
            accepted=summary.accepted,
            reviewer_notes=reviewer_notes or [],
            recommended_next_tool=summary.recommended_next_tool,
            quality_score=summary.quality_score,
            quality_risk=summary.quality_risk,
            summary=summary,
        )
        updated_session = session.model_copy(
            update={
                "updated_at": step.created_at,
                "baseline_run_id": session.baseline_run_id or summary.baseline_run_id,
                "status": "accepted" if summary.accepted else "active",
                "accepted_candidate_run_id": summary.candidate_run_id if summary.accepted else None,
                "steps": [step, *session.steps],
                "next_actions": _next_actions(summary),
            },
            deep=True,
        )
        sessions[session_index] = updated_session
        self._write_sessions(sorted(sessions, key=lambda item: item.updated_at, reverse=True))
        return updated_session

    def list_sessions(
        self,
        *,
        limit: int = 20,
        status: TuningSessionStatus | None = None,
    ) -> InteractiveTuningSessionList:
        """List persisted interactive tuning sessions."""
        sessions = self._read_sessions()
        active_count = sum(session.status == "active" for session in sessions)
        accepted_count = sum(session.status == "accepted" for session in sessions)
        if status is not None:
            sessions = [session for session in sessions if session.status == status]
        bounded_limit = max(1, min(limit, 100))
        return InteractiveTuningSessionList(
            sessions=sessions[:bounded_limit],
            total_count=len(sessions),
            active_count=active_count,
            accepted_count=accepted_count,
        )

    def export_session(
        self,
        session_id: str,
        *,
        output_format: Literal["markdown", "json"] = "markdown",
    ) -> InteractiveTuningSessionExport:
        """Export one interactive tuning session for handoff."""
        _, session = self._find_session(self._read_sessions(), session_id)
        if output_format == "json":
            content = json.dumps(
                {**session.model_dump(mode="json"), "step_count": session.step_count},
                indent=2,
                sort_keys=True,
            )
        else:
            content = _render_markdown_session(session)
        return InteractiveTuningSessionExport(
            format=output_format,
            content=content,
            session_id=session.session_id,
            status=session.status,
            step_count=session.step_count,
            accepted_candidate_run_id=session.accepted_candidate_run_id,
        )

    def _read_sessions(self) -> list[InteractiveTuningSession]:
        if not self.index_path.exists():
            return []
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        sessions: list[InteractiveTuningSession] = []
        for item in payload.get("sessions", []):
            session_payload = dict(item)
            session_payload.pop("step_count", None)
            sessions.append(InteractiveTuningSession.model_validate(session_payload))
        return sessions

    def _write_sessions(self, sessions: list[InteractiveTuningSession]) -> None:
        payload = {"sessions": [session.model_dump(mode="json", exclude={"step_count"}) for session in sessions]}
        self.index_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _find_session(
        self,
        sessions: list[InteractiveTuningSession],
        session_id: str,
    ) -> tuple[int, InteractiveTuningSession]:
        for index, session in enumerate(sessions):
            if session.session_id == session_id:
                return index, session
        raise FileNotFoundError(self.root / _SESSIONS_FILE / session_id)


def _normalize_targets(targets: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for target in targets:
        clean_target = target.strip()
        if clean_target and clean_target not in seen:
            normalized.append(clean_target)
            seen.add(clean_target)
    return normalized or ["image"]


def _next_actions(summary: TuningSessionSummary) -> list[str]:
    if summary.accepted:
        return ["Call `export_pipeline` or `export_tuning_session` for handoff."]
    if summary.recommended_next_tool == "adjust_pipeline":
        return ["Call `adjust_pipeline`, validate, and render the next candidate."]
    if summary.recommended_next_tool == "render_preview_batch":
        return ["Render another candidate preview before deciding."]
    return ["Ask the user for structured feedback tags before adjusting."]


def _render_markdown_session(session: InteractiveTuningSession) -> str:
    lines = [
        "# Interactive Tuning Session",
        "",
        f"- Session: {session.session_id}",
        f"- Task: {session.task}",
        f"- Status: {session.status}",
        f"- Baseline: {session.baseline_run_id or 'none'}",
        f"- Accepted candidate: {session.accepted_candidate_run_id or 'none'}",
        f"- Steps: {session.step_count}",
        "",
        "| Step | Candidate | Accepted | Score | Risk | Feedback | Notes |",
        "| ---: | --- | --- | ---: | --- | --- | --- |",
    ]
    for index, step in enumerate(reversed(session.steps), start=1):
        lines.append(
            "| "
            f"{index} | "
            f"{step.candidate_run_id} | "
            f"{str(step.accepted).lower()} | "
            f"{step.quality_score:.1f} | "
            f"{step.quality_risk} | "
            f"{', '.join(step.feedback_tags) or 'none'} | "
            f"{'; '.join(step.reviewer_notes)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
