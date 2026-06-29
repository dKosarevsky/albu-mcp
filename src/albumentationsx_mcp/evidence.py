"""Privacy-safe host evidence recording primitives for CLI adapters."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

HostName = Literal["Claude Desktop", "Claude Code", "Cursor", "Codex"]
HostStatus = Literal["passed", "blocked", "pending"]
HOST_NAMES: tuple[HostName, ...] = ("Claude Desktop", "Claude Code", "Cursor", "Codex")
P0_REQUIRED_HOSTS: tuple[HostName, ...] = ("Codex", "Claude Code")
P0_REQUIRED_GATES: tuple[str, ...] = ("manual_host_ui", "first_10_minutes_replay")
_NON_FABRICATION_POLICY = (
    "Record passed only after a reviewer observes the real MCP host UI flow; generated smoke output alone is not "
    "accepted as P0 evidence."
)


class HostManualRun(BaseModel):
    """One dated manual UI run record for an MCP host."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    host: HostName
    status: HostStatus
    date: date
    evidence: str = Field(min_length=1)


class FirstTenMinutesReplayRun(HostManualRun):
    """One dated first-10-minutes workflow replay record for an MCP host."""

    artifacts: list[str] = Field(default_factory=list)


class HostManualRuns(BaseModel):
    """Manual UI evidence records loaded from docs/HOST_MANUAL_RUNS.json."""

    model_config = ConfigDict(extra="forbid")

    manual_host_ui: list[HostManualRun] = Field(default_factory=list)
    first_10_minutes_replay: list[FirstTenMinutesReplayRun] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_unique_hosts(self) -> HostManualRuns:
        """Reject ambiguous overlays before generating host acceptance evidence."""
        _require_unique_hosts(self.manual_host_ui, label="manual host UI")
        _require_unique_hosts(self.first_10_minutes_replay, label="first 10 minutes replay")
        return self


@dataclass(frozen=True)
class FirstTenMinutesReplayEvidence:
    """Inputs for one first-10-minutes replay evidence record."""

    host: HostName
    status: HostStatus
    run_date: str
    evidence: str
    artifacts: list[str]


@dataclass(frozen=True)
class EvidenceArtifactImport:
    """Inputs for importing one reviewer-observed evidence session into required P0 gates."""

    path: Path
    host: HostName
    status: HostStatus
    run_date: str
    evidence: str
    artifacts: list[str]
    confirm_real_host_observed: bool = False


def validate_host_manual_runs(path: Path = Path("docs/HOST_MANUAL_RUNS.json")) -> HostManualRuns:
    """Load and validate manual host evidence records."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return HostManualRuns.model_validate(payload)
    except json.JSONDecodeError as exc:
        msg = f"{path}: invalid JSON: {exc.msg}"
        raise ValueError(msg) from exc
    except ValidationError as exc:
        msg = f"{path}: invalid manual host run records\n{exc}"
        raise ValueError(msg) from exc


def record_host_manual_run(
    *,
    path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    host: HostName,
    status: HostStatus,
    run_date: str,
    evidence: str,
) -> HostManualRuns:
    """Add or replace one manual host run record and return the validated payload."""
    current = validate_host_manual_runs(path) if path.exists() else HostManualRuns()
    record = HostManualRun(host=host, status=status, date=date.fromisoformat(run_date), evidence=evidence)
    by_host = {item.host: item for item in current.manual_host_ui}
    by_host[record.host] = record
    ordered = [by_host[name] for name in HOST_NAMES if name in by_host]
    updated = HostManualRuns(manual_host_ui=ordered, first_10_minutes_replay=current.first_10_minutes_replay)
    write_host_manual_runs(path, updated)
    return updated


def record_first_10_minutes_replay(
    *,
    path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    replay: FirstTenMinutesReplayEvidence,
) -> HostManualRuns:
    """Add or replace one first-10-minutes host replay record."""
    current = validate_host_manual_runs(path) if path.exists() else HostManualRuns()
    record = FirstTenMinutesReplayRun(
        host=replay.host,
        status=replay.status,
        date=date.fromisoformat(replay.run_date),
        evidence=replay.evidence,
        artifacts=replay.artifacts,
    )
    by_host = {item.host: item for item in current.first_10_minutes_replay}
    by_host[replay.host] = record
    ordered = [by_host[name] for name in HOST_NAMES if name in by_host]
    updated = HostManualRuns(manual_host_ui=current.manual_host_ui, first_10_minutes_replay=ordered)
    write_host_manual_runs(path, updated)
    return updated


def write_host_manual_runs(path: Path, payload: HostManualRuns) -> None:
    """Write host evidence records in the canonical JSON representation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(content, encoding="utf-8")


def summarize_host_manual_runs(records: HostManualRuns) -> str:
    """Return a compact human-readable evidence record count."""
    return (
        "host evidence records are valid "
        f"(manual_host_ui={len(records.manual_host_ui)}, "
        f"first_10_minutes_replay={len(records.first_10_minutes_replay)})"
    )


def build_evidence_session_plan(
    *,
    host: HostName,
    path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
) -> dict[str, Any]:
    """Build a guided real-host evidence session plan without writing evidence records."""
    records = validate_host_manual_runs(path) if path.exists() else HostManualRuns()
    host_status = _host_gate_status(host=host, records=records)
    return {
        "host": host,
        "records_path": str(path),
        "session_status": "ready_to_record" if host_status["overall_status"] == "passed" else "operator_run_required",
        "writes_records": False,
        "non_fabrication_policy": _NON_FABRICATION_POLICY,
        "current_host_status": host_status,
        "operator_steps": _operator_steps(host),
        "recording_commands": {
            "passed": (
                "albu-mcp evidence import-artifacts "
                f"--host {host!r} --status passed --date YYYY-MM-DD --evidence '...' "
                "--artifact docs/assets/demo/demo_report.md --confirm-real-host-observed"
            ),
            "blocked": (
                "albu-mcp evidence import-artifacts "
                f"--host {host!r} --status blocked --date YYYY-MM-DD --evidence '...'"
            ),
        },
    }


