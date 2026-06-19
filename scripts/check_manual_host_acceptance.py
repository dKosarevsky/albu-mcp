"""Require dated manual MCP host UI evidence for selected hosts."""

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
class ManualHostAcceptanceCheck:
    """One manual host evidence requirement result."""

    host: HostName
    status: str
    ok: bool
    message: str
    date: str = "none"
    evidence: str = "manual UI run not recorded"


@dataclass(frozen=True)
class ManualHostAcceptanceReport:
    """Aggregate result for required manual MCP host UI runs."""

    checks: list[ManualHostAcceptanceCheck]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)


def check_manual_host_acceptance(
    path: Path = _DEFAULT_MANUAL_RUNS_PATH,
    *,
    required_hosts: tuple[HostName, ...] = HOST_NAMES,
) -> ManualHostAcceptanceReport:
    """Return whether all required hosts have dated passed manual UI evidence."""
    manual_runs = validate_host_manual_runs(path)
    by_host = {record.host: record for record in manual_runs.manual_host_ui}
    checks: list[ManualHostAcceptanceCheck] = []
    for host in required_hosts:
        record = by_host.get(host)
        if record is None:
            checks.append(
                ManualHostAcceptanceCheck(
                    host=host,
                    status="pending",
                    ok=False,
                    message="manual UI run not recorded",
                )
            )
            continue
        status = record.status
        ok = status == "passed"
        checks.append(
            ManualHostAcceptanceCheck(
                host=host,
                status=status,
                ok=ok,
                message=_message_for_status(host=host, status=status),
                date=record.model_dump(mode="json")["date"],
                evidence=record.evidence,
            )
        )
    return ManualHostAcceptanceReport(checks=checks)


def main() -> None:
    """CLI entrypoint for final manual host UI acceptance gates."""
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
    report = check_manual_host_acceptance(args.path, required_hosts=required_hosts)
    if args.format == "json":
        sys.stdout.write(json.dumps({"ok": report.ok, "checks": [asdict(check) for check in report.checks]}, indent=2))
        sys.stdout.write("\n")
    elif report.ok:
        hosts = ", ".join(check.host for check in report.checks)
        sys.stdout.write(f"manual host acceptance passed: {hosts}\n")

    if report.ok:
        return

    if args.format == "text":
        for check in report.checks:
            if check.ok:
                continue
            sys.stderr.write(f"[{check.host}] {check.message}\n")
    raise SystemExit(1)


def _message_for_status(*, host: HostName, status: str) -> str:
    if status == "passed":
        return f"{host} has dated passed manual UI evidence"
    if status == "blocked":
        return f"{host} manual UI run is blocked"
    return f"{host} manual UI run is pending"


if __name__ == "__main__":
    main()
