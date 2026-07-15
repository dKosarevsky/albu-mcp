"""Export the stable-v1 stabilization plan from committed release gates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_product_depth_selection import build_product_depth_selection
from scripts.export_v1_decision_report import build_v1_decision_report
from scripts.export_v1_growth_cutover_report import build_v1_growth_cutover_report
from scripts.export_v1_trust_gates import build_v1_trust_gates
from scripts.historical_status import add_historical_status_banner

_V1_SCOPE = [
    "Stable MCP server packaging and server.json metadata.",
    "Privacy-safe local image and artifact workflows.",
    "Host evidence gates for Codex and Claude Code before RC publication.",
    "Beta workflow intake for robustness variants, noisy preview tuning, and dataset health.",
    "Release and distribution docs that are generated from committed evidence.",
]
_EXIT_CRITERIA = [
    "P0 host evidence is passed for required RC hosts.",
    "RC cutover gate opens with --require-open.",
    "At least one privacy-safe beta validation attempt exists for each beta workflow.",
    "Release readiness, tests, lint, type checks, build, and MCP smoke pass in CI.",
    "PyPI, GitHub Release, MCP Registry, and directory visibility pass after RC publication.",
]


def build_v1_stabilization_plan() -> dict[str, Any]:
    """Build stable-v1 stabilization guidance without bypassing current blockers."""
    decision = build_v1_decision_report()
    trust_gates = build_v1_trust_gates()
    growth = build_v1_growth_cutover_report()
    depth_selection = build_product_depth_selection()
    stable_allowed = decision["ready_for_v1"] and not trust_gates["manual_evidence_required"]
    return {
        "package": decision["package"],
        "package_version": decision["package_version"],
        "stabilization_status": "ready_for_stable_v1" if stable_allowed else "blocked_until_trust_gates_pass",
        "ready_for_v1": decision["ready_for_v1"],
        "stable_v1_allowed": stable_allowed,
        "manual_gate_count": len(trust_gates["manual_gates"]),
        "cutover_status": growth["cutover_status"],
        "selected_depth_item": depth_selection["recommended_candidate"]["product_area"],
        "feature_freeze_policy": (
            "Keep v1 scope frozen to release reliability, host evidence, beta validation, "
            "and documentation corrections."
        ),
        "v1_scope": list(_V1_SCOPE),
        "exit_criteria": list(_EXIT_CRITERIA),
        "non_goals": decision["non_goals"],
        "post_v1_backlog": [
            {
                "item": depth_selection["recommended_candidate"]["product_area"],
                "status": depth_selection["selection_status"],
                "candidate": depth_selection["recommended_candidate"]["candidate"],
            },
            {
                "item": "review_agent_v3",
                "status": "waiting_for_beta_signal",
                "candidate": "Feedback-to-adjustment improvements after repeated noisy-preview beta findings.",
            },
            {
                "item": "dataset_quality_depth",
                "status": "waiting_for_beta_signal",
                "candidate": "Deeper annotation, class-balance, and duplicate checks after beta validation.",
            },
        ],
        "source_docs": [
            "docs/V1_DECISION_REPORT.md",
            "docs/V1_TRUST_GATES.md",
            "docs/V1_GROWTH_CUTOVER_REPORT.md",
            "docs/PRODUCT_DEPTH_SELECTION.md",
        ],
    }


def render_v1_stabilization_plan_markdown(plan: dict[str, Any]) -> str:
    """Render stable-v1 stabilization guidance as Markdown."""
    lines = [
        "# V1 Stabilization Plan",
        "",
        f"Package: `{plan['package']}=={plan['package_version']}`",
        f"Stabilization status: `{plan['stabilization_status']}`",
        f"Ready for v1: `{str(plan['ready_for_v1']).lower()}`",
        f"Stable v1 allowed: `{str(plan['stable_v1_allowed']).lower()}`",
        f"Manual gate count: `{plan['manual_gate_count']}`",
        f"Cutover status: `{plan['cutover_status']}`",
        "",
        "## Feature Freeze Policy",
        "",
        plan["feature_freeze_policy"],
        "",
        "## V1 Scope",
        "",
    ]
    lines.extend(f"- {item}" for item in plan["v1_scope"])
    lines.extend(["", "## Exit Criteria", ""])
    lines.extend(f"- {item}" for item in plan["exit_criteria"])
    lines.extend(["", "## Non-Goals", ""])
    lines.extend(f"- {item}" for item in plan["non_goals"])
    lines.extend(
        [
            "",
            "## Post-V1 Backlog",
            "",
            "| Item | Status | Candidate |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(f"| `{item['item']}` | `{item['status']}` | {item['candidate']} |" for item in plan["post_v1_backlog"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in plan["source_docs"])
    return add_historical_status_banner("\n".join(lines) + "\n")


def main() -> None:
    """CLI entrypoint for the v1 stabilization plan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_v1_stabilization_plan_markdown(build_v1_stabilization_plan())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
