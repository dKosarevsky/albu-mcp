"""Privacy-safe host evidence recording primitives for CLI adapters."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

HostName = Literal["Claude Desktop", "Claude Code", "Cursor", "Codex"]
HostStatus = Literal["passed", "blocked", "pending"]
HOST_NAMES: tuple[HostName, ...] = ("Claude Desktop", "Claude Code", "Cursor", "Codex")


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


def _require_unique_hosts(records: Sequence[HostManualRun], *, label: str) -> None:
    seen: set[str] = set()
    for record in records:
        if record.host in seen:
            msg = f"Duplicate {label} record for {record.host!r}"
            raise ValueError(msg)
        seen.add(record.host)
