"""Export a focused pack for unblocking P0 real-host evidence."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_p0_blocker_triage import build_p0_blocker_triage

_P0_HOSTS = frozenset({"Codex", "Claude Code"})
_FAILURE_BY_HOST = {
    "Codex": "codex_tool_call_cancelled",
    "Claude Code": "claude_cli_missing",
}
_DIAGNOSTIC_BY_FAILURE = {
    "codex_tool_call_cancelled": [
        "Confirm the host can list AlbumentationsX MCP tools and read albumentationsx://examples/client-smoke.",
        "Repeat run_host_smoke_check from an interactive Codex session where MCP tool approval is visible.",
        "If the tool is cancelled again, capture the host approval state and record a blocked note, not a pass.",
    ],
    "claude_cli_missing": [
        "Install or expose the Claude Code CLI before running the MCP host proof.",
        "Run `claude --version` in the same shell/session that starts the host proof.",
        "Only replay the First 10 Minutes workflow after Claude Code can start the configured MCP server.",
    ],
}


def build_p0_host_unblock_pack() -> dict[str, Any]:
    """Build P0 host unblock lanes from the committed blocker triage state."""
    triage = build_p0_blocker_triage()
    lanes = [
        _recovery_lane(item)
        for item in triage["triage_matrix"]
        if item["host"] in _P0_HOSTS and item["evidence_status"] != "recorded"
    ]
    return {
        "pack_status": "blocked_evidence_triage_required" if lanes else "ready_for_rc_recheck",
        "rc_reopen_allowed": not lanes,
        "summary": {
            "lane_count": len(lanes),
            "blocked_lane_count": sum(lane["evidence_status"] == "blocked" for lane in lanes),
            "missing_lane_count": sum(lane["evidence_status"] == "missing" for lane in lanes),
        },
        "recovery_policy": (
            "Do not mark any P0 gate as passed until a real host run completes the gate and leaves a dated, "
            "reviewer-observed artifact or evidence note."
        ),
        "recovery_lanes": lanes,
        "post_recovery_commands": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_p0_host_unblock_pack.py --output docs/P0_HOST_UNBLOCK_PACK.md",
            "uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md",
            "uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json",
        ],
        "source_docs": [
            "docs/P0_BLOCKER_TRIAGE.md",
            "docs/HOST_FAILURE_COOKBOOK.md",
            "docs/HOST_MANUAL_RUNS.json",
        ],
    }


def render_p0_host_unblock_pack_markdown(pack: dict[str, Any]) -> str:
    """Render P0 host unblock lanes as Markdown."""
    lines = [
        "# P0 Host Evidence Unblock Pack",
        "",
        f"Pack status: `{pack['pack_status']}`",
        f"RC reopen allowed: `{str(pack['rc_reopen_allowed']).lower()}`",
        "",
        "## Recovery Policy",
        "",
        pack["recovery_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in pack["summary"].items())
    lines.extend(
        [
            "",
            "## Recovery Lanes",
            "",
            "| Host | Gate | Failure Class | First Diagnostic | Record Command |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if pack["recovery_lanes"]:
        lines.extend(
            "| "
            f"{lane['host']} | "
            f"`{lane['gate']}` | "
            f"`{lane['failure_class']}` | "
            f"{lane['diagnostic_steps'][0]} | "
            f"`{lane['record_command']}` |"
            for lane in pack["recovery_lanes"]
        )
    else:
        lines.append("| none | `none` | `none` | No P0 blockers remain. | `none` |")
    lines.extend(["", "## Lane Details", ""])
    for lane in pack["recovery_lanes"]:
        lines.extend(
            [
                f"### {lane['host']} / {lane['gate']}",
                "",
                f"- Evidence status: `{lane['evidence_status']}`",
                f"- Failure class: `{lane['failure_class']}`",
                f"- Acceptance criterion: {lane['acceptance_criterion']}",
                "- Diagnostics:",
            ]
        )
        lines.extend(f"  - {step}" for step in lane["diagnostic_steps"])
        lines.extend(["", f"- Record command: `{lane['record_command']}`", ""])
    lines.extend(["## Post-Recovery Commands", ""])
    lines.extend(f"- `{command}`" for command in pack["post_recovery_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in pack["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for the P0 host evidence unblock pack."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_p0_host_unblock_pack_markdown(build_p0_host_unblock_pack())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _recovery_lane(item: dict[str, Any]) -> dict[str, Any]:
    failure_class = _FAILURE_BY_HOST[item["host"]]
    return {
        "host": item["host"],
        "gate": item["gate"],
        "evidence_status": item["evidence_status"],
        "failure_class": failure_class,
        "diagnostic_steps": _DIAGNOSTIC_BY_FAILURE[failure_class],
        "acceptance_criterion": (
            f"Replace this blocked record with a dated passed record only after the real host completes {item['gate']}."
        ),
        "record_command": _record_command(host=item["host"], gate=item["gate"]),
    }


def _record_command(*, host: str, gate: str) -> str:
    args = [
        "uv",
        "run",
        "python",
        "scripts/record_host_manual_run.py",
    ]
    if gate == "first_10_minutes_replay":
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
            f"{host} completed {gate} in a real MCP host UI.",
        ]
    )
    if gate == "first_10_minutes_replay":
        args.extend(["--artifact", "docs/assets/demo/demo_report.md"])
    return " ".join(shlex.quote(arg) for arg in args)


if __name__ == "__main__":
    main()
