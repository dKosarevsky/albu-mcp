"""Export the gated P1 host-onboarding depth plan."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_host_failure_cookbook import build_host_failure_cookbook
from scripts.export_p0_host_unblock_pack import build_p0_host_unblock_pack
from scripts.export_product_depth_selection import build_product_depth_selection

_IMPLEMENTATION_SLICES = [
    {
        "deliverable": "host_setup_probe",
        "outcome": "Detect missing CLI, stale MCP tool discovery, and invalid roots before the first preview.",
        "test_focus": "Parameterized host setup diagnostics for Codex, Claude Code, Cursor, and Claude Desktop.",
    },
    {
        "deliverable": "approval_troubleshooting",
        "outcome": "Explain host tool-approval cancellation without asking users to inspect private logs.",
        "test_focus": "Blocked Codex tool-call evidence maps to a concrete recovery step.",
    },
    {
        "deliverable": "blocked_evidence_capture",
        "outcome": "Convert repeated setup failures into structured blocked evidence and next actions.",
        "test_focus": "Record commands preserve privacy and never convert blocked evidence into passed evidence.",
    },
]


def build_host_onboarding_depth_plan() -> dict[str, Any]:
    """Build the first P1 product-depth plan without bypassing product-depth gates."""
    selection = build_product_depth_selection()
    candidate = selection["recommended_candidate"]
    cookbook = build_host_failure_cookbook()
    unblock_pack = build_p0_host_unblock_pack()
    implementation_allowed = selection["implementation_allowed"]
    return {
        "plan_status": "ready_for_implementation" if implementation_allowed else "blocked_until_depth_gate_opens",
        "implementation_allowed": implementation_allowed,
        "product_area": candidate["product_area"],
        "triage_bucket": candidate["triage_bucket"],
        "candidate": candidate["candidate"],
        "success_signal": candidate["success_signal"],
        "blocked_reasons": selection["blocked_reasons"],
        "depth_policy": "Do not implement host-onboarding depth work until RC and beta gates open.",
        "implementation_slices": [
            {
                **item,
                "status": "ready" if implementation_allowed else "planned_after_gate",
            }
            for item in _IMPLEMENTATION_SLICES
        ],
        "failure_classes_to_cover": [item["code"] for item in cookbook["failure_cases"]],
        "active_p0_blockers": [
            {
                "host": lane["host"],
                "gate": lane["gate"],
                "failure_class": lane["failure_class"],
            }
            for lane in unblock_pack["recovery_lanes"]
        ],
        "source_docs": [
            "docs/PRODUCT_DEPTH_SELECTION.md",
            "docs/HOST_FAILURE_COOKBOOK.md",
            "docs/P0_HOST_UNBLOCK_PACK.md",
        ],
    }


def render_host_onboarding_depth_plan_markdown(plan: dict[str, Any]) -> str:
    """Render the host-onboarding depth plan as Markdown."""
    lines = [
        "# Host Onboarding Depth Plan",
        "",
        f"Plan status: `{plan['plan_status']}`",
        f"Implementation allowed: `{str(plan['implementation_allowed']).lower()}`",
        f"Product area: `{plan['product_area']}`",
        f"Triage bucket: `{plan['triage_bucket']}`",
        "",
        "## Depth Policy",
        "",
        plan["depth_policy"],
        "",
        "## Candidate",
        "",
        f"- Candidate: {plan['candidate']}",
        f"- Success signal: {plan['success_signal']}",
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
            "## Implementation Slices",
            "",
            "| Deliverable | Status | Outcome | Test Focus |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"`{item['deliverable']}` | "
        f"`{item['status']}` | "
        f"{item['outcome']} | "
        f"{item['test_focus']} |"
        for item in plan["implementation_slices"]
    )
    lines.extend(["", "## Failure Classes To Cover", ""])
    lines.extend(f"- `{failure_class}`" for failure_class in plan["failure_classes_to_cover"])
    lines.extend(["", "## Active P0 Blockers", ""])
    if plan["active_p0_blockers"]:
        lines.extend(
            f"- {item['host']} / `{item['gate']}`: `{item['failure_class']}`"
            for item in plan["active_p0_blockers"]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in plan["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for the host-onboarding depth plan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_host_onboarding_depth_plan_markdown(build_host_onboarding_depth_plan())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
