"""Export an RC dry-run packet that rehearses release checks without publishing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_v1_rc_cutover_gate import build_v1_rc_cutover_gate
from scripts.export_distribution_rollout_packet import build_distribution_rollout_packet
from scripts.export_rc_cutover_recovery_plan import build_rc_cutover_recovery_plan
from scripts.export_v1_rc_rehearsal_plan import build_v1_rc_rehearsal_plan
from scripts.export_v1_stabilization_plan import build_v1_stabilization_plan
from scripts.historical_status import add_historical_status_banner


def build_rc_dry_run() -> dict[str, Any]:
    """Build the current RC dry-run packet without opening publish commands."""
    gate = build_v1_rc_cutover_gate()
    rehearsal = build_v1_rc_rehearsal_plan()
    recovery = build_rc_cutover_recovery_plan()
    rollout = build_distribution_rollout_packet()
    stabilization = build_v1_stabilization_plan()
    cutover_allowed = gate["cutover_allowed"]
    return {
        "package": gate["package"],
        "package_version": gate["package_version"],
        "release_tag": gate["release_tag"],
        "dry_run_status": "ready_for_publish_rehearsal" if cutover_allowed else "preflight_only_blocked_publish",
        "gate_status": gate["gate_status"],
        "blocked_reason": gate["blocked_reason"],
        "dry_run_allowed": rehearsal["dry_run_allowed"],
        "publish_allowed": False,
        "rc_cutover_allowed": cutover_allowed,
        "distribution_status": rollout["distribution_status"],
        "stabilization_status": stabilization["stabilization_status"],
        "p0_summary": gate["p0_summary"],
        "operator_policy": (
            "Run safe checks and local builds only. Do not create tags, GitHub Releases, public announcements, "
            "or PyPI uploads from this dry run."
        ),
        "safe_dry_run_commands": [
            *rehearsal["dry_run_commands"],
            "uv run python scripts/check_v1_rc_cutover_gate.py --format json",
            "uv run python scripts/export_rc_dry_run.py --output docs/RC_DRY_RUN.md",
        ],
        "blocked_publish_commands": recovery["blocked_publish_commands"],
        "blocked_distribution_actions": rollout["next_actions"],
        "success_criteria": [
            "Every safe dry-run command exits 0.",
            "uv build creates local artifacts only; no upload is attempted.",
            "The hard RC cutover gate remains blocked unless every P0 host gate is passed.",
            "Regenerated RC docs match committed generated-doc checks.",
        ],
        "reopen_criteria": recovery["reopen_criteria"],
        "source_docs": [
            "docs/V1_RC_REHEARSAL_PLAN.md",
            "docs/RC_CUTOVER_RECOVERY_PLAN.md",
            "docs/DISTRIBUTION_ROLLOUT_PACKET.md",
            "docs/V1_STABILIZATION_PLAN.md",
            "docs/V1_RC_CUTOVER_GATE.md",
        ],
    }


def render_rc_dry_run_markdown(dry_run: dict[str, Any]) -> str:
    """Render the RC dry-run packet as Markdown."""
    lines = [
        "# RC Dry Run",
        "",
        f"Package: `{dry_run['package']}=={dry_run['package_version']}`",
        f"Release tag: `{dry_run['release_tag']}`",
        f"Dry-run status: `{dry_run['dry_run_status']}`",
        f"Gate status: `{dry_run['gate_status']}`",
        f"Blocked reason: `{dry_run['blocked_reason']}`",
        f"Dry run allowed: `{str(dry_run['dry_run_allowed']).lower()}`",
        f"Publish allowed: `{str(dry_run['publish_allowed']).lower()}`",
        f"RC cutover allowed: `{str(dry_run['rc_cutover_allowed']).lower()}`",
        f"Distribution status: `{dry_run['distribution_status']}`",
        f"Stabilization status: `{dry_run['stabilization_status']}`",
        "",
        "## Operator Policy",
        "",
        dry_run["operator_policy"],
        "",
        "## P0 Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in dry_run["p0_summary"].items())
    lines.extend(["", "## Safe Dry-Run Commands", ""])
    lines.extend(f"- `{command}`" for command in dry_run["safe_dry_run_commands"])
    lines.extend(["", "## Blocked Publish Commands", ""])
    if dry_run["blocked_publish_commands"]:
        lines.extend(f"- `{command}`" for command in dry_run["blocked_publish_commands"])
    else:
        lines.append("- none")
    lines.extend(["", "## Blocked Distribution Actions", ""])
    lines.extend(f"- {action}" for action in dry_run["blocked_distribution_actions"])
    lines.extend(["", "## Success Criteria", ""])
    lines.extend(f"- {criterion}" for criterion in dry_run["success_criteria"])
    lines.extend(["", "## Reopen Criteria", ""])
    lines.extend(f"- {criterion}" for criterion in dry_run["reopen_criteria"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in dry_run["source_docs"])
    return add_historical_status_banner("\n".join(lines) + "\n")


def main() -> None:
    """CLI entrypoint for RC dry-run exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_rc_dry_run_markdown(build_rc_dry_run())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
