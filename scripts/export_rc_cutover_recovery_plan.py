"""Export the blocked-to-open recovery path for the RC cutover gate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_v1_rc_cutover_gate import build_v1_rc_cutover_gate
from scripts.export_distribution_rollout_packet import build_distribution_rollout_packet
from scripts.export_v1_rc_rehearsal_plan import build_v1_rc_rehearsal_plan
from scripts.historical_status import add_historical_status_banner


def build_rc_cutover_recovery_plan() -> dict[str, Any]:
    """Build an RC recovery plan without opening blocked release commands."""
    gate = build_v1_rc_cutover_gate()
    rehearsal = build_v1_rc_rehearsal_plan()
    rollout = build_distribution_rollout_packet()
    cutover_allowed = gate["cutover_allowed"]
    return {
        "package": gate["package"],
        "package_version": gate["package_version"],
        "release_tag": gate["release_tag"],
        "recovery_status": "ready_for_rc_publish" if cutover_allowed else "blocked_by_p0_evidence",
        "rc_cutover_allowed": cutover_allowed,
        "publish_allowed": cutover_allowed,
        "safe_preflight_allowed": rehearsal["dry_run_allowed"],
        "distribution_status": rollout["distribution_status"],
        "p0_summary": gate["p0_summary"],
        "failed_gates": gate["failed_gates"],
        "operator_policy": (
            "Do not tag, create a GitHub Release, or publish to PyPI while recovery_status is blocked."
        ),
        "recovery_steps": _recovery_steps(cutover_allowed=cutover_allowed),
        "preflight_commands": gate["preflight_commands"],
        "publish_commands": gate["publish_commands"],
        "blocked_publish_commands": gate["blocked_publish_commands"],
        "reopen_criteria": [
            "Every P0 host gate has record_status `passed`.",
            "`uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json` exits 0.",
            "Distribution rollout remains unpublished until the RC tag and package are visible.",
        ],
        "source_docs": [
            "docs/V1_RC_CUTOVER_GATE.md",
            "docs/V1_RC_REHEARSAL_PLAN.md",
            "docs/DISTRIBUTION_ROLLOUT_PACKET.md",
            "docs/P0_HOST_UNBLOCK_PACK.md",
        ],
    }


def render_rc_cutover_recovery_plan_markdown(plan: dict[str, Any]) -> str:
    """Render the RC cutover recovery plan as Markdown."""
    lines = [
        "# RC Cutover Recovery Plan",
        "",
        f"Package: `{plan['package']}=={plan['package_version']}`",
        f"Release tag: `{plan['release_tag']}`",
        f"Recovery status: `{plan['recovery_status']}`",
        f"RC cutover allowed: `{str(plan['rc_cutover_allowed']).lower()}`",
        f"Publish allowed: `{str(plan['publish_allowed']).lower()}`",
        f"Safe preflight allowed: `{str(plan['safe_preflight_allowed']).lower()}`",
        f"Distribution status: `{plan['distribution_status']}`",
        "",
        "## Operator Policy",
        "",
        plan["operator_policy"],
        "",
        "## P0 Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in plan["p0_summary"].items())
    lines.extend(["", "## Recovery Steps", ""])
    lines.extend(f"- {step}" for step in plan["recovery_steps"])
    lines.extend(["", "## Failed Gates", ""])
    if plan["failed_gates"]:
        lines.extend(
            f"- {item['host']} / `{item['gate']}`: `{item['record_status']}` on `{item['date']}`"
            for item in plan["failed_gates"]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Safe Preflight Commands", ""])
    lines.extend(f"- `{command}`" for command in plan["preflight_commands"])
    lines.extend(["", "## Publish Commands", ""])
    if plan["publish_commands"]:
        lines.extend(f"- `{command}`" for command in plan["publish_commands"])
    else:
        lines.append("- none")
    lines.extend(["", "## Blocked Publish Commands", ""])
    if plan["blocked_publish_commands"]:
        lines.extend(f"- `{command}`" for command in plan["blocked_publish_commands"])
    else:
        lines.append("- none")
    lines.extend(["", "## Reopen Criteria", ""])
    lines.extend(f"- {criterion}" for criterion in plan["reopen_criteria"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in plan["source_docs"])
    return add_historical_status_banner("\n".join(lines) + "\n")


def main() -> None:
    """CLI entrypoint for RC cutover recovery plan exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_rc_cutover_recovery_plan_markdown(build_rc_cutover_recovery_plan())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _recovery_steps(*, cutover_allowed: bool) -> list[str]:
    if cutover_allowed:
        return [
            "Run every preflight command from a clean worktree.",
            "Create the RC tag and GitHub Release.",
            "Run post-RC distribution checks before public rollout.",
        ]
    return [
        "Run the safe preflight commands to confirm the codebase is still releasable.",
        "Resolve every P0 lane in docs/P0_HOST_UNBLOCK_PACK.md with real host evidence.",
        "Regenerate P0, RC, and distribution reports after evidence changes.",
        "Rerun the hard RC cutover gate with --require-open before any tag or publish command.",
    ]


if __name__ == "__main__":
    main()
