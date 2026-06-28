"""Export a beta validation sprint for real computer-vision users."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_feedback_intake import build_beta_feedback_intake
from scripts.export_beta_workflow_pack import build_beta_workflow_pack


def build_beta_validation_sprint() -> dict[str, Any]:
    """Build a privacy-safe beta validation sprint without claiming user evidence."""
    workflow_pack = build_beta_workflow_pack()
    intake = build_beta_feedback_intake()
    intake_by_workflow = {item["workflow_id"]: item for item in intake["workflow_intake"]}
    return {
        "validation_status": "manual_beta_required",
        "privacy_policy": intake["privacy_policy"],
        "minimum_signal": "At least one real user attempt per beta workflow before product-depth reprioritization.",
        "participant_slots": [
            {
                "workflow_id": workflow["id"],
                "target_user": workflow["target_user"],
                "job": workflow["job"],
                "mcp_flow": workflow["mcp_flow"],
                "expected_feedback": intake_by_workflow[workflow["id"]]["expected_feedback"],
                "done_when": workflow["done_when"],
            }
            for workflow in workflow_pack["workflows"]
        ],
        "recording_commands": [
            _recording_command(
                workflow_id=workflow["id"],
                participant_role=workflow["target_user"],
                triage_bucket=intake_by_workflow[workflow["id"]]["triage_hint"],
            )
            for workflow in workflow_pack["workflows"]
        ],
        "triage_buckets": intake["triage_buckets"],
        "weekly_cadence": [
            "Review new GitHub issues, beta notes, and redacted artifact references.",
            "Map every report to one workflow and one triage bucket.",
            "Convert repeated beta reports into tests before changing behavior.",
            "Regenerate docs/BETA_FEEDBACK_INTAKE.md and docs/PRODUCT_DEPTH_BACKLOG.md after accepted changes.",
        ],
        "exit_criteria": [
            "Each beta workflow has at least one real user attempt.",
            "Every blocker is either reproduced, triaged, or explicitly marked insufficient evidence.",
            "No private datasets, tokens, screenshots, or full host logs are collected.",
        ],
    }


def render_beta_validation_sprint_markdown(sprint: dict[str, Any]) -> str:
    """Render the beta validation sprint as Markdown."""
    lines = [
        "# Beta Validation Sprint",
        "",
        f"Validation status: `{sprint['validation_status']}`",
        "",
        "## Privacy Policy",
        "",
        sprint["privacy_policy"],
        "",
        "## Minimum Signal",
        "",
        sprint["minimum_signal"],
        "",
        "## Participant Slots",
        "",
    ]
    for slot in sprint["participant_slots"]:
        lines.extend(
            [
                f"### {slot['workflow_id']}",
                "",
                f"- Target user: {slot['target_user']}",
                f"- Job: {slot['job']}",
                f"- Done when: {slot['done_when']}",
                "- MCP flow:",
            ]
        )
        lines.extend(f"  - `{tool}`" for tool in slot["mcp_flow"])
        lines.append("- Expected feedback:")
        lines.extend(f"  - {item}" for item in slot["expected_feedback"])
        lines.append("")
    lines.extend(["## Recording Commands", ""])
    lines.extend(f"- `{command}`" for command in sprint["recording_commands"])
    lines.extend(["## Triage Buckets", ""])
    lines.extend(f"- `{bucket}`" for bucket in sprint["triage_buckets"])
    lines.extend(["", "## Weekly Cadence", ""])
    lines.extend(f"- {item}" for item in sprint["weekly_cadence"])
    lines.extend(["", "## Exit Criteria", ""])
    lines.extend(f"- {item}" for item in sprint["exit_criteria"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for beta validation sprint exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_beta_validation_sprint_markdown(build_beta_validation_sprint())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _recording_command(*, workflow_id: str, participant_role: str, triage_bucket: str) -> str:
    return (
        "uv run python scripts/record_beta_validation.py "
        f"--workflow-id {workflow_id} "
        "--status needs_followup "
        "--attempt-date YYYY-MM-DD "
        f"--participant-role {participant_role!r} "
        "--summary 'Redacted real beta workflow attempt summary.' "
        f"--triage-bucket {triage_bucket} "
        "--artifact-ref docs/assets/demo/demo_report.md"
    )


if __name__ == "__main__":
    main()
