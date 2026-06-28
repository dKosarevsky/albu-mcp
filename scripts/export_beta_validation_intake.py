"""Export a privacy-safe beta validation intake packet."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_campaign_execution import build_beta_campaign_execution

_DEFAULT_RECORDS_PATH = Path("docs/BETA_VALIDATION_RECORDS.json")
_ISSUE_TEMPLATE_BY_WORKFLOW = {
    "robustness_distortion_variants": ".github/ISSUE_TEMPLATE/workflow-feedback.yml",
    "noisy_preview_tuning": ".github/ISSUE_TEMPLATE/workflow-feedback.yml",
    "dataset_health_before_training": ".github/ISSUE_TEMPLATE/dataset-health.yml",
}
_REQUIRED_RECORD_FIELDS = [
    "workflow_id",
    "status",
    "attempt_date",
    "participant_role",
    "summary",
    "triage_bucket",
    "artifact_ref",
]


def build_beta_validation_intake(records_path: Path = _DEFAULT_RECORDS_PATH) -> dict[str, Any]:
    """Build a beta intake packet from campaign execution lanes."""
    execution = build_beta_campaign_execution(records_path)
    missing_count = execution["summary"]["missing_workflow_count"]
    return {
        "intake_status": "collecting_beta_validation" if missing_count else "ready_for_depth_triage",
        "validation_status": execution["validation_status"],
        "feedback_status": execution["feedback_status"],
        "records_path": str(records_path),
        "summary": {
            "workflow_count": execution["summary"]["workflow_count"],
            "missing_workflow_count": missing_count,
            "recorded_workflow_count": execution["summary"]["recorded_workflow_count"],
            "target_beta_records": execution["summary"]["target_beta_records"],
        },
        "minimum_signal": (
            "Record at least one privacy-safe attempt for every beta workflow before product-depth reprioritization."
        ),
        "privacy_checklist": [
            "Do not request or commit private datasets, raw images, credentials, or unredacted local paths.",
            "Prefer synthetic/demo images and generated artifact references.",
            "Redact participant identity to a role, such as CV engineer or ML practitioner.",
            "Capture workflow symptoms and expected behavior instead of full host logs.",
        ],
        "intake_lanes": [_intake_lane(lane) for lane in execution["invite_lanes"]],
        "post_intake_commands": [
            "uv run python scripts/validate_beta_validation_records.py",
            "uv run python scripts/export_beta_validation_status.py --output docs/BETA_VALIDATION_STATUS.md",
            "uv run python scripts/export_beta_campaign_execution.py --output docs/BETA_CAMPAIGN_EXECUTION.md",
            "uv run python scripts/export_beta_validation_intake.py --output docs/BETA_VALIDATION_INTAKE.md",
            "uv run python scripts/export_product_depth_gate.py --output docs/PRODUCT_DEPTH_GATE.md",
            "uv run python scripts/check_release_readiness.py",
        ],
        "source_docs": [
            "docs/BETA_CAMPAIGN_EXECUTION.md",
            "docs/BETA_VALIDATION_STATUS.md",
            "docs/BETA_VALIDATION_RECORDS.json",
            ".github/ISSUE_TEMPLATE/workflow-feedback.yml",
            ".github/ISSUE_TEMPLATE/dataset-health.yml",
        ],
    }


def render_beta_validation_intake_markdown(intake: dict[str, Any]) -> str:
    """Render beta validation intake as Markdown."""
    lines = [
        "# Beta Validation Intake",
        "",
        f"Intake status: `{intake['intake_status']}`",
        f"Validation status: `{intake['validation_status']}`",
        f"Feedback status: `{intake['feedback_status']}`",
        f"Records path: `{intake['records_path']}`",
        "",
        "## Minimum Signal",
        "",
        intake["minimum_signal"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in intake["summary"].items())
    lines.extend(["", "## Privacy Checklist", ""])
    lines.extend(f"- {item}" for item in intake["privacy_checklist"])
    lines.extend(
        [
            "",
            "## Intake Lanes",
            "",
            "| Workflow | Attempt Status | Issue Template | Record Command | Required Fields |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"`{lane['workflow_id']}` | "
        f"`{lane['attempt_status']}` | "
        f"`{lane['issue_template']}` | "
        f"`{lane['validation_record_command']}` | "
        f"{', '.join(f'`{field}`' for field in lane['required_record_fields'])} |"
        for lane in intake["intake_lanes"]
    )
    lines.extend(["", "## Post-Intake Commands", ""])
    lines.extend(f"- `{command}`" for command in intake["post_intake_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in intake["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for beta validation intake exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=_DEFAULT_RECORDS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_beta_validation_intake_markdown(build_beta_validation_intake(args.records))
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _intake_lane(lane: dict[str, str]) -> dict[str, Any]:
    return {
        "workflow_id": lane["workflow_id"],
        "title": lane["title"],
        "attempt_status": lane["attempt_status"],
        "issue_template": _ISSUE_TEMPLATE_BY_WORKFLOW[lane["workflow_id"]],
        "validation_record_command": lane["validation_record_command"],
        "required_record_fields": _REQUIRED_RECORD_FIELDS,
    }


if __name__ == "__main__":
    main()
