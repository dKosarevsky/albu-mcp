"""Export an operator kit for capturing real P0 host evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_p0_host_evidence_recovery import build_p0_host_evidence_recovery


def build_host_evidence_capture_kit() -> dict[str, Any]:
    """Build a real-host evidence capture kit without marking evidence passed."""
    recovery = build_p0_host_evidence_recovery()
    lanes = [
        {
            "host": lane["host"],
            "capture_status": "blocked_until_operator_run",
            "blocker": lane["blocker"],
            "gates": lane["gates"],
            "first_action": lane["first_action"],
            "next_doc": lane["next_doc"],
            "passed_record_commands": lane["passed_record_commands"],
            "blocked_record_commands": lane["blocked_record_commands"],
        }
        for lane in recovery["host_recovery_lanes"]
    ]
    return {
        "kit_status": "operator_capture_required"
        if recovery["summary"]["blocked_gate_count"]
        else "ready_for_rc_recheck",
        "non_fabrication_policy": "Record passed only after a reviewer observes the real MCP host UI flow.",
        "target_hosts": [lane["host"] for lane in lanes],
        "summary": {
            "target_host_count": len(lanes),
            "required_gate_count": recovery["summary"]["required_gate_count"],
            "blocked_gate_count": recovery["summary"]["blocked_gate_count"],
            "passed_gate_count": recovery["summary"]["passed_gate_count"],
        },
        "pre_capture_commands": [
            "uv run python scripts/check_host_setup_probe.py --live --format json",
            "uv run python scripts/check_p0_host_run_preflight.py",
            "uv run python scripts/export_manual_host_acceptance_packet.py --host '<host>' "
            "--output /tmp/albu-host-<host>.md",
        ],
        "capture_lanes": lanes,
        "post_capture_commands": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md",
            "uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md",
            "uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json",
        ],
        "acceptance_criteria": [
            "The reviewer sees the MCP host list AlbumentationsX MCP tools/resources.",
            "The reviewer sees run_host_smoke_check complete in the host UI.",
            "The reviewer sees preview_ready true before first-preview work.",
            "The record command includes only redacted evidence and artifact references.",
        ],
        "source_docs": [
            "docs/REAL_HOST_EVIDENCE_COMMAND_CENTER.md",
            "docs/P0_HOST_EVIDENCE_RECOVERY.md",
            "docs/P0_EVIDENCE_RECORDER.md",
            "docs/HOST_MANUAL_RUNS.json",
        ],
    }


def render_host_evidence_capture_kit_markdown(kit: dict[str, Any]) -> str:
    """Render the host evidence capture kit as Markdown."""
    lines = [
        "# Host Evidence Capture Kit",
        "",
        f"Kit status: `{kit['kit_status']}`",
        f"Target hosts: `{', '.join(kit['target_hosts'])}`",
        "",
        "## Non-Fabrication Policy",
        "",
        kit["non_fabrication_policy"],
        "Do not record `passed` from generated smoke output.",
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in kit["summary"].items())
    lines.extend(["", "## Pre-Capture Commands", ""])
    lines.extend(f"- `{command}`" for command in kit["pre_capture_commands"])
    lines.extend(
        [
            "",
            "## Capture Lanes",
            "",
            "| Host | Capture Status | Blocker | Gates | First Action | Next Doc |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"`{lane['host']}` | "
        f"`{lane['capture_status']}` | "
        f"`{lane['blocker']}` | "
        f"{', '.join(f'`{gate}`' for gate in lane['gates'])} | "
        f"{lane['first_action']} | "
        f"`{lane['next_doc']}` |"
        for lane in kit["capture_lanes"]
    )
    lines.extend(["", "## Record Commands", ""])
    lines.append("`scripts/record_host_manual_run.py` is the only P0 evidence writer.")
    for lane in kit["capture_lanes"]:
        lines.extend([f"### {lane['host']}", "", "Passed evidence:"])
        lines.extend(f"- `{command}`" for command in lane["passed_record_commands"])
        lines.extend(["", "Blocked evidence:"])
        lines.extend(f"- `{command}`" for command in lane["blocked_record_commands"])
        lines.append("")
    lines.extend(["## Acceptance Criteria", ""])
    lines.extend(f"- {criterion}" for criterion in kit["acceptance_criteria"])
    lines.extend(["", "## Post-Capture Commands", ""])
    lines.extend(f"- `{command}`" for command in kit["post_capture_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in kit["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for host evidence capture kit exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_host_evidence_capture_kit_markdown(build_host_evidence_capture_kit())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
