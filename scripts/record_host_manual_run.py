"""Record or replace one dated manual MCP host acceptance result."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_host_manual_runs import (
    HOST_NAMES,
    FirstTenMinutesReplayRun,
    HostManualRun,
    HostManualRuns,
    HostName,
    HostStatus,
    validate_host_manual_runs,
)


@dataclass(frozen=True)
class FirstTenMinutesReplayEvidence:
    """Inputs for one first-10-minutes replay evidence record."""

    host: HostName
    status: HostStatus
    run_date: str
    evidence: str
    artifacts: list[str]


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
    _write_manual_runs(path, updated)
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
    _write_manual_runs(path, updated)
    return updated


def main() -> None:
    """CLI entrypoint for reviewers recording host UI evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kind",
        choices=["host-ui", "first-10-minutes"],
        default="host-ui",
        help="Evidence record type to write.",
    )
    parser.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    parser.add_argument("--host", choices=get_args(HostName), required=True)
    parser.add_argument("--status", choices=get_args(HostStatus), required=True)
    parser.add_argument("--date", required=True, help="ISO date, for example 2026-06-19.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Artifact path or URL for first-10-minutes replay evidence. Can be repeated.",
    )
    args = parser.parse_args()

    try:
        if args.kind == "first-10-minutes":
            record_first_10_minutes_replay(
                path=args.path,
                replay=FirstTenMinutesReplayEvidence(
                    host=args.host,
                    status=args.status,
                    run_date=args.date,
                    evidence=args.evidence,
                    artifacts=args.artifact,
                ),
            )
        else:
            record_host_manual_run(
                path=args.path,
                host=args.host,
                status=args.status,
                run_date=args.date,
                evidence=args.evidence,
            )
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc
    if args.kind == "first-10-minutes":
        sys.stdout.write(f"recorded first-10-minutes {args.host} {args.status} on {args.date} in {args.path}\n")
    else:
        sys.stdout.write(f"recorded {args.host} {args.status} on {args.date} in {args.path}\n")


def _write_manual_runs(path: Path, payload: HostManualRuns) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
