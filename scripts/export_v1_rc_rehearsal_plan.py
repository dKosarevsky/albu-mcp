"""Export a safe v1 RC rehearsal plan without publishing artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_v1_rc_cutover_gate import build_v1_rc_cutover_gate
from scripts.export_v1_rc_automation_pack import build_v1_rc_automation_pack
from scripts.historical_status import add_historical_status_banner


def build_v1_rc_rehearsal_plan() -> dict[str, Any]:
    """Build a preflight-only RC rehearsal plan from the hard cutover gate."""
    gate = build_v1_rc_cutover_gate()
    automation_pack = build_v1_rc_automation_pack()
    return {
        "package": gate["package"],
        "package_version": gate["package_version"],
        "release_tag": gate["release_tag"],
        "rehearsal_status": "ready_to_publish" if gate["cutover_allowed"] else "preflight_only",
        "rc_cutover_allowed": gate["cutover_allowed"],
        "dry_run_allowed": True,
        "publish_allowed": gate["cutover_allowed"],
        "p0_summary": gate["p0_summary"],
        "dry_run_commands": automation_pack["preflight_commands"],
        "publish_commands": gate["publish_commands"],
        "blocked_publish_commands": gate["blocked_publish_commands"],
        "stop_conditions": [
            "Any P0 host evidence gate is missing or blocked.",
            "The worktree is dirty after regenerating release reports.",
            "Any local verification command fails.",
        ],
        "operator_policy": "Do not create tags, GitHub Releases, or PyPI uploads during rehearsal.",
        "source_docs": [
            "docs/V1_RC_CUTOVER_GATE.md",
            "docs/V1_RC_AUTOMATION_PACK.md",
            "docs/DISTRIBUTION_READINESS_PACK.md",
            "docs/P0_EVIDENCE_STATUS.md",
        ],
    }


def render_v1_rc_rehearsal_plan_markdown(plan: dict[str, Any]) -> str:
    """Render the v1 RC rehearsal plan as Markdown."""
    lines = [
        "# V1 RC Rehearsal Plan",
        "",
        f"Package: `{plan['package']}=={plan['package_version']}`",
        f"Release tag: `{plan['release_tag']}`",
        f"Rehearsal status: `{plan['rehearsal_status']}`",
        f"RC cutover allowed: `{str(plan['rc_cutover_allowed']).lower()}`",
        f"Dry run allowed: `{str(plan['dry_run_allowed']).lower()}`",
        f"Publish allowed: `{str(plan['publish_allowed']).lower()}`",
        "",
        "## Operator Policy",
        "",
        plan["operator_policy"],
        "",
        "## P0 Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in plan["p0_summary"].items())
    lines.extend(["", "## Dry-Run Commands", ""])
    lines.extend(f"- `{command}`" for command in plan["dry_run_commands"])
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
    lines.extend(["", "## Stop Conditions", ""])
    lines.extend(f"- {condition}" for condition in plan["stop_conditions"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in plan["source_docs"])
    return add_historical_status_banner("\n".join(lines) + "\n")


def main() -> None:
    """CLI entrypoint for v1 RC rehearsal plan exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_v1_rc_rehearsal_plan_markdown(build_v1_rc_rehearsal_plan())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
