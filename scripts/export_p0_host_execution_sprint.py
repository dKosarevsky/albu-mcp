"""Export an operator-focused P0 real-host evidence sprint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_p0_evidence_status import build_p0_evidence_status
from scripts.export_p0_host_runbook import build_p0_host_runbook


def build_p0_host_execution_sprint() -> dict[str, Any]:
    """Build the P0 host execution sprint without claiming real host evidence."""
    runbook = build_p0_host_runbook()
    status = build_p0_evidence_status()
    packet_by_host = {item["host"]: item["packet_command"] for item in runbook["run_queue"]}
    return {
        "target_hosts": status["target_hosts"],
        "execution_status": "ready_for_rc" if status["rc_ready"] else "manual_evidence_required",
        "non_fabrication_policy": "Never mark a host passed without reviewer-observed real UI evidence.",
        "source_docs": [
            "docs/P0_HOST_RUNBOOK.md",
            "docs/P0_EVIDENCE_RECORDER.md",
            "docs/P0_EVIDENCE_STATUS.md",
            "docs/P0_BLOCKER_TRIAGE.md",
        ],
        "gate_matrix": [
            {
                "host": item["host"],
                "operator_packet": packet_by_host[item["host"]],
                "gates": [
                    {
                        "gate": gate["gate"],
                        "evidence_status": gate["status"],
                        "next_action": gate["next_action"],
                    }
                    for gate in item["gates"]
                ],
            }
            for item in status["host_statuses"]
        ],
        "stop_conditions": [
            "Do not tag v1 RC while any P0 gate is missing or blocked.",
            "Do not convert pending evidence into passed evidence without a real host UI run.",
            "Record blocked evidence at the first failing gate and use docs/P0_BLOCKER_TRIAGE.md.",
        ],
        "after_real_ui_commands": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md",
            "uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md",
            "uv run python scripts/export_v1_rc_release_packet.py --output docs/V1_RC_RELEASE_PACKET.md",
            "uv run python scripts/check_release_readiness.py",
        ],
    }


def render_p0_host_execution_sprint_markdown(sprint: dict[str, Any]) -> str:
    """Render the P0 host execution sprint as Markdown."""
    lines = [
        "# P0 Host Execution Sprint",
        "",
        f"Target hosts: `{', '.join(sprint['target_hosts'])}`",
        f"Execution status: `{sprint['execution_status']}`",
        "",
        "## Non-Fabrication Policy",
        "",
        sprint["non_fabrication_policy"],
        "",
        "## Source Docs",
        "",
    ]
    lines.extend(f"- `{source}`" for source in sprint["source_docs"])
    lines.extend(
        [
            "",
            "## Gate Matrix",
            "",
            "| Host | Gate | Evidence Status | Next Action | Operator Packet |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for host in sprint["gate_matrix"]:
        lines.extend(
            "| "
            f"{host['host']} | "
            f"`{gate['gate']}` | "
            f"`{gate['evidence_status']}` | "
            f"`{gate['next_action']}` | "
            f"`{host['operator_packet']}` |"
            for gate in host["gates"]
        )
    lines.extend(["", "## Stop Conditions", ""])
    lines.extend(f"- {condition}" for condition in sprint["stop_conditions"])
    lines.extend(["", "## After Real UI Runs", ""])
    lines.extend(f"- `{command}`" for command in sprint["after_real_ui_commands"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for P0 host execution sprint exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_p0_host_execution_sprint_markdown(build_p0_host_execution_sprint())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
