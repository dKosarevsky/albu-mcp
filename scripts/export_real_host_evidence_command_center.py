"""Export a command center for the next real-host evidence sprint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_host_setup_probe import build_host_setup_probe
from scripts.export_host_evidence_runner import build_host_evidence_runner
from scripts.export_p0_evidence_recorder import build_p0_evidence_recorder
from scripts.export_p0_host_evidence_recovery import build_p0_host_evidence_recovery


def build_real_host_evidence_command_center() -> dict[str, Any]:
    """Build the current operator command center without fabricating evidence."""
    recovery = build_p0_host_evidence_recovery()
    runner = build_host_evidence_runner()
    probe = build_host_setup_probe()
    recorder = build_p0_evidence_recorder()
    blocked_hosts = [lane["host"] for lane in recovery["host_recovery_lanes"] if lane["status"] != "passed"]
    blocked_gate_count = recovery["summary"]["blocked_gate_count"]
    return {
        "command_center_status": "blocked_until_real_host_runs"
        if blocked_gate_count
        else "ready_for_rc_gate_recheck",
        "non_fabrication_policy": "Only reviewer-observed real MCP host UI runs can satisfy P0 gates.",
        "summary": {
            "target_host_count": recovery["summary"]["target_host_count"],
            "required_gate_count": recovery["summary"]["required_gate_count"],
            "passed_gate_count": recovery["summary"]["passed_gate_count"],
            "blocked_gate_count": blocked_gate_count,
            "setup_probe_check_count": probe["summary"]["check_count"],
            "runner_lane_count": runner["summary"]["runner_lane_count"],
        },
        "blocked_hosts": blocked_hosts,
        "next_operator_action": _next_operator_action(blocked_gate_count=blocked_gate_count),
        "operator_commands": [
            "uv run python scripts/check_host_setup_probe.py --live --format json",
            "uv run python scripts/check_p0_host_run_preflight.py",
            "uv run python scripts/export_manual_host_acceptance_packet.py --host '<host>' "
            "--output /tmp/albu-host-<host>.md",
            "uv run python scripts/record_host_manual_run.py --host '<host>' --status passed "
            "--date YYYY-MM-DD --evidence '<redacted reviewer-observed evidence>'",
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json",
        ],
        "host_lanes": [
            {
                "host": lane["host"],
                "status": lane["status"],
                "blocker": lane["blocker"],
                "gates": lane["gates"],
                "first_action": lane["first_action"],
                "next_doc": lane["next_doc"],
            }
            for lane in recovery["host_recovery_lanes"]
        ],
        "recording_policy": recorder["recording_policy"],
        "source_docs": [
            "docs/HOST_SETUP_PROBE.md",
            "docs/HOST_EVIDENCE_RUNNER.md",
            "docs/P0_EVIDENCE_RECORDER.md",
            "docs/P0_HOST_EVIDENCE_RECOVERY.md",
            "docs/HOST_MANUAL_RUNS.json",
        ],
    }


def render_real_host_evidence_command_center_markdown(center: dict[str, Any]) -> str:
    """Render the real-host evidence command center as Markdown."""
    lines = [
        "# Real Host Evidence Command Center",
        "",
        f"Command center status: `{center['command_center_status']}`",
        f"Next operator action: {center['next_operator_action']}",
        "",
        "## Non-Fabrication Policy",
        "",
        center["non_fabrication_policy"],
        center["recording_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in center["summary"].items())
    lines.extend(["", "## Blocked Hosts", ""])
    if center["blocked_hosts"]:
        lines.extend(f"- `{host}`" for host in center["blocked_hosts"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Host Lanes",
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
        for lane in center["host_lanes"]
    )
    lines.extend(["", "## Operator Commands", ""])
    lines.extend(f"- `{command}`" for command in center["operator_commands"])
    lines.extend(["", "## Recorder", "", "`scripts/record_host_manual_run.py` is the only P0 evidence writer."])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in center["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for real-host evidence command center exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_real_host_evidence_command_center_markdown(build_real_host_evidence_command_center())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _next_operator_action(*, blocked_gate_count: int) -> str:
    if blocked_gate_count:
        return "Run the host setup probe live, then execute the first blocked host lane."
    return "Regenerate P0 docs, then rerun the hard RC cutover gate with --require-open."


if __name__ == "__main__":
    main()
