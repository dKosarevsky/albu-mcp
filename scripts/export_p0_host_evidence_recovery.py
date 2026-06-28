"""Export a focused recovery packet for reopening P0 real-host evidence gates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_claude_code_setup_path import build_claude_code_setup_path
from scripts.export_codex_cancellation_triage import build_codex_cancellation_triage
from scripts.export_host_evidence_runner import build_host_evidence_runner
from scripts.export_p0_evidence_status import build_p0_evidence_status


def build_p0_host_evidence_recovery() -> dict[str, Any]:
    """Build the current P0 host evidence recovery view without fabricating passed evidence."""
    status = build_p0_evidence_status()
    runner = build_host_evidence_runner()
    codex = build_codex_cancellation_triage()
    claude = build_claude_code_setup_path()
    blocked_gate_count = status["summary"]["blocked_gate_count"]
    return {
        "recovery_status": "blocked_until_real_host_evidence" if blocked_gate_count else "ready_for_rc_gate_recheck",
        "rc_ready": status["rc_ready"],
        "rc_reopen_allowed": runner["rc_reopen_allowed"] and blocked_gate_count == 0,
        "summary": {
            "target_host_count": runner["summary"]["target_host_count"],
            "required_gate_count": status["summary"]["required_gate_count"],
            "passed_gate_count": status["summary"]["passed_gate_count"],
            "blocked_gate_count": blocked_gate_count,
            "missing_gate_count": status["summary"]["missing_gate_count"],
        },
        "recovery_policy": (
            "Do not replace blocked P0 records until Codex and Claude Code complete the real MCP host flow and "
            "leave dated reviewer-observed evidence."
        ),
        "host_recovery_lanes": [
            _host_recovery_lane(
                {
                    "host": "Codex",
                    "blocker": codex["failure_class"],
                    "status": codex["triage_status"],
                    "gates": codex["affected_gates"],
                    "next_doc": "docs/CODEX_CANCELLATION_TRIAGE.md",
                    "first_action": "Run Codex with visible MCP tool approval and complete run_host_smoke_check.",
                }
            ),
            _host_recovery_lane(
                {
                    "host": "Claude Code",
                    "blocker": claude["failure_class"],
                    "status": claude["setup_status"],
                    "gates": claude["affected_gates"],
                    "next_doc": "docs/CLAUDE_CODE_SETUP_PATH.md",
                    "first_action": (
                        "Install or expose the Claude Code CLI, then import the AlbumentationsX MCP config."
                    ),
                }
            ),
        ],
        "post_recovery_commands": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md",
            "uv run python scripts/export_p0_host_evidence_recovery.py --output docs/P0_HOST_EVIDENCE_RECOVERY.md",
            "uv run python scripts/export_rc_dry_run.py --output docs/RC_DRY_RUN.md",
            "uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json",
        ],
        "source_docs": [
            "docs/P0_EVIDENCE_STATUS.md",
            "docs/HOST_EVIDENCE_RUNNER.md",
            "docs/CODEX_CANCELLATION_TRIAGE.md",
            "docs/CLAUDE_CODE_SETUP_PATH.md",
            "docs/HOST_MANUAL_RUNS.json",
        ],
    }


def render_p0_host_evidence_recovery_markdown(recovery: dict[str, Any]) -> str:
    """Render the P0 host evidence recovery packet as Markdown."""
    lines = [
        "# P0 Host Evidence Recovery",
        "",
        f"Recovery status: `{recovery['recovery_status']}`",
        f"RC ready: `{str(recovery['rc_ready']).lower()}`",
        f"RC reopen allowed: `{str(recovery['rc_reopen_allowed']).lower()}`",
        "",
        "## Recovery Policy",
        "",
        recovery["recovery_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in recovery["summary"].items())
    lines.extend(
        [
            "",
            "## Host Recovery Lanes",
            "",
            "| Host | Status | Blocker | Gates | First Action | Next Doc |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"{lane['host']} | "
        f"`{lane['status']}` | "
        f"`{lane['blocker']}` | "
        f"{', '.join(f'`{gate}`' for gate in lane['gates'])} | "
        f"{lane['first_action']} | "
        f"`{lane['next_doc']}` |"
        for lane in recovery["host_recovery_lanes"]
    )
    lines.extend(["", "## Record Commands", ""])
    for lane in recovery["host_recovery_lanes"]:
        lines.extend([f"### {lane['host']}", "", "Passed evidence:"])
        lines.extend(f"- `{command}`" for command in lane["passed_record_commands"])
        lines.extend(["", "Blocked evidence:"])
        lines.extend(f"- `{command}`" for command in lane["blocked_record_commands"])
        lines.append("")
    lines.extend(["## Post-Recovery Commands", ""])
    lines.extend(f"- `{command}`" for command in recovery["post_recovery_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in recovery["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for P0 host evidence recovery exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_p0_host_evidence_recovery_markdown(build_p0_host_evidence_recovery())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _host_recovery_lane(details: dict[str, Any]) -> dict[str, Any]:
    gates = details["gates"]
    return {
        "host": details["host"],
        "status": details["status"],
        "blocker": details["blocker"],
        "gates": [gate["gate"] for gate in gates],
        "first_action": details["first_action"],
        "next_doc": details["next_doc"],
        "passed_record_commands": [gate["passed_record_command"] for gate in gates],
        "blocked_record_commands": [gate["blocked_record_command"] for gate in gates],
    }


if __name__ == "__main__":
    main()
