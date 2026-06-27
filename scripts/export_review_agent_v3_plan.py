"""Export a beta-driven Review Agent v3 plan."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_feedback_status import build_beta_feedback_status
from scripts.export_product_depth_backlog import build_product_depth_backlog


def build_review_agent_v3_plan() -> dict[str, Any]:
    """Build the Review Agent v3 plan without changing runtime behavior."""
    beta_status = build_beta_feedback_status()
    backlog_item = _review_agent_backlog_item()
    return {
        "plan_status": "ready_for_implementation"
        if beta_status["summary"]["record_count"]
        else "waiting_for_beta_signal",
        "triage_bucket": backlog_item["triage_bucket"],
        "product_area": backlog_item["product_area"],
        "priority": backlog_item["priority"],
        "beta_record_count": beta_status["summary"]["record_count"],
        "candidate": backlog_item["candidate"],
        "success_signal": backlog_item["success_signal"],
        "tracks": [
            {
                "track_id": "feedback_intent_calibration",
                "scope": "Map free-form feedback to stable tags, intents, and severity.",
                "test_seed": "Add beta-derived cases to tests/test_review_agent.py.",
            },
            {
                "track_id": "safe_adjustment_planning",
                "scope": "Recommend safer adjustment steps for noisy or unreadable candidates.",
                "test_seed": "Assert destructive transforms are reduced before adding new transforms.",
            },
            {
                "track_id": "object_readability_guard",
                "scope": "Protect object readability when feedback says the object is unrecognizable.",
                "test_seed": "Add regression cases for object_unrecognizable feedback.",
            },
        ],
        "implementation_guards": [
            "Do not change runtime review behavior without repeated beta feedback or a failing test.",
            "Preserve existing review_agent output fields and contract snapshots.",
            "Keep the first implementation behind tests before updating public docs.",
        ],
        "acceptance_gates": [
            "At least one repeated review_agent_v3_gap record exists or a maintainer supplies a concrete failing case.",
            "New tests fail before implementation and pass after implementation.",
            "Golden MCP evals and output contract snapshots remain stable or are intentionally updated.",
        ],
        "source_docs": [
            "docs/BETA_FEEDBACK_STATUS.md",
            "docs/PRODUCT_DEPTH_BACKLOG.md",
            "docs/BETA_VALIDATION_SPRINT.md",
        ],
    }


def render_review_agent_v3_plan_markdown(plan: dict[str, Any]) -> str:
    """Render the Review Agent v3 plan as Markdown."""
    lines = [
        "# Review Agent V3 Plan",
        "",
        f"Plan status: `{plan['plan_status']}`",
        f"Triage bucket: `{plan['triage_bucket']}`",
        f"Product area: `{plan['product_area']}`",
        f"Priority: `{plan['priority']}`",
        f"Beta record count: `{plan['beta_record_count']}`",
        "",
        "## Candidate",
        "",
        plan["candidate"],
        "",
        "## Success Signal",
        "",
        plan["success_signal"],
        "",
        "## Tracks",
        "",
        "| Track | Scope | Test Seed |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| `{track['track_id']}` | {track['scope']} | {track['test_seed']} |" for track in plan["tracks"])
    lines.extend(["", "## Implementation Guards", ""])
    lines.extend(f"- {guard}" for guard in plan["implementation_guards"])
    lines.extend(["", "## Acceptance Gates", ""])
    lines.extend(f"- {gate}" for gate in plan["acceptance_gates"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in plan["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for Review Agent v3 plan exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_review_agent_v3_plan_markdown(build_review_agent_v3_plan())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _review_agent_backlog_item() -> dict[str, Any]:
    backlog = build_product_depth_backlog()
    return next(item for item in backlog["items"] if item["triage_bucket"] == "review_agent_v3_gap")


if __name__ == "__main__":
    main()
