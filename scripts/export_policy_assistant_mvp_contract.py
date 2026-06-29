"""Export the gated MVP contract for feedback-aware policy recommendation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_policy_assistant_plan import build_policy_assistant_plan


def build_policy_assistant_mvp_contract() -> dict[str, Any]:
    """Build an MVP contract that allows only preview-gated starter policy planning."""
    plan = build_policy_assistant_plan()
    return {
        "contract_status": plan["plan_status"],
        "runtime_implementation_allowed": plan["implementation_allowed"],
        "safe_runtime_mvp_available": True,
        "production_policy_acceptance_allowed": False,
        "first_slice": plan["first_slice"],
        "blocked_reasons": plan["blocked_reasons"],
        "contract_policy": (
            "Safe runtime MVP behavior may produce starter candidates only. It does not open product-depth, "
            "RC, beta, export, or production policy acceptance gates without real preview and host evidence."
        ),
        "runtime_tools": [
            "plan_augmentation_policy",
            "plan_augmentation_policy_candidates",
        ],
        "interfaces": [
            {
                "name": "policy_context",
                "fields": ["task", "sample_count", "annotation_type", "preview_constraints"],
                "purpose": "Carry dataset and review context into recommendation planning.",
            },
            {
                "name": "feedback_signal",
                "fields": ["tag", "severity", "freeform_note", "rejected_candidate_id"],
                "purpose": "Normalize user feedback such as too_noisy or object_lost.",
            },
            {
                "name": "recommendation_result",
                "fields": ["candidate_pipeline", "risk_notes", "next_preview_request", "export_hint"],
                "purpose": "Describe the next safe policy candidate without mutating files.",
            },
            {
                "name": "candidate_set",
                "fields": ["candidates", "candidate_count", "selection_policy", "preview_gate"],
                "purpose": "Return three to five ranked preview-gated policy candidates for human review.",
            },
        ],
        "golden_scenarios": [
            "too_noisy_high_reduces_noise_strength",
            "object_lost_reduces_geometric_distortion",
            "looks_good_preserves_exportable_pipeline",
        ],
        "source_docs": [
            "docs/POLICY_ASSISTANT_PLAN.md",
            "docs/POLICY_ASSISTANT_MVP_CONTRACT.md",
            "docs/PRODUCT_DEPTH_SELECTION.md",
            "docs/BETA_TO_BACKLOG_TRIAGE.md",
        ],
    }


def render_policy_assistant_mvp_contract_markdown(contract: dict[str, Any]) -> str:
    """Render the policy assistant MVP contract as Markdown."""
    lines = [
        "# Policy Assistant MVP Contract",
        "",
        f"Contract status: `{contract['contract_status']}`",
        f"Runtime implementation allowed: `{str(contract['runtime_implementation_allowed']).lower()}`",
        f"Safe runtime MVP available: `{str(contract['safe_runtime_mvp_available']).lower()}`",
        f"Production policy acceptance allowed: `{str(contract['production_policy_acceptance_allowed']).lower()}`",
        f"First slice: `{contract['first_slice']}`",
        "",
        "## Contract Policy",
        "",
        contract["contract_policy"],
        "",
        "## Blocked Reasons",
        "",
    ]
    if contract["blocked_reasons"]:
        lines.extend(f"- `{reason}`" for reason in contract["blocked_reasons"])
    else:
        lines.append("- none")
    lines.extend(["", "## Runtime Tools", ""])
    lines.extend(f"- `{tool}`" for tool in contract["runtime_tools"])
    lines.extend(
        [
            "",
            "## Interfaces",
            "",
            "| Interface | Fields | Purpose |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"`{interface['name']}` | "
        f"{', '.join(f'`{field}`' for field in interface['fields'])} | "
        f"{interface['purpose']} |"
        for interface in contract["interfaces"]
    )
    lines.extend(["", "## Golden Scenarios", ""])
    lines.extend(f"- `{scenario}`" for scenario in contract["golden_scenarios"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in contract["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for policy assistant MVP contract exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_policy_assistant_mvp_contract_markdown(build_policy_assistant_mvp_contract())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
