"""Export the evidence-driven flow for reopening the RC gate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_v1_rc_cutover_gate import build_v1_rc_cutover_gate
from scripts.export_beta_validation_status import build_beta_validation_status
from scripts.export_rc_gate_reopen_packet import build_rc_gate_reopen_packet
from scripts.historical_status import add_historical_status_banner


def build_rc_evidence_reopen_flow() -> dict[str, Any]:
    """Build an RC reopen flow that refuses publish while evidence is incomplete."""
    gate = build_v1_rc_cutover_gate()
    beta = build_beta_validation_status()
    reopen = build_rc_gate_reopen_packet()
    p0_status = "passed" if not gate["failed_gates"] else "blocked"
    beta_status = "ready" if beta["validation_status"] == "ready_for_depth_triage" else "missing"
    hard_gate_status = "open" if gate["cutover_allowed"] else "blocked"
    return {
        "flow_status": reopen["reopen_status"],
        "decision": gate["rc_decision"],
        "cutover_allowed": gate["cutover_allowed"],
        "publish_allowed": bool(gate["publish_commands"]),
        "hard_gate_command": "uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json",
        "operator_policy": (
            "No tag, release, upload, or public announcement is allowed while any evidence gate is blocked."
        ),
        "gates": [
            {"name": "p0_host_evidence", "status": p0_status, "required_before": "rc_tag"},
            {"name": "beta_validation", "status": beta_status, "required_before": "rc_tag"},
            {"name": "release_readiness", "status": "ready", "required_before": "rc_tag"},
            {"name": "hard_rc_gate", "status": hard_gate_status, "required_before": "publish"},
        ],
        "safe_commands": [
            "uv run python scripts/check_host_setup_probe.py --live --format json",
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/validate_beta_validation_records.py",
            "uv run python scripts/check_release_readiness.py",
            "uv run python scripts/check_v1_rc_cutover_gate.py --format json",
        ],
        "blocked_publish_commands": gate["blocked_publish_commands"],
        "source_docs": [
            "docs/RC_GATE_REOPEN_PACKET.md",
            "docs/V1_RC_CUTOVER_GATE.md",
            "docs/P0_HOST_EVIDENCE_RECOVERY.md",
            "docs/BETA_VALIDATION_STATUS.md",
        ],
    }


def render_rc_evidence_reopen_flow_markdown(flow: dict[str, Any]) -> str:
    """Render the RC evidence reopen flow as Markdown."""
    lines = [
        "# RC Evidence Reopen Flow",
        "",
        f"Flow status: `{flow['flow_status']}`",
        f"Decision: `{flow['decision']}`",
        f"Cutover allowed: `{str(flow['cutover_allowed']).lower()}`",
        f"Publish allowed: `{str(flow['publish_allowed']).lower()}`",
        f"Hard gate command: `{flow['hard_gate_command']}`",
        "",
        "## Operator Policy",
        "",
        flow["operator_policy"],
        "",
        "## Gates",
        "",
        "| Gate | Status | Required Before |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| `{gate['name']}` | `{gate['status']}` | `{gate['required_before']}` |" for gate in flow["gates"])
    lines.extend(["", "## Safe Commands", ""])
    lines.extend(f"- `{command}`" for command in flow["safe_commands"])
    lines.extend(["", "## Blocked Publish Commands", ""])
    if flow["blocked_publish_commands"]:
        lines.extend(f"- `{command}`" for command in flow["blocked_publish_commands"])
    else:
        lines.append("- none")
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in flow["source_docs"])
    return add_historical_status_banner("\n".join(lines) + "\n")


def main() -> None:
    """CLI entrypoint for RC evidence reopen flow exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_rc_evidence_reopen_flow_markdown(build_rc_evidence_reopen_flow())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
