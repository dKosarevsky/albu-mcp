"""Export the manual host evidence sprint board without fabricating evidence."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_v1_launch_report import build_v1_launch_report

_HOST_ORDER = ("Codex", "Claude Code", "Cursor", "Claude Desktop")
_P0_HOSTS = frozenset({"Codex", "Claude Code"})


def build_host_evidence_sprint_board() -> dict[str, Any]:
    """Build a deterministic sprint board for manual host evidence collection."""
    report = build_v1_launch_report()
    evidence_by_host = {item["host"]: item for item in report["evidence_plan"]}
    hosts = [_host_row(evidence_by_host[host]) for host in _HOST_ORDER]
    return {
        "package": report["package"],
        "version": report["package_version"],
        "ready_for_v1": report["ready_for_v1"],
        "manual_evidence_policy": "Never mark a host passed until a reviewer runs the real host UI.",
        "summary": {
            "host_count": len(hosts),
            "passed_manual_host_ui": sum(host["manual_host_ui_status"] == "recorded" for host in hosts),
            "passed_first_10_minutes_replay": sum(
                host["first_10_minutes_replay_status"] == "recorded" for host in hosts
            ),
            "blocked_hosts": sum(host["next_gate"] == "blocked" for host in hosts),
        },
        "hosts": hosts,
        "next_checks": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/check_first_10_minutes_replay.py",
            "uv run python scripts/check_manual_host_acceptance.py",
            "uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md",
            "uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md",
            "uv run python scripts/export_host_evidence_sprint_board.py --output docs/HOST_EVIDENCE_SPRINT_BOARD.md",
        ],
    }


def render_host_evidence_sprint_board_markdown(board: dict[str, Any]) -> str:
    """Render the manual host evidence sprint board as Markdown."""
    lines = [
        "# Host Evidence Sprint Board",
        "",
        f"Package: `{board['package']}=={board['version']}`",
        f"Ready for v1: `{str(board['ready_for_v1']).lower()}`",
        "",
        "## Manual Evidence Policy",
        "",
        f"{board['manual_evidence_policy']} Do not paste synthetic evidence or mark generated smoke checks as host UI.",
        "",
        "## Summary",
        "",
        f"- Hosts: `{board['summary']['host_count']}`",
        f"- Passed manual Host UI: `{board['summary']['passed_manual_host_ui']}`",
        f"- Passed First 10 Minutes replay: `{board['summary']['passed_first_10_minutes_replay']}`",
        f"- Blocked hosts: `{board['summary']['blocked_hosts']}`",
        "",
        "## Sprint Board",
        "",
        "| Host | Priority | Manual UI | First 10 Minutes | Next Gate |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        "| "
        f"{host['host']} | "
        f"`{host['priority']}` | "
        f"`{host['manual_host_ui_status']}` | "
        f"`{host['first_10_minutes_replay_status']}` | "
        f"`{host['next_gate']}` |"
        for host in board["hosts"]
    )
    lines.extend(["", "## Host Commands", ""])
    for host in board["hosts"]:
        lines.extend(
            [
                f"### {host['host']}",
                "",
                "```bash",
                host["record_first_10_minutes_command"],
                host["record_manual_host_ui_command"],
                host["verify_first_10_minutes_command"],
                host["verify_manual_host_ui_command"],
                "```",
                "",
            ]
        )
    lines.extend(["## Next Checks", ""])
    lines.extend(f"- `{command}`" for command in board["next_checks"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for the manual host evidence sprint board."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_host_evidence_sprint_board_markdown(build_host_evidence_sprint_board())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _host_row(item: dict[str, Any]) -> dict[str, str]:
    manual = item["manual_host_ui"]
    replay = item["first_10_minutes_replay"]
    host = item["host"]
    return {
        "host": host,
        "priority": "p0" if host in _P0_HOSTS else "p1",
        "manual_host_ui_status": manual["status"],
        "first_10_minutes_replay_status": replay["status"],
        "next_gate": _next_gate(manual["status"], replay["status"]),
        "record_manual_host_ui_command": item["record_commands"]["manual_host_ui"],
        "record_first_10_minutes_command": item["record_commands"]["first_10_minutes_replay"],
        "verify_manual_host_ui_command": _verify_manual_host_ui_command(host),
        "verify_first_10_minutes_command": _verify_first_10_minutes_command(host),
    }


def _next_gate(manual_status: str, replay_status: str) -> str:
    if manual_status == "blocked" or replay_status == "blocked":
        return "blocked"
    if replay_status != "recorded":
        return "first_10_minutes_replay"
    if manual_status != "recorded":
        return "manual_host_ui"
    return "complete"


def _verify_manual_host_ui_command(host: str) -> str:
    return " ".join(
        shlex.quote(part) for part in ["uv", "run", "python", "scripts/check_manual_host_acceptance.py", "--host", host]
    )


def _verify_first_10_minutes_command(host: str) -> str:
    return " ".join(
        shlex.quote(part)
        for part in ["uv", "run", "python", "scripts/check_first_10_minutes_replay.py", "--host", host]
    )


if __name__ == "__main__":
    main()
