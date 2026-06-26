"""Export a reviewer-facing execution pack for real MCP host evidence runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_host_evidence_sprint_board import build_host_evidence_sprint_board
from scripts.export_v1_decision_report import build_v1_decision_report

_REQUIRED_OBSERVATIONS = [
    "Host shows AlbumentationsX MCP tools and resources.",
    "Host completes run_host_smoke_check.",
    "Host validates the preview request before rendering.",
    "Host renders baseline and candidate previews under artifact root.",
    "Host compares preview runs and exports a pipeline or report.",
]


def build_real_host_evidence_execution_pack() -> dict[str, Any]:
    """Build a deterministic execution pack without claiming manual evidence."""
    board = build_host_evidence_sprint_board()
    decision = build_v1_decision_report()
    return {
        "package": board["package"],
        "version": board["version"],
        "decision": decision["decision"],
        "ready_for_v1": decision["ready_for_v1"],
        "non_fabrication_policy": "Record passed only after a real MCP host UI completes the flow.",
        "run_queue": [_run_queue_item(item) for item in board["run_queue"]],
        "after_run_commands": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md",
            "uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md",
            "uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md",
            "uv run python scripts/export_host_evidence_sprint_board.py --output docs/HOST_EVIDENCE_SPRINT_BOARD.md",
            "uv run python scripts/check_release_readiness.py",
        ],
    }


def render_real_host_evidence_execution_pack_markdown(pack: dict[str, Any]) -> str:
    """Render the real host evidence execution pack as Markdown."""
    lines = [
        "# Real Host Evidence Execution Pack",
        "",
        f"Package: `{pack['package']}=={pack['version']}`",
        f"Decision: `{pack['decision']}`",
        f"Ready for v1: `{str(pack['ready_for_v1']).lower()}`",
        "",
        "## Non-Fabrication Policy",
        "",
        pack["non_fabrication_policy"],
        "Keep hosts pending or blocked until the reviewer has a dated real UI observation.",
        "",
        "## Execution Queue",
        "",
        "| Order | Host | Priority | Next Action | Packet |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        "| "
        f"{item['run_order']} | "
        f"{item['host']} | "
        f"`{item['priority']}` | "
        f"`{item['next_action']}` | "
        f"`{item['packet_command']}` |"
        for item in pack["run_queue"]
    )
    lines.extend(["", "## Reviewer Worksheet", ""])
    for item in pack["run_queue"]:
        lines.extend(
            [
                f"### {item['host']}",
                "",
                f"- Packet: `{item['packet_command']}`",
                f"- Next action: `{item['next_action']}`",
                "- Required observations:",
            ]
        )
        lines.extend(f"  - {observation}" for observation in item["worksheet"]["required_observations"])
        lines.extend(
            [
                "- Status decision: `passed`, `blocked`, or `pending`.",
                "- Evidence note: one redacted sentence naming completed gates and the first blocker if any.",
                "",
            ]
        )
    lines.extend(["## After Each Host Run", ""])
    lines.extend(f"- `{command}`" for command in pack["after_run_commands"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for real host evidence execution pack exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_real_host_evidence_execution_pack_markdown(build_real_host_evidence_execution_pack())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _run_queue_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_order": item["run_order"],
        "host": item["host"],
        "priority": item["priority"],
        "next_action": item["next_action"],
        "packet_command": item["packet_command"],
        "worksheet": {"required_observations": list(_REQUIRED_OBSERVATIONS)},
    }


if __name__ == "__main__":
    main()
