"""Export v1 RC and growth cutover status."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_campaign_pack import build_beta_campaign_pack
from scripts.export_network_growth_tracker import build_network_growth_tracker
from scripts.export_v1_evidence_operator_packet import build_v1_evidence_operator_packet
from scripts.export_v1_rc_automation_pack import build_v1_rc_automation_pack


def build_v1_growth_cutover_report() -> dict[str, Any]:
    """Build a deterministic v1 cutover report without bypassing evidence gates."""
    evidence_packet = build_v1_evidence_operator_packet()
    automation_pack = build_v1_rc_automation_pack()
    beta_campaign = build_beta_campaign_pack()
    growth_tracker = build_network_growth_tracker()
    blocking_gates = _blocking_gates(automation_pack)
    return {
        "cutover_status": "ready_for_rc" if not blocking_gates else "blocked_by_p0_evidence",
        "rc_publish_allowed": automation_pack["release_candidate_allowed"],
        "automation_status": automation_pack["automation_status"],
        "evidence_status": evidence_packet["packet_status"],
        "beta_campaign_status": beta_campaign["campaign_status"],
        "growth_status": _growth_status(growth_tracker),
        "blocking_gates": blocking_gates,
        "growth_channels": growth_tracker["channels"],
        "preflight_commands": automation_pack["preflight_commands"],
        "publish_commands": automation_pack["publish_commands"],
        "next_cutover_actions": _next_cutover_actions(blocking_gates),
        "source_docs": [
            "docs/V1_EVIDENCE_OPERATOR_PACKET.md",
            "docs/V1_RC_AUTOMATION_PACK.md",
            "docs/BETA_CAMPAIGN_PACK.md",
            "docs/NETWORK_GROWTH_TRACKER.md",
        ],
    }


def render_v1_growth_cutover_report_markdown(report: dict[str, Any]) -> str:
    """Render the v1 growth cutover report as Markdown."""
    lines = [
        "# V1 Growth Cutover Report",
        "",
        f"Cutover status: `{report['cutover_status']}`",
        f"RC publish allowed: `{str(report['rc_publish_allowed']).lower()}`",
        f"Automation status: `{report['automation_status']}`",
        f"Evidence status: `{report['evidence_status']}`",
        f"Beta campaign status: `{report['beta_campaign_status']}`",
        f"Growth status: `{report['growth_status']}`",
        "",
        "## Blocking Gates",
        "",
    ]
    if report["blocking_gates"]:
        lines.extend(f"- `{gate}`" for gate in report["blocking_gates"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Growth Channels",
            "",
            "| Channel | Status | URL | Next Action |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| {channel['name']} | `{channel['status']}` | {channel['url']} | {channel['next_action']} |"
        for channel in report["growth_channels"]
    )
    lines.extend(["", "## Preflight Commands", ""])
    lines.extend(f"- `{command}`" for command in report["preflight_commands"])
    lines.extend(["", "## Publish Commands", ""])
    lines.extend(f"- `{command}`" for command in report["publish_commands"])
    lines.extend(["", "## Next Cutover Actions", ""])
    lines.extend(f"- {action}" for action in report["next_cutover_actions"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in report["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for v1 growth cutover report exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_v1_growth_cutover_report_markdown(build_v1_growth_cutover_report())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _blocking_gates(automation_pack: dict[str, Any]) -> list[str]:
    if automation_pack["release_candidate_allowed"]:
        return []
    return ["p0_host_evidence"]


def _growth_status(growth_tracker: dict[str, Any]) -> str:
    blocked_statuses = {"blocked", "missing", "unknown"}
    return (
        "blocked" if any(channel["status"] in blocked_statuses for channel in growth_tracker["channels"]) else "ready"
    )


def _next_cutover_actions(blocking_gates: list[str]) -> list[str]:
    if "p0_host_evidence" in blocking_gates:
        return [
            "Record real Codex and Claude Code P0 host evidence.",
            "Regenerate evidence, RC automation, and cutover reports.",
            "Run release readiness before creating an RC tag.",
            "Invite beta users with docs/BETA_CAMPAIGN_PACK.md while RC remains blocked.",
        ]
    return [
        "Run preflight commands from a clean worktree.",
        "Create the RC tag and GitHub release through the gated release workflow.",
        "Verify PyPI, MCP Registry, and directory visibility after publication.",
        "Continue beta campaign triage with privacy-safe records.",
    ]


if __name__ == "__main__":
    main()
