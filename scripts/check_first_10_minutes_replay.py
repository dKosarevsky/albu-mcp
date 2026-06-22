"""Require dated first-10-minutes MCP host replay evidence for selected hosts."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_host_manual_runs import HOST_NAMES, HostName, validate_host_manual_runs

_DEFAULT_MANUAL_RUNS_PATH = Path("docs/HOST_MANUAL_RUNS.json")


@dataclass(frozen=True)
class FirstTenMinutesReplayCheck:
    """One first-10-minutes replay evidence requirement result."""

    host: HostName
    status: str
    ok: bool
    message: str
    date: str = "none"
    evidence: str = "first 10 minutes replay not recorded"
    artifacts: list[str] | None = None


@dataclass(frozen=True)
class FirstTenMinutesReplayReport:
    """Aggregate result for required first-10-minutes host replays."""

    checks: list[FirstTenMinutesReplayCheck]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)


def check_first_10_minutes_replay(
    path: Path = _DEFAULT_MANUAL_RUNS_PATH,
    *,
    required_hosts: tuple[HostName, ...] = HOST_NAMES,
) -> FirstTenMinutesReplayReport:
    """Return whether all required hosts have dated passed first-10-minutes replay evidence."""
    manual_runs = validate_host_manual_runs(path)
    by_host = {record.host: record for record in manual_runs.first_10_minutes_replay}
    checks: list[FirstTenMinutesReplayCheck] = []
    for host in required_hosts:
        record = by_host.get(host)
        if record is None:
            checks.append(
                FirstTenMinutesReplayCheck(
                    host=host,
                    status="pending",
                    ok=False,
                    message="first 10 minutes replay not recorded",
                    artifacts=[],
                )
            )
            continue
        status = record.status
        ok = status == "passed"
        checks.append(
            FirstTenMinutesReplayCheck(
                host=host,
                status=status,
                ok=ok,
                message=_message_for_status(host=host, status=status),
                date=record.model_dump(mode="json")["date"],
                evidence=record.evidence,
                artifacts=record.artifacts,
            )
        )
    return FirstTenMinutesReplayReport(checks=checks)


def main() -> None:
    """CLI entrypoint for final first-10-minutes replay gates."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=_DEFAULT_MANUAL_RUNS_PATH)
    parser.add_argument(
        "--host",
        action="append",
        choices=HOST_NAMES,
        help="Required host. Repeat to check a subset. Defaults to all supported hosts.",
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    required_hosts = tuple(args.host) if args.host else HOST_NAMES
    report = check_first_10_minutes_replay(args.path, required_hosts=required_hosts)
    if args.format == "json":
        sys.stdout.write(json.dumps({"ok": report.ok, "checks": [asdict(check) for check in report.checks]}, indent=2))
        sys.stdout.write("\n")
    elif report.ok:
        hosts = ", ".join(check.host for check in report.checks)
        sys.stdout.write(f"first-10-minutes replay passed: {hosts}\n")

    if report.ok:
        return

    if args.format == "text":
        for check in report.checks:
            if not check.ok:
                sys.stderr.write(f"[{check.host}] {check.message}\n")
    raise SystemExit(1)


def _message_for_status(*, host: HostName, status: str) -> str:
    if status == "passed":
        return f"{host} has dated passed first 10 minutes replay evidence"
    if status == "blocked":
        return f"{host} first 10 minutes replay is blocked"
    return f"{host} first 10 minutes replay is pending"


if __name__ == "__main__":
    main()
