"""Export the gated plan for an interactive augmentation-policy assistant."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_v1_rc_cutover_gate import build_v1_rc_cutover_gate
from scripts.export_beta_validation_status import build_beta_validation_status


def build_policy_assistant_plan() -> dict[str, Any]:
    """Build the next product-depth plan without bypassing evidence gates."""
    gate = build_v1_rc_cutover_gate()
    beta = build_beta_validation_status()
    blocked_reasons = _blocked_reasons(gate=gate, beta=beta)
    return {
        "plan_status": "ready_for_implementation" if not blocked_reasons else "blocked_until_rc_and_beta_signal",
        "implementation_allowed": not blocked_reasons,
        "product_thesis": "Turn AlbumentationsX MCP into an interactive augmentation-policy assistant.",
        "first_slice": "feedback_aware_policy_recommendation",
        "blocked_reasons": blocked_reasons,
        "components": [
            {
                "name": "dataset_signal_reader",
                "responsibility": "Summarize dataset task, sample count, annotations, and preview constraints.",
                "depends_on": "existing dataset onboarding and quality inspection reports",
            },
            {
                "name": "policy_candidate_generator",
                "responsibility": "Propose bounded AlbumentationsX policy candidates with explicit risk notes.",
                "depends_on": "recipe catalog, transform schemas, and beta validation findings",
            },
            {
                "name": "preview_feedback_loop",
                "responsibility": "Map user feedback like too noisy or object lost into safer next candidates.",
                "depends_on": "preview comparison, feedback interpretation, and tuning decision records",
            },
            {
                "name": "exportable_policy_contract",
                "responsibility": "Export accepted policy as reproducible Python/YAML plus a short review report.",
                "depends_on": "existing export pipeline and output contract snapshots",
            },
        ],
        "acceptance_gates": [
            "P0 real-host evidence passed for Codex and Claude Code.",
            "Every beta validation workflow has a privacy-safe real attempt.",
            "First slice has failing tests before runtime behavior changes.",
            "Output contracts are regenerated only after reviewed behavior changes.",
        ],
        "next_actions": _next_actions(blocked_reasons=blocked_reasons),
        "source_docs": [
            "docs/PRODUCT_DEPTH_SELECTION.md",
            "docs/BETA_TO_BACKLOG_TRIAGE.md",
            "docs/BETA_VALIDATION_LOOP.md",
            "docs/V1_RC_CUTOVER_GATE.md",
        ],
    }


def render_policy_assistant_plan_markdown(plan: dict[str, Any]) -> str:
    """Render the policy assistant plan as Markdown."""
    lines = [
        "# Policy Assistant Plan",
        "",
        f"Plan status: `{plan['plan_status']}`",
        f"Implementation allowed: `{str(plan['implementation_allowed']).lower()}`",
        f"First slice: `{plan['first_slice']}`",
        "",
        "## Product Thesis",
        "",
        plan["product_thesis"],
        "",
        "## Blocked Reasons",
        "",
    ]
    if plan["blocked_reasons"]:
        lines.extend(f"- `{reason}`" for reason in plan["blocked_reasons"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Components",
            "",
            "| Component | Responsibility | Depends On |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"`{component['name']}` | "
        f"{component['responsibility']} | "
        f"{component['depends_on']} |"
        for component in plan["components"]
    )
    lines.extend(["", "## Acceptance Gates", ""])
    lines.extend(f"- {gate}" for gate in plan["acceptance_gates"])
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in plan["next_actions"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in plan["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for policy assistant plan exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_policy_assistant_plan_markdown(build_policy_assistant_plan())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _blocked_reasons(*, gate: dict[str, Any], beta: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not gate["cutover_allowed"]:
        reasons.append(gate["blocked_reason"])
    if beta["validation_status"] != "ready_for_depth_triage":
        reasons.append("beta_validation_records_missing")
    return reasons


def _next_actions(*, blocked_reasons: list[str]) -> list[str]:
    if blocked_reasons:
        return [
            "Do not start runtime implementation until RC and beta gates open.",
            "Use this plan to prepare tests and API boundaries only.",
            "Rebuild the plan after real host and beta evidence changes.",
        ]
    return [
        "Write a focused implementation plan for the first slice.",
        "Add failing tests for policy recommendation behavior.",
        "Ship one policy assistant capability before expanding scope.",
    ]


if __name__ == "__main__":
    main()
