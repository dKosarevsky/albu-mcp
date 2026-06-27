"""Export a privacy-safe beta feedback intake loop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_workflow_pack import build_beta_workflow_pack

_EXPECTED_FEEDBACK_BY_WORKFLOW = {
    "robustness_distortion_variants": [
        "Contact sheet path",
        "Preview report path",
        "Accepted/rejected candidate",
        "Reason for rejection",
    ],
    "noisy_preview_tuning": [
        "Free-form user note",
        "Structured feedback tags",
        "Recommended next MCP tool",
        "Whether the revised candidate became acceptable",
    ],
    "dataset_health_before_training": [
        "Dataset quality findings",
        "Annotation format",
        "Whether preview was blocked",
        "Requested follow-up",
    ],
}


def build_beta_feedback_intake() -> dict[str, Any]:
    """Build deterministic feedback intake for beta workflows."""
    workflow_pack = build_beta_workflow_pack()
    return {
        "privacy_policy": "Collect workflow symptoms and redacted artifacts, never private datasets.",
        "workflow_intake": [
            {
                "workflow_id": workflow["id"],
                "target_user": workflow["target_user"],
                "job": workflow["job"],
                "expected_feedback": _EXPECTED_FEEDBACK_BY_WORKFLOW[workflow["id"]],
                "triage_hint": _triage_hint(workflow["id"]),
            }
            for workflow in workflow_pack["workflows"]
        ],
        "triage_buckets": [
            "host_setup_gap",
            "review_agent_v3_gap",
            "dataset_quality_gap",
            "docs_gap",
            "workflow_fit_gap",
        ],
        "weekly_loop": [
            "Review new feedback issues and manual beta notes.",
            "Group reports by triage bucket and affected workflow.",
            "Convert repeated reports into tests before changing behavior.",
            "Regenerate beta docs and release readiness reports after accepted changes.",
        ],
    }


def render_beta_feedback_intake_markdown(intake: dict[str, Any]) -> str:
    """Render beta feedback intake as Markdown."""
    lines = [
        "# Beta Feedback Intake",
        "",
        "## Privacy Policy",
        "",
        intake["privacy_policy"],
        "",
        "## Workflow Intake",
        "",
    ]
    for workflow in intake["workflow_intake"]:
        lines.extend(
            [
                f"### {workflow['workflow_id']}",
                "",
                f"- Target user: {workflow['target_user']}",
                f"- Job: {workflow['job']}",
                f"- Triage hint: `{workflow['triage_hint']}`",
                "- Expected feedback:",
            ]
        )
        lines.extend(f"  - {item}" for item in workflow["expected_feedback"])
        lines.append("")
    lines.extend(["## Triage Buckets", ""])
    lines.extend(f"- `{bucket}`" for bucket in intake["triage_buckets"])
    lines.extend(["", "## Weekly Loop", ""])
    lines.extend(f"- {item}" for item in intake["weekly_loop"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for beta feedback intake exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_beta_feedback_intake_markdown(build_beta_feedback_intake())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _triage_hint(workflow_id: str) -> str:
    if workflow_id == "noisy_preview_tuning":
        return "review_agent_v3_gap"
    if workflow_id == "dataset_health_before_training":
        return "dataset_quality_gap"
    return "workflow_fit_gap"


if __name__ == "__main__":
    main()
