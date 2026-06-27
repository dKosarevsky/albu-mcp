"""Export a P0 host evidence ledger from committed manual run records."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_host_manual_runs import HostManualRun, HostManualRuns, validate_host_manual_runs

_P0_HOSTS = ("Codex", "Claude Code")
_GATES = ("first_10_minutes_replay", "manual_host_ui")
_DEFAULT_RECORDS_PATH = Path("docs/HOST_MANUAL_RUNS.json")


def build_p0_host_evidence_ledger(records_path: Path = _DEFAULT_RECORDS_PATH) -> dict[str, Any]:
    """Build the P0 evidence ledger without fabricating host evidence."""
    records = validate_host_manual_runs(records_path) if records_path.exists() else HostManualRuns()
    host_gates = [_host_gate_records(host=host, records=records) for host in _P0_HOSTS]
    gates = [gate for host in host_gates for gate in host["gates"]]
    passed_count = sum(gate["record_status"] == "passed" for gate in gates)
    blocked_count = sum(gate["record_status"] == "blocked" for gate in gates)
    missing_count = sum(gate["record_status"] in {"missing", "pending"} for gate in gates)
    return {
        "records_path": str(records_path),
        "target_hosts": list(_P0_HOSTS),
        "ledger_status": "ready_for_rc"
        if passed_count == len(gates) and blocked_count == 0
        else "manual_evidence_required",
        "non_fabrication_policy": "Only docs/HOST_MANUAL_RUNS.json can satisfy a P0 gate.",
        "summary": {
            "required_gate_count": len(gates),
            "recorded_gate_count": passed_count,
            "missing_gate_count": missing_count,
            "blocked_gate_count": blocked_count,
        },
        "host_gates": host_gates,
        "after_recording_commands": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md",
            "uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md",
            "uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md",
            "uv run python scripts/check_release_readiness.py",
        ],
    }


def render_p0_host_evidence_ledger_markdown(ledger: dict[str, Any]) -> str:
    """Render the P0 host evidence ledger as Markdown."""
    lines = [
        "# P0 Host Evidence Ledger",
        "",
        f"Records path: `{ledger['records_path']}`",
        f"Target hosts: `{', '.join(ledger['target_hosts'])}`",
        f"Ledger status: `{ledger['ledger_status']}`",
        "",
        "## Non-Fabrication Policy",
        "",
        ledger["non_fabrication_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in ledger["summary"].items())
    lines.extend(
        [
            "",
            "## Gate Records",
            "",
            "| Host | Gate | Record Status | Date | Evidence | Record Command |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for host in ledger["host_gates"]:
        lines.extend(
            "| "
            f"{host['host']} | "
            f"`{gate['gate']}` | "
            f"`{gate['record_status']}` | "
            f"`{gate['date']}` | "
            f"{gate['evidence']} | "
            f"`{gate['record_command']}` |"
            for gate in host["gates"]
        )
    lines.extend(["", "## After Recording", ""])
    lines.extend(f"- `{command}`" for command in ledger["after_recording_commands"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for P0 host evidence ledger exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=_DEFAULT_RECORDS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_p0_host_evidence_ledger_markdown(build_p0_host_evidence_ledger(args.records))
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _host_gate_records(*, host: str, records: HostManualRuns) -> dict[str, Any]:
    manual_by_host = {record.host: record for record in records.manual_host_ui}
    replay_by_host = {record.host: record for record in records.first_10_minutes_replay}
    record_by_gate = {
        "first_10_minutes_replay": replay_by_host.get(host),
        "manual_host_ui": manual_by_host.get(host),
    }
    return {
        "host": host,
        "gates": [_gate_record(host=host, gate=gate, record=record_by_gate[gate]) for gate in _GATES],
    }


def _gate_record(*, host: str, gate: str, record: HostManualRun | None) -> dict[str, str]:
    return {
        "gate": gate,
        "record_status": record.status if record is not None else "missing",
        "date": record.date.isoformat() if record is not None else "not_recorded",
        "evidence": record.evidence if record is not None else "No reviewer-observed real UI evidence recorded.",
        "record_command": _record_command(host=host, gate=gate),
    }


def _record_command(*, host: str, gate: str) -> str:
    args = ["uv", "run", "python", "scripts/record_host_manual_run.py"]
    if gate == "first_10_minutes_replay":
        args.extend(["--kind", "first-10-minutes"])
    args.extend(["--host", host, "--status", "passed", "--date", "YYYY-MM-DD", "--evidence", "<redacted evidence>"])
    if gate == "first_10_minutes_replay":
        args.extend(["--artifact", "docs/assets/demo/demo_report.md"])
    return " ".join(shlex.quote(arg) for arg in args)


if __name__ == "__main__":
    main()