def import_evidence_artifacts(request: EvidenceArtifactImport) -> HostManualRuns:
    """Import one reviewer-observed host evidence session into both required P0 gates."""
    if request.status == "passed" and not request.confirm_real_host_observed:
        msg = "--confirm-real-host-observed is required when recording passed evidence"
        raise ValueError(msg)
    record_host_manual_run(
        path=request.path,
        host=request.host,
        status=request.status,
        run_date=request.run_date,
        evidence=request.evidence,
    )
    return record_first_10_minutes_replay(
        path=request.path,
        replay=FirstTenMinutesReplayEvidence(
            host=request.host,
            status=request.status,
            run_date=request.run_date,
            evidence=request.evidence,
            artifacts=request.artifacts,
        ),
    )


def build_evidence_doctor_report(path: Path = Path("docs/HOST_MANUAL_RUNS.json")) -> dict[str, Any]:
    """Inspect P0 host evidence records and return actionable remediation for missing gates."""
    records = validate_host_manual_runs(path) if path.exists() else HostManualRuns()
    host_statuses = {host: _host_gate_status(host=host, records=records) for host in P0_REQUIRED_HOSTS}
    flat_gates = [
        gate
        for status in host_statuses.values()
        for gate in [status["manual_host_ui"], status["first_10_minutes_replay"]]
    ]
    summary = {
        "required_gate_count": len(P0_REQUIRED_HOSTS) * len(P0_REQUIRED_GATES),
        "passed_gate_count": sum(gate == "passed" for gate in flat_gates),
        "blocked_gate_count": sum(gate == "blocked" for gate in flat_gates),
        "missing_gate_count": sum(gate == "missing" for gate in flat_gates),
    }
    return {
        "records_path": str(path),
        "rc_reopen_allowed": summary["passed_gate_count"] == summary["required_gate_count"],
        "non_fabrication_policy": _NON_FABRICATION_POLICY,
        "summary": summary,
        "host_statuses": host_statuses,
        "next_actions": _doctor_next_actions(summary),
    }


def _require_unique_hosts(records: Sequence[HostManualRun], *, label: str) -> None:
    seen: set[str] = set()
    for record in records:
        if record.host in seen:
            msg = f"Duplicate {label} record for {record.host!r}"
            raise ValueError(msg)
        seen.add(record.host)


def _host_gate_status(*, host: HostName, records: HostManualRuns) -> dict[str, Any]:
    manual = next((record for record in records.manual_host_ui if record.host == host), None)
    replay = next((record for record in records.first_10_minutes_replay if record.host == host), None)
    manual_status = manual.status if manual else "missing"
    replay_status = replay.status if replay else "missing"
    overall_status = _overall_host_status(manual_status=manual_status, replay_status=replay_status)
    return {
        "overall_status": overall_status,
        "manual_host_ui": manual_status,
        "first_10_minutes_replay": replay_status,
        "missing_gates": [
            gate
            for gate, status in [("manual_host_ui", manual_status), ("first_10_minutes_replay", replay_status)]
            if status != "passed"
        ],
        "remediation_actions": _remediation_actions(host=host, overall_status=overall_status),
    }


def _overall_host_status(*, manual_status: str, replay_status: str) -> str:
    if manual_status == "passed" and replay_status == "passed":
        return "passed"
    if manual_status == "blocked" or replay_status == "blocked":
        return "blocked"
    return "missing"


def _operator_steps(host: HostName) -> list[dict[str, str]]:
    return [
        {
            "step": "connect_host",
            "action": f"Open {host} with the AlbumentationsX MCP server configured and visible.",
        },
        {
            "step": "smoke_check",
            "action": "Call run_host_smoke_check and continue only when preview_ready is true.",
        },
        {
            "step": "first_preview",
            "action": "Replay the first-10-minutes workflow and keep redacted artifact references.",
        },
        {
            "step": "record",
            "action": "Run import-artifacts only after the reviewer observed the real host UI session.",
        },
    ]


def _remediation_actions(*, host: HostName, overall_status: str) -> list[dict[str, str]]:
    if overall_status == "passed":
        return []
    actions = {
        "Codex": [
            {
                "code": "run_codex_visible_tool_approval",
                "message": "Run Codex with visible MCP tool approval and complete run_host_smoke_check.",
            }
        ],
        "Claude Code": [
            {
                "code": "install_or_expose_claude_cli",
                "message": "Install or expose the Claude Code CLI, then import the AlbumentationsX MCP config.",
            }
        ],
        "Cursor": [
            {
                "code": "refresh_cursor_mcp_tools",
                "message": "Refresh Cursor MCP server discovery before running the preview smoke path.",
            }
        ],
        "Claude Desktop": [
            {
                "code": "refresh_claude_desktop_config",
                "message": "Reload Claude Desktop MCP config and confirm AlbumentationsX tools are listed.",
            }
        ],
    }
    return actions[host]


def _doctor_next_actions(summary: dict[str, int]) -> list[str]:
    if summary["passed_gate_count"] == summary["required_gate_count"]:
        return ["Run albu-mcp rc reopen --format json and review the publish decision."]
    return [
        "Run albu-mcp evidence run-session for each missing or blocked host.",
        "Record passed evidence only with --confirm-real-host-observed after a reviewer observes the real host UI.",
        "Rerun albu-mcp evidence doctor before attempting RC reopen.",
    ]
