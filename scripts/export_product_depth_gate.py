"""Export the gate for post-RC product-depth work."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_v1_rc_cutover_gate import build_v1_rc_cutover_gate
from scripts.export_beta_validation_status import build_beta_validation_status
from scripts.export_product_depth_backlog import build_product_depth_backlog


def build_product_depth_gate() -> dict[str, Any]:
    """Build the product-depth gate from RC, beta, and backlog state."""
    rc_gate = build_v1_rc_cutover_gate()
    beta_status = build_beta_validation_status()
    backlog = build_product_depth_backlog()
    blocked_reasons = _blocked_reasons(rc_gate=rc_gate, beta_status=beta_status)
    return {
        "gate_status": "ready_for_depth_triage" if not blocked_reasons else "blocked_by_rc_and_beta_signal",
        "product_depth_allowed": not blocked_reasons,
        "rc_cutover_allowed": rc_gate["cutover_allowed"],
        "beta_validation_status": beta_status["validation_status"],
        "backlog_status": backlog["backlog_status"],
        "prioritization_rule": backlog["prioritization_rule"],
        "blocked_reasons": blocked_reasons,
        "summary": {
            "backlog_item_count": len(backlog["items"]),
            "beta_record_count": beta_status["summary"]["record_count"],
            "beta_covered_workflow_count": beta_status["summary"]["covered_workflow_count"],
            "required_beta_workflow_count": beta_status["summary"]["workflow_count"],
        },
        "candidate_items": backlog["items"],
        "source_docs": [
            "docs/PRODUCT_DEPTH_BACKLOG.md",
            "docs/BETA_VALIDATION_STATUS.md",
            "docs/V1_RC_CUTOVER_GATE.md",
        ],
        "next_actions": _next_actions(blocked_reasons=blocked_reasons),
    }


def render_product_depth_gate_markdown(gate: dict[str, Any]) -> str:
    """Render the product-depth gate as Markdown."""
    lines = [
        "# Product Depth Gate",
        "",
        f"Gate status: `{gate['gate_status']}`",
        f"Product depth allowed: `{str(gate['product_depth_allowed']).lower()}`",
        f"RC cutover allowed: `{str(gate['rc_cutover_allowed']).lower()}`",
        f"Beta validation status: `{gate['beta_validation_status']}`",
        f"Backlog status: `{gate['backlog_status']}`",
        "",
        "## Prioritization Rule",
        "",
        gate["prioritization_rule"],
        "",
        "## Blocked Reasons",
        "",
    ]
    if gate["blocked_reasons"]:
        lines.extend(f"- `{reason}`" for reason in gate["blocked_reasons"])
    else:
        lines.append("- none")
    lines.extend(["", "## Summary", ""])
    lines.extend(f"- {key}: `{value}`" for key, value in gate["summary"].items())
    lines.extend(
        [
            "",
            "## Candidate Items",
            "",
            "| Product Area | Priority | Candidate | Success Signal |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| `{item['product_area']}` | `{item['priority']}` | {item['candidate']} | {item['success_signal']} |"
        for item in gate["candidate_items"]
    )
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in gate["source_docs"])
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in gate["next_actions"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for product-depth gate exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_product_depth_gate_markdown(build_product_depth_gate())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _blocked_reasons(*, rc_gate: dict[str, Any], beta_status: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not rc_gate["cutover_allowed"]:
        reasons.append("rc_cutover_blocked")
    if beta_status["validation_status"] != "ready_for_depth_triage":
        reasons.append("beta_validation_incomplete")
    return reasons


def _next_actions(*, blocked_reasons: list[str]) -> list[str]:
    actions: list[str] = []
    if "rc_cutover_blocked" in blocked_reasons:
        actions.append("Complete P0 real-host evidence and open the RC cutover gate before product-depth work.")
    if "beta_validation_incomplete" in blocked_reasons:
        actions.append("Record one privacy-safe real beta attempt for each beta workflow.")
    if not blocked_reasons:
        actions.append("Select the highest-signal repeated beta gap and write a focused implementation plan.")
    return actions


if __name__ == "__main__":
    main()
