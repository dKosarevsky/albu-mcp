"""Export the current v1 go/no-go decision from committed launch evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_v1_launch_report import build_v1_launch_report


def build_v1_decision_report() -> dict[str, Any]:
    """Build a deterministic v1 decision report from the launch report."""
    launch_report = build_v1_launch_report()
    ready_for_v1 = launch_report["ready_for_v1"]
    host_blocker_count = len(launch_report["host_blockers"])
    decision = "cut_v1_release_candidate" if ready_for_v1 else "hold_v1"
    return {
        "package": launch_report["package"],
        "package_version": launch_report["package_version"],
        "server_version": launch_report["server_version"],
        "ready_for_v1": ready_for_v1,
        "decision": decision,
        "release_candidate_allowed": ready_for_v1,
        "host_blocker_count": host_blocker_count,
        "blocking_codes": [blocker["code"] for blocker in launch_report["blockers"]],
        "decision_policy": "Do not cut v1 from synthetic or generated host evidence.",
        "required_before_v1": _required_before_v1(launch_report),
        "non_goals": [
            "Do not reduce the supported host set only to make the gate pass.",
            "Do not mark generated MCP smoke output as real host UI evidence.",
            "Do not publish a stable v1 while host_blocker_count is greater than zero.",
        ],
        "next_decision_checks": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/check_first_10_minutes_replay.py",
            "uv run python scripts/check_manual_host_acceptance.py",
            "uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md",
            "uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md",
            "uv run python scripts/check_release_readiness.py",
        ],
    }


def render_v1_decision_report_markdown(report: dict[str, Any]) -> str:
    """Render the v1 decision report as Markdown."""
    lines = [
        "# V1 Decision Report",
        "",
        f"Package: `{report['package']}=={report['package_version']}`",
        f"Server version: `{report['server_version']}`",
        f"Ready for v1: `{str(report['ready_for_v1']).lower()}`",
        f"Decision: `{report['decision']}`",
        f"Release candidate allowed: `{str(report['release_candidate_allowed']).lower()}`",
        f"Host blocker count: `{report['host_blocker_count']}`",
        "",
        "## Decision Policy",
        "",
        report["decision_policy"],
        "",
        "## Blocking Codes",
        "",
    ]
    lines.extend(f"- `{code}`" for code in report["blocking_codes"])
    lines.extend(["", "## Required Before V1", ""])
    lines.extend(f"- {item}" for item in report["required_before_v1"])
    lines.extend(["", "## Non-Goals", ""])
    lines.extend(f"- {item}" for item in report["non_goals"])
    lines.extend(["", "## Next Decision Checks", ""])
    lines.extend(f"- `{command}`" for command in report["next_decision_checks"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for v1 decision report exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    report = build_v1_decision_report()
    content = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_v1_decision_report_markdown(report)
    )
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _required_before_v1(launch_report: dict[str, Any]) -> list[str]:
    if launch_report["ready_for_v1"]:
        return ["Run final release readiness checks, tag the release candidate, and watch CI/release workflows."]
    required = ["Run host evidence sprint queue and record real host UI evidence."]
    if any(blocker["code"] == "first_10_minutes_replay_pending" for blocker in launch_report["blockers"]):
        required.append("Record First 10 Minutes replay artifacts for every supported host.")
    if any(blocker["code"] == "manual_host_ui_pending" for blocker in launch_report["blockers"]):
        required.append("Record manual Host UI evidence for every supported host.")
    required.append("Regenerate V1 Launch Report and V1 Decision Report after evidence changes.")
    return required


if __name__ == "__main__":
    main()
