"""Export the next product-depth selection without bypassing gates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_product_depth_gate import build_product_depth_gate


def build_product_depth_selection() -> dict[str, Any]:
    """Build the recommended first product-depth item from the gated backlog."""
    gate = build_product_depth_gate()
    candidate = _recommended_candidate(gate["candidate_items"])
    return {
        "selection_status": "ready_for_implementation"
        if gate["product_depth_allowed"]
        else "blocked_until_depth_gate_opens",
        "implementation_allowed": gate["product_depth_allowed"],
        "blocked_reasons": gate["blocked_reasons"],
        "decision_policy": "Select one P1 depth item only after RC and beta validation gates open.",
        "recommended_candidate": candidate,
        "selection_rationale": [
            "Start with the first P1 candidate because host setup failure blocks every beta workflow.",
            "Keep review-agent and dataset-depth changes behind real beta validation signal.",
            "Do not start parallel product-depth work until the selected item has tests and docs.",
        ],
        "next_actions": _next_actions(implementation_allowed=gate["product_depth_allowed"]),
        "source_docs": [
            "docs/PRODUCT_DEPTH_GATE.md",
            "docs/PRODUCT_DEPTH_BACKLOG.md",
            "docs/BETA_VALIDATION_STATUS.md",
            "docs/V1_RC_CUTOVER_GATE.md",
        ],
    }


def render_product_depth_selection_markdown(selection: dict[str, Any]) -> str:
    """Render the product-depth selection as Markdown."""
    candidate = selection["recommended_candidate"]
    lines = [
        "# Product Depth Selection",
        "",
        f"Selection status: `{selection['selection_status']}`",
        f"Implementation allowed: `{str(selection['implementation_allowed']).lower()}`",
        "",
        "## Decision Policy",
        "",
        selection["decision_policy"],
        "",
        "## Blocked Reasons",
        "",
    ]
    if selection["blocked_reasons"]:
        lines.extend(f"- `{reason}`" for reason in selection["blocked_reasons"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Recommended Candidate",
            "",
            f"- Product area: `{candidate['product_area']}`",
            f"- Triage bucket: `{candidate['triage_bucket']}`",
            f"- Priority: `{candidate['priority']}`",
            f"- Candidate: {candidate['candidate']}",
            f"- Success signal: {candidate['success_signal']}",
            "",
            "## Selection Rationale",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in selection["selection_rationale"])
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in selection["next_actions"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in selection["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for product-depth selection exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_product_depth_selection_markdown(build_product_depth_selection())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _recommended_candidate(items: list[dict[str, str]]) -> dict[str, str]:
    for item in items:
        if item["priority"] == "p1_after_p0":
            return item
    return items[0]


def _next_actions(*, implementation_allowed: bool) -> list[str]:
    if implementation_allowed:
        return [
            "Write a focused implementation plan for the recommended candidate.",
            "Add failing tests before changing runtime behavior.",
            "Ship one product-depth item before selecting another.",
        ]
    return [
        "Complete P0 real-host evidence and beta validation before implementation.",
        "Keep this selection as a planning artifact, not an implementation approval.",
        "Rebuild this document after evidence and beta records change.",
    ]


if __name__ == "__main__":
    main()
