"""Export a recording pack for privacy-safe beta validation attempts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_validation_intake import build_beta_validation_intake
from scripts.export_beta_validation_status import build_beta_validation_status

_DEFAULT_RECORDS_PATH = Path("docs/BETA_VALIDATION_RECORDS.json")


def build_beta_validation_recording_pack(records_path: Path = _DEFAULT_RECORDS_PATH) -> dict[str, Any]:
    """Build beta validation recording guidance without creating synthetic records."""
    status = build_beta_validation_status(records_path)
    intake = build_beta_validation_intake(records_path)
    missing_count = intake["summary"]["missing_workflow_count"]
    return {
        "recording_status": "manual_records_required" if missing_count else "ready_for_depth_triage",
        "validation_status": status["validation_status"],
        "records_path": str(records_path),
        "summary": {
            "record_count": status["summary"]["record_count"],
            "workflow_count": status["summary"]["workflow_count"],
            "missing_workflow_count": missing_count,
            "covered_workflow_count": status["summary"]["covered_workflow_count"],
            "private_data_record_count": status["summary"]["private_data_record_count"],
        },
        "recording_policy": (
            "Record only real beta attempts. Synthetic examples can be referenced as artifacts, but they do not "
            "replace participant-observed workflow symptoms."
        ),
        "accepted_statuses": ["passed", "blocked", "needs_followup"],
        "privacy_checklist": intake["privacy_checklist"],
        "recording_lanes": [_recording_lane(lane) for lane in intake["intake_lanes"]],
        "post_recording_commands": [
            "uv run python scripts/validate_beta_validation_records.py",
            "uv run python scripts/export_beta_validation_status.py --output docs/BETA_VALIDATION_STATUS.md",
            "uv run python scripts/export_beta_validation_intake.py --output docs/BETA_VALIDATION_INTAKE.md",
            "uv run python scripts/export_beta_validation_recording_pack.py "
            "--output docs/BETA_VALIDATION_RECORDING_PACK.md",
            "uv run python scripts/export_product_depth_gate.py --output docs/PRODUCT_DEPTH_GATE.md",
            "uv run python scripts/check_release_readiness.py",
        ],
        "source_docs": [
            "docs/BETA_VALIDATION_INTAKE.md",
            "docs/BETA_VALIDATION_STATUS.md",
            "docs/BETA_VALIDATION_RECORDS.json",
            ".github/ISSUE_TEMPLATE/workflow-feedback.yml",
            ".github/ISSUE_TEMPLATE/dataset-health.yml",
        ],
    }


def render_beta_validation_recording_pack_markdown(pack: dict[str, Any]) -> str:
    """Render the beta validation recording pack as Markdown."""
    lines = [
        "# Beta Validation Recording Pack",
        "",
        f"Recording status: `{pack['recording_status']}`",
        f"Validation status: `{pack['validation_status']}`",
        f"Records path: `{pack['records_path']}`",
        "",
        "## Recording Policy",
        "",
        pack["recording_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in pack["summary"].items())
    lines.extend(["", "## Accepted Statuses", ""])
    lines.extend(f"- `{status}`" for status in pack["accepted_statuses"])
    lines.extend(["", "## Privacy Checklist", ""])
    lines.extend(f"- {item}" for item in pack["privacy_checklist"])
    lines.extend(
        [
            "",
            "## Recording Lanes",
            "",
            "| Workflow | Attempt Status | Issue Template | Command | Acceptance Note |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"`{lane['workflow_id']}` | "
        f"`{lane['attempt_status']}` | "
        f"`{lane['issue_template']}` | "
        f"`{lane['record_command']}` | "
        f"{lane['acceptance_note']} |"
        for lane in pack["recording_lanes"]
    )
    lines.extend(["", "## Post-Recording Commands", ""])
    lines.extend(f"- `{command}`" for command in pack["post_recording_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in pack["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for beta validation recording pack exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=_DEFAULT_RECORDS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_beta_validation_recording_pack_markdown(build_beta_validation_recording_pack(args.records))
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _recording_lane(lane: dict[str, Any]) -> dict[str, str]:
    return {
        "workflow_id": lane["workflow_id"],
        "attempt_status": lane["attempt_status"],
        "issue_template": lane["issue_template"],
        "record_command": lane["validation_record_command"],
        "acceptance_note": (
            "Use this command only after a real participant attempt produces a redacted symptom summary."
        ),
    }


if __name__ == "__main__":
    main()
