"""Export beta CV workflows for early AlbumentationsX MCP users."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def build_beta_workflow_pack() -> dict[str, Any]:
    """Build deterministic beta workflows for first external users."""
    return {
        "trial_inputs": [
            "docs/FIRST_10_MINUTES.md",
            "docs/REAL_HOST_EVIDENCE_EXECUTION.md",
            "docs/BETA_WORKFLOW_PACK.md",
        ],
        "success_criteria": [
            "User can render a contact sheet from local images.",
            "User can reject an over-noisy candidate without reading docs.",
            "User can inspect dataset health before augmentation preview work.",
        ],
        "workflows": [
            {
                "id": "robustness_distortion_variants",
                "title": "Robustness Distortion Variants",
                "target_user": "CV engineer preparing robustness data",
                "job": "Make varied distorted previews for robustness review.",
                "mcp_flow": [
                    "run_host_smoke_check",
                    "build_review_packet",
                    "validate_preview_request",
                    "render_preview_batch",
                    "compare_preview_runs",
                    "export_preview_report",
                ],
                "privacy_boundary": "local paths only; no dataset upload",
                "done_when": "Contact sheet and preview report are generated under artifact root.",
            },
            {
                "id": "noisy_preview_tuning",
                "title": "Noisy Preview Tuning",
                "target_user": "ML practitioner reviewing candidate augmentations",
                "job": "Interpret free-form feedback and plan a safer adjustment.",
                "mcp_flow": [
                    "interpret_preview_feedback",
                    "plan_preview_review",
                    "adjust_pipeline",
                    "render_preview_batch",
                    "record_tuning_decision",
                    "export_pipeline",
                ],
                "privacy_boundary": "local paths only; no dataset upload",
                "done_when": "Feedback maps to structured tags and a revised candidate pipeline.",
            },
            {
                "id": "dataset_health_before_training",
                "title": "Dataset Health Before Training",
                "target_user": "Researcher checking annotations before training",
                "job": "Inspect annotations before augmentation preview work.",
                "mcp_flow": [
                    "inspect_dataset_quality",
                    "build_dataset_onboarding_report",
                    "build_review_packet",
                    "validate_preview_request",
                    "render_preview_batch",
                ],
                "privacy_boundary": "local paths only; no dataset upload",
                "done_when": "Dataset issues are reported before preview rendering starts.",
            },
        ],
    }


def render_beta_workflow_pack_markdown(pack: dict[str, Any]) -> str:
    """Render beta workflows as Markdown."""
    lines = ["# Beta Workflow Pack", "", "## Trial Inputs", ""]
    lines.extend(f"- `{item}`" for item in pack["trial_inputs"])
    lines.extend(["", "## Workflows", ""])
    for workflow in pack["workflows"]:
        lines.extend(
            [
                f"### {workflow['id']}",
                "",
                f"- Title: {workflow['title']}",
                f"- Target user: {workflow['target_user']}",
                f"- Job: {workflow['job']}",
                f"- Privacy boundary: {workflow['privacy_boundary']}",
                f"- Done when: {workflow['done_when']}",
                "- MCP flow:",
            ]
        )
        lines.extend(f"  - `{tool}`" for tool in workflow["mcp_flow"])
        lines.append("")
    lines.extend(["## Success Criteria", ""])
    lines.extend(f"- {item}" for item in pack["success_criteria"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for beta workflow pack exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_beta_workflow_pack_markdown(build_beta_workflow_pack())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
