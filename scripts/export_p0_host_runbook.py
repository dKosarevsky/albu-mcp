"""Export a focused P0 host runbook for v1 RC evidence collection."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_host_evidence_sprint_board import build_host_evidence_sprint_board

_P0_HOSTS = ("Codex", "Claude Code")


def build_p0_host_runbook() -> dict[str, Any]:
    """Build a P0-only host runbook without claiming host evidence."""
    board = build_host_evidence_sprint_board()
    run_queue = [_runbook_item(item) for item in board["run_queue"] if item["host"] in _P0_HOSTS]
    return {
        "package": board["package"],
        "version": board["version"],
        "ready_for_v1": board["ready_for_v1"],
        "target_hosts": list(_P0_HOSTS),
        "non_fabrication_policy": board["manual_evidence_policy"],
        "run_queue": run_queue,
        "after_p0_commands": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md",
            "uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md",
            "uv run python scripts/check_release_readiness.py",
        ],
    }


def render_p0_host_runbook_markdown(runbook: dict[str, Any]) -> str:
    """Render the P0 host runbook as Markdown."""
    lines = [
        "# P0 Host Runbook",
        "",
        f"Package: `{runbook['package']}=={runbook['version']}`",
        f"Target hosts: `{', '.join(runbook['target_hosts'])}`",
        f"Ready for v1: `{str(runbook['ready_for_v1']).lower()}`",
        "",
        "## Evidence Policy",
        "",
        f"{runbook['non_fabrication_policy']} Keep hosts pending or blocked until the real UI run is observed.",
        "",
        "## P0 Queue",
        "",
        "| Order | Host | Next Action | Packet |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| {item['run_order']} | {item['host']} | `{item['next_action']}` | `{item['packet_command']}` |"
        for item in runbook["run_queue"]
    )
    lines.extend(["", "## Record Commands", ""])
    for item in runbook["run_queue"]:
        lines.extend(
            [
                f"### {item['host']}",
                "",
                "```bash",
                item["first_10_minutes_record_command"],
                item["manual_record_command"],
                "```",
                "",
            ]
        )
    lines.extend(["## After P0 Runs", ""])
    lines.extend(f"- `{command}`" for command in runbook["after_p0_commands"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for P0 host runbook exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_p0_host_runbook_markdown(build_p0_host_runbook())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _runbook_item(item: dict[str, Any]) -> dict[str, Any]:
    host = item["host"]
    return {
        "run_order": len([candidate for candidate in _P0_HOSTS if _P0_HOSTS.index(candidate) <= _P0_HOSTS.index(host)]),
        "host": host,
        "priority": item["priority"],
        "next_action": item["next_action"],
        "packet_command": item["packet_command"],
        "manual_record_command": _record_command(host=host, kind="manual_host_ui"),
        "first_10_minutes_record_command": _record_command(host=host, kind="first_10_minutes_replay"),
    }


def _record_command(*, host: str, kind: str) -> str:
    args = ["uv", "run", "python", "scripts/record_host_manual_run.py"]
    if kind == "first_10_minutes_replay":
        args.extend(["--kind", "first-10-minutes"])
    args.extend(
        [
            "--host",
            host,
            "--status",
            "passed",
            "--date",
            "YYYY-MM-DD",
            "--evidence",
            _evidence_placeholder(host=host, kind=kind),
        ]
    )
    if kind == "first_10_minutes_replay":
        args.extend(["--artifact", "docs/assets/demo/demo_report.md"])
    return " ".join(shlex.quote(arg) for arg in args)


def _evidence_placeholder(*, host: str, kind: str) -> str:
    if kind == "first_10_minutes_replay":
        return (
            f"{host} completed First 10 Minutes smoke, validation, baseline/candidate render, "
            "comparison, and export in the real host UI."
        )
    return f"{host} listed AlbumentationsX MCP tools/resources and completed run_host_smoke_check in the real host UI."


if __name__ == "__main__":
    main()
