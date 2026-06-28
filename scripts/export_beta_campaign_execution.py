"""Export an execution checklist for privacy-safe beta validation."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_campaign_pack import build_beta_campaign_pack
from scripts.export_beta_validation_status import build_beta_validation_status

_DEFAULT_RECORDS_PATH = Path("docs/BETA_VALIDATION_RECORDS.json")


def build_beta_campaign_execution(records_path: Path = _DEFAULT_RECORDS_PATH) -> dict[str, Any]:
    """Build beta execution lanes without claiming missing validation attempts."""
    campaign = build_beta_campaign_pack()
    validation = build_beta_validation_status(records_path)
    status_by_workflow = {item["workflow_id"]: item for item in validation["workflow_statuses"]}
    lanes = [
        _invite_lane(workflow=workflow, workflow_status=status_by_workflow[workflow["workflow_id"]])
        for workflow in campaign["workflow_cards"]
    ]
    missing_count = sum(lane["attempt_status"] == "missing" for lane in lanes)
    return {
        "execution_status": campaign["campaign_status"],
        "validation_status": validation["validation_status"],
        "feedback_status": campaign["feedback_status"],
        "privacy_guard": campaign["privacy_guard"],
        "outreach_copy": campaign["outreach_copy"],
        "summary": {
            "workflow_count": len(lanes),
            "missing_workflow_count": missing_count,
            "recorded_workflow_count": len(lanes) - missing_count,
            "target_beta_records": campaign["target_beta_records"],
        },
        "invite_lanes": lanes,
        "completion_rule": (
            "Collect at least one privacy-safe validation record for each beta workflow before product-depth "
            "reprioritization."
        ),
        "post_recording_commands": [
            "uv run python scripts/validate_beta_validation_records.py",
            "uv run python scripts/export_beta_validation_status.py --output docs/BETA_VALIDATION_STATUS.md",
            "uv run python scripts/export_beta_campaign_execution.py --output docs/BETA_CAMPAIGN_EXECUTION.md",
            "uv run python scripts/export_product_depth_gate.py --output docs/PRODUCT_DEPTH_GATE.md",
        ],
        "source_docs": [
            "docs/BETA_CAMPAIGN_PACK.md",
            "docs/BETA_VALIDATION_STATUS.md",
            "docs/BETA_VALIDATION_RECORDS.json",
        ],
    }


def render_beta_campaign_execution_markdown(execution: dict[str, Any]) -> str:
    """Render beta campaign execution as Markdown."""
    lines = [
        "# Beta Campaign Execution",
        "",
        f"Execution status: `{execution['execution_status']}`",
        f"Validation status: `{execution['validation_status']}`",
        f"Feedback status: `{execution['feedback_status']}`",
        "",
        "## Privacy Guard",
        "",
        execution["privacy_guard"],
        "",
        "## Outreach Copy",
        "",
        execution["outreach_copy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in execution["summary"].items())
    lines.extend(
        [
            "",
            "## Invite Lanes",
            "",
            "| Workflow | Attempt Status | Next Action | Validation Record Command |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"`{lane['workflow_id']}` | "
        f"`{lane['attempt_status']}` | "
        f"`{lane['next_action']}` | "
        f"`{lane['validation_record_command']}` |"
        for lane in execution["invite_lanes"]
    )
    lines.extend(["", "## Completion Rule", "", execution["completion_rule"]])
    lines.extend(["", "## Post-Recording Commands", ""])
    lines.extend(f"- `{command}`" for command in execution["post_recording_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in execution["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for beta campaign execution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=_DEFAULT_RECORDS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_beta_campaign_execution_markdown(build_beta_campaign_execution(args.records))
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _invite_lane(*, workflow: dict[str, Any], workflow_status: dict[str, str]) -> dict[str, str]:
    attempt_status = workflow_status["attempt_status"]
    return {
        "workflow_id": workflow["workflow_id"],
        "title": workflow["title"],
        "target_user": workflow["target_user"],
        "attempt_status": attempt_status,
        "next_action": "invite_beta_user" if attempt_status == "missing" else "review_recorded_attempt",
        "validation_record_command": _validation_record_command(workflow=workflow),
    }


def _validation_record_command(*, workflow: dict[str, Any]) -> str:
    args = [
        "uv",
        "run",
        "python",
        "scripts/record_beta_validation.py",
        "--workflow-id",
        workflow["workflow_id"],
        "--status",
        "needs_followup",
        "--attempt-date",
        "YYYY-MM-DD",
        "--participant-role",
        workflow["target_user"],
        "--summary",
        f"Redacted beta attempt for {workflow['workflow_id']}.",
        "--triage-bucket",
        workflow["triage_bucket"],
        "--artifact-ref",
        "docs/assets/demo/demo_report.md",
    ]
    return " ".join(shlex.quote(arg) for arg in args)


if __name__ == "__main__":
    main()
