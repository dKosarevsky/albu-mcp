"""Export the final packet required before reopening the RC cutover gate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_v1_rc_cutover_gate import build_v1_rc_cutover_gate
from scripts.export_beta_to_backlog_triage import build_beta_to_backlog_triage
from scripts.export_beta_validation_recording_pack import build_beta_validation_recording_pack
from scripts.export_p0_host_evidence_recovery import build_p0_host_evidence_recovery
from scripts.export_rc_dry_run import build_rc_dry_run
from scripts.historical_status import add_historical_status_banner


def build_rc_gate_reopen_packet() -> dict[str, Any]:
    """Build the current RC gate reopen packet without mutating release state."""
    gate = build_v1_rc_cutover_gate()
    dry_run = build_rc_dry_run()
    p0_recovery = build_p0_host_evidence_recovery()
    beta_recording = build_beta_validation_recording_pack()
    beta_triage = build_beta_to_backlog_triage()
    reopen_blockers = _reopen_blockers(gate=gate, p0_recovery=p0_recovery, beta_recording=beta_recording)
    return {
        "package": gate["package"],
        "package_version": gate["package_version"],
        "release_tag": gate["release_tag"],
        "reopen_status": "ready_for_rc_cutover" if not reopen_blockers else "blocked_until_p0_and_beta_evidence",
        "cutover_allowed": gate["cutover_allowed"],
        "publish_allowed": bool(gate["publish_commands"]),
        "dry_run_allowed": dry_run["dry_run_allowed"],
        "rc_decision": gate["rc_decision"],
        "summary": {
            "p0_blocked_gate_count": p0_recovery["summary"]["blocked_gate_count"],
            "p0_passed_gate_count": p0_recovery["summary"]["passed_gate_count"],
            "beta_record_count": beta_recording["summary"]["record_count"],
            "beta_missing_workflow_count": beta_recording["summary"]["missing_workflow_count"],
            "promoted_backlog_item_count": beta_triage["summary"]["promoted_backlog_item_count"],
            "blocked_publish_command_count": len(gate["blocked_publish_commands"]),
        },
        "reopen_policy": (
            "Do not create RC tags, GitHub Releases, PyPI uploads, or public rollout announcements until this packet "
            "has reopen_status ready_for_rc_cutover and the hard gate exits 0 with --require-open."
        ),
        "reopen_blockers": reopen_blockers,
        "open_criteria": [
            "Every Codex and Claude Code P0 host evidence gate has record_status `passed`.",
            "Every beta validation workflow has at least one privacy-safe real attempt recorded.",
            "`uv run python scripts/check_release_readiness.py` exits 0 after regenerating reports.",
            "`uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json` exits 0.",
        ],
        "reopen_sequence": [
            "Run docs/P0_HOST_EVIDENCE_RECOVERY.md and replace blocked P0 records only with real host evidence.",
            "Run docs/BETA_VALIDATION_RECORDING_PACK.md and record privacy-safe real beta attempts.",
            "Regenerate P0, beta, RC, and product-depth generated docs.",
            "Run release readiness, full tests, type checks, formatting, and local build.",
            "Run the hard RC cutover gate with --require-open.",
            "Create RC tag and GitHub prerelease only after the hard gate opens.",
        ],
        "safe_commands": dry_run["safe_dry_run_commands"],
        "blocked_publish_commands": gate["blocked_publish_commands"],
        "source_docs": [
            "docs/P0_HOST_EVIDENCE_RECOVERY.md",
            "docs/BETA_VALIDATION_RECORDING_PACK.md",
            "docs/BETA_TO_BACKLOG_TRIAGE.md",
            "docs/RC_DRY_RUN.md",
            "docs/V1_RC_CUTOVER_GATE.md",
        ],
    }


def render_rc_gate_reopen_packet_markdown(packet: dict[str, Any]) -> str:
    """Render the RC gate reopen packet as Markdown."""
    lines = [
        "# RC Gate Reopen Packet",
        "",
        f"Package: `{packet['package']}=={packet['package_version']}`",
        f"Release tag: `{packet['release_tag']}`",
        f"Reopen status: `{packet['reopen_status']}`",
        f"Cutover allowed: `{str(packet['cutover_allowed']).lower()}`",
        f"Publish allowed: `{str(packet['publish_allowed']).lower()}`",
        f"Dry run allowed: `{str(packet['dry_run_allowed']).lower()}`",
        f"RC decision: `{packet['rc_decision']}`",
        "",
        "## Reopen Policy",
        "",
        packet["reopen_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in packet["summary"].items())
    lines.extend(["", "## Reopen Blockers", ""])
    if packet["reopen_blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in packet["reopen_blockers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Open Criteria", ""])
    lines.extend(f"- {criterion}" for criterion in packet["open_criteria"])
    lines.extend(["", "## Reopen Sequence", ""])
    lines.extend(f"{index}. {step}" for index, step in enumerate(packet["reopen_sequence"], start=1))
    lines.extend(["", "## Safe Commands", ""])
    lines.extend(f"- `{command}`" for command in packet["safe_commands"])
    lines.extend(["", "## Blocked Publish Commands", ""])
    if packet["blocked_publish_commands"]:
        lines.extend(f"- `{command}`" for command in packet["blocked_publish_commands"])
    else:
        lines.append("- none")
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in packet["source_docs"])
    return add_historical_status_banner("\n".join(lines) + "\n")


def main() -> None:
    """CLI entrypoint for RC gate reopen packet exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_rc_gate_reopen_packet_markdown(build_rc_gate_reopen_packet())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _reopen_blockers(
    *,
    gate: dict[str, Any],
    p0_recovery: dict[str, Any],
    beta_recording: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if p0_recovery["summary"]["blocked_gate_count"]:
        blockers.append("p0_host_evidence_blocked")
    if beta_recording["summary"]["missing_workflow_count"]:
        blockers.append("beta_validation_records_missing")
    if not gate["cutover_allowed"]:
        blockers.append(gate["blocked_reason"])
    return blockers


if __name__ == "__main__":
    main()
