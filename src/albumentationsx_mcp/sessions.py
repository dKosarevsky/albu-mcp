"""JSON-backed interactive tuning session store."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from albumentationsx_mcp.models import (
    ArtifactRef,
    InteractiveTuningSession,
    InteractiveTuningSessionCleanup,
    InteractiveTuningSessionExport,
    InteractiveTuningSessionList,
    InteractiveTuningStep,
    QualityProfileName,
    TuningSessionStatus,
    TuningSessionSummary,
)

_SESSIONS_FILE = "tuning_sessions.json"
_SESSION_EXPORT_MIME_TYPES: dict[Literal["markdown", "json"], str] = {
    "markdown": "text/markdown",
    "json": "application/json",
}
_SESSION_EXPORT_SUFFIXES: dict[Literal["markdown", "json"], str] = {
    "markdown": "md",
    "json": "json",
}
_SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_.-]+")


class InteractiveTuningSessionStore:
    """Small JSON-backed journal for multi-step preview tuning sessions."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / _SESSIONS_FILE
        self.export_root = self.root / "tuning-sessions"
        self.export_root.mkdir(parents=True, exist_ok=True)

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

    def close_session(
        self,
        session_id: str,
        *,
        status: Literal["accepted", "rejected"],
        accepted_candidate_run_id: str | None = None,
        note: str | None = None,
    ) -> InteractiveTuningSession:
        """Close a session as accepted or rejected without adding another comparison step."""
        sessions = self._read_sessions()
        session_index, session = self._find_session(sessions, session_id)
        now = _utc_now()
        accepted_candidate = _accepted_candidate_for_close(session, accepted_candidate_run_id)
        if status == "accepted" and accepted_candidate is None:
            msg = "accepted sessions require an accepted_candidate_run_id or an accepted recorded step"
            raise ValueError(msg)
        updated_session = session.model_copy(
            update={
                "updated_at": now,
                "closed_at": now,
                "archived_at": None,
                "status": status,
                "status_note": note,
                "accepted_candidate_run_id": accepted_candidate if status == "accepted" else None,
                "next_actions": _closed_next_actions(status),
            },
            deep=True,
        )
        sessions[session_index] = updated_session
        self._write_sessions(sorted(sessions, key=lambda item: item.updated_at, reverse=True))
        return updated_session

    def archive_session(self, session_id: str, *, note: str | None = None) -> InteractiveTuningSession:
        """Archive a session so normal active/accepted/rejected lists can ignore it."""
        sessions = self._read_sessions()
        session_index, session = self._find_session(sessions, session_id)
        now = _utc_now()
        updated_session = session.model_copy(
            update={
                "updated_at": now,
                "archived_at": now,
                "status": "archived",
                "status_note": note,
                "next_actions": ["Session archived."],
            },
            deep=True,
        )
        sessions[session_index] = updated_session
        self._write_sessions(sorted(sessions, key=lambda item: item.updated_at, reverse=True))
        return updated_session

    def cleanup_sessions(
        self,
        *,
        keep_last: int = 100,
        include_active: bool = False,
    ) -> InteractiveTuningSessionCleanup:
        """Delete older persisted sessions while protecting active sessions by default."""
        sessions = self._read_sessions()
        bounded_keep = max(0, min(keep_last, 1000))
        protected = [session for session in sessions if session.status == "active" and not include_active]
        cleanup_candidates = [session for session in sessions if include_active or session.status != "active"]
        kept_candidate_ids = {session.session_id for session in cleanup_candidates[:bounded_keep]}
        deleted = [
            session for session in cleanup_candidates[bounded_keep:] if session.session_id not in kept_candidate_ids
        ]
        deleted_ids = {session.session_id for session in deleted}
        remaining = [session for session in sessions if session.session_id not in deleted_ids]
        self._write_sessions(remaining)
        return InteractiveTuningSessionCleanup(
            deleted_sessions=deleted,
            deleted_count=len(deleted),
            kept_count=len(remaining),
            protected_active_count=len(protected),
        )

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
        rejected_count = sum(session.status == "rejected" for session in sessions)
        archived_count = sum(session.status == "archived" for session in sessions)
        if status is not None:
            sessions = [session for session in sessions if session.status == status]
        bounded_limit = max(1, min(limit, 100))
        return InteractiveTuningSessionList(
            sessions=sessions[:bounded_limit],
            total_count=len(sessions),
            active_count=active_count,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            archived_count=archived_count,
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
        path = self._export_path(session.session_id, output_format)
        path.write_text(content, encoding="utf-8")
        return InteractiveTuningSessionExport(
            format=output_format,
            content=content,
            artifact=self._artifact_ref(path, mime_type=_SESSION_EXPORT_MIME_TYPES[output_format]),
            session_id=session.session_id,
            status=session.status,
            step_count=session.step_count,
            accepted_candidate_run_id=session.accepted_candidate_run_id,
        )

    def _export_path(self, session_id: str, output_format: Literal["markdown", "json"]) -> Path:
        safe_session = _safe_name(session_id or "session")
        suffix = _SESSION_EXPORT_SUFFIXES[output_format]
        return self.export_root / f"tuning-session-{safe_session}.{suffix}"

    def _artifact_ref(self, path: Path, *, mime_type: str) -> ArtifactRef:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return ArtifactRef(
            kind="report",
            uri=f"artifact://{path.relative_to(self.root)}",
            path=str(path),
            mime_type=mime_type,
            sha256=digest,
            size_bytes=path.stat().st_size,
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


def _safe_name(value: str) -> str:
    safe = _SAFE_NAME_PATTERN.sub("-", value).strip("-")
    return safe or "session"


def _next_actions(summary: TuningSessionSummary) -> list[str]:
    if summary.accepted:
        return ["Call `export_pipeline` or `export_tuning_session` for handoff."]
    if summary.recommended_next_tool == "adjust_pipeline":
        return ["Call `adjust_pipeline`, validate, and render the next candidate."]
    if summary.recommended_next_tool == "render_preview_batch":
        return ["Render another candidate preview before deciding."]
    return ["Ask the user for structured feedback tags before adjusting."]


def _closed_next_actions(status: Literal["accepted", "rejected"]) -> list[str]:
    if status == "accepted":
        return ["Session closed as accepted. Call `export_pipeline` or `export_tuning_session` for handoff."]
    return ["Session closed as rejected. Call `export_tuning_session` for audit."]


def _accepted_candidate_for_close(
    session: InteractiveTuningSession,
    accepted_candidate_run_id: str | None,
) -> str | None:
    if accepted_candidate_run_id is not None:
        known_candidates = {step.candidate_run_id for step in session.steps}
        if known_candidates and accepted_candidate_run_id not in known_candidates:
            msg = f"accepted_candidate_run_id {accepted_candidate_run_id!r} does not match a recorded session step"
            raise ValueError(msg)
        return accepted_candidate_run_id
    if session.accepted_candidate_run_id is not None:
        return session.accepted_candidate_run_id
    accepted_steps = [step for step in session.steps if step.accepted]
    return accepted_steps[0].candidate_run_id if accepted_steps else None


def _render_markdown_session(session: InteractiveTuningSession) -> str:
    lines = [
        "# Interactive Tuning Session",
        "",
        f"- Session: {session.session_id}",
        f"- Task: {session.task}",
        f"- Status: {session.status}",
        f"- Status note: {session.status_note or 'none'}",
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
