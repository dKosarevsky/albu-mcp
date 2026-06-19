"""Record or replace one dated manual MCP host acceptance result."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_host_manual_runs import (
    HOST_NAMES,
    HostManualRun,
    HostManualRuns,
    HostName,
    HostStatus,
    validate_host_manual_runs,
)


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
    updated = HostManualRuns(manual_host_ui=ordered)
    _write_manual_runs(path, updated)
    return updated


def main() -> None:
    """CLI entrypoint for reviewers recording host UI evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    parser.add_argument("--host", choices=get_args(HostName), required=True)
    parser.add_argument("--status", choices=get_args(HostStatus), required=True)
    parser.add_argument("--date", required=True, help="ISO date, for example 2026-06-19.")
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()

    try:
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
    sys.stdout.write(f"recorded {args.host} {args.status} on {args.date} in {args.path}\n")


def _write_manual_runs(path: Path, payload: HostManualRuns) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
