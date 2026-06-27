"""Export product-depth backlog candidates from beta feedback buckets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_feedback_intake import build_beta_feedback_intake

_BACKLOG_BY_BUCKET = {
    "host_setup_gap": {
        "product_area": "host_onboarding",
        "priority": "p1_after_p0",
        "candidate": "Host-specific setup probes and clearer blocked evidence capture.",
        "success_signal": "A beta user can recover from setup failure without maintainer intervention.",
    },
    "review_agent_v3_gap": {
        "product_area": "preview_review_agent",
        "priority": "p1_after_p0",
        "candidate": "Feedback-to-adjustment planning that better handles noisy or unreadable previews.",
        "success_signal": "Repeated noisy-preview feedback maps to safer candidate adjustments.",
    },
    "dataset_quality_gap": {
        "product_area": "dataset_quality",
        "priority": "p1_after_p0",
        "candidate": "Deeper dataset health findings for annotations, class balance, and duplicate handling.",
        "success_signal": "Dataset issues are caught before preview rendering in beta workflows.",
    },
    "docs_gap": {
        "product_area": "host_docs",
        "priority": "p2_after_beta",
        "candidate": "Short host-specific cards for Codex, Claude Code, Cursor, and Claude Desktop.",
        "success_signal": "Users can start the first preview without reading long-form docs.",
    },
    "workflow_fit_gap": {
        "product_area": "cv_workflow_templates",
        "priority": "p2_after_beta",
        "candidate": "More task-specific workflow templates for robustness, OCR, detection, and segmentation.",
        "success_signal": "Beta users select a workflow template without custom prompting.",
    },
}


def build_product_depth_backlog() -> dict[str, Any]:
    """Build product-depth candidates without claiming beta validation signal."""
    intake = build_beta_feedback_intake()
    return {
        "backlog_status": "waiting_for_beta_signal",
        "prioritization_rule": "Do not promote depth work above P0 host evidence until RC gates pass.",
        "items": [
            {
                "triage_bucket": bucket,
                **_BACKLOG_BY_BUCKET[bucket],
            }
            for bucket in intake["triage_buckets"]
        ],
        "quality_bar": [
            "Convert repeated reports into tests before changing behavior.",
            "Keep local dataset privacy and bounded roots unchanged.",
            "Preserve public MCP contract snapshots for existing hosts.",
        ],
        "source_docs": [
            "docs/BETA_FEEDBACK_INTAKE.md",
            "docs/BETA_VALIDATION_SPRINT.md",
            "docs/P0_HOST_EXECUTION_SPRINT.md",
            "docs/V1_RC_CUTOVER_CHECKLIST.md",
        ],
    }


def render_product_depth_backlog_markdown(backlog: dict[str, Any]) -> str:
    """Render product-depth backlog as Markdown."""
    lines = [
        "# Product Depth Backlog",
        "",
        f"Backlog status: `{backlog['backlog_status']}`",
        "",
        "## Prioritization Rule",
        "",
        backlog["prioritization_rule"],
        "",
        "## Backlog Items",
        "",
        "| Triage Bucket | Product Area | Priority | Candidate | Success Signal |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        "| "
        f"`{item['triage_bucket']}` | "
        f"`{item['product_area']}` | "
        f"`{item['priority']}` | "
        f"{item['candidate']} | "
        f"{item['success_signal']} |"
        for item in backlog["items"]
    )
    lines.extend(["", "## Quality Bar", ""])
    lines.extend(f"- {item}" for item in backlog["quality_bar"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in backlog["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for product-depth backlog exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_product_depth_backlog_markdown(build_product_depth_backlog())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
