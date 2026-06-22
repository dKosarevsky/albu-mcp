"""Validate dated manual MCP host acceptance records."""

from __future__ import annotations

import argparse
import json
import sys
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


def _require_unique_hosts(records: list[HostManualRun], *, label: str) -> None:
    seen: set[str] = set()
    for record in records:
        if record.host in seen:
            msg = f"Duplicate {label} record for {record.host!r}"
            raise ValueError(msg)
        seen.add(record.host)


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


def main() -> None:
    """CLI entrypoint for CI and release checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    args = parser.parse_args()
    report = validate_host_manual_runs(args.path)
    sys.stdout.write(
        "manual host run records are valid "
        f"({len(report.manual_host_ui)} host UI, {len(report.first_10_minutes_replay)} first-10-minutes replay)\n"
    )


if __name__ == "__main__":
    main()
