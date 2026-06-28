"""Export an operator kit for capturing real beta validation attempts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_validation_recording_pack import build_beta_validation_recording_pack


def build_beta_attempt_capture_kit() -> dict[str, Any]:
    """Build a beta attempt capture kit without creating synthetic records."""
    recording = build_beta_validation_recording_pack()
    return {
        "kit_status": "manual_attempts_required"
        if recording["summary"]["missing_workflow_count"]
        else "ready_for_depth_triage",
        "records_path": recording["records_path"],
        "privacy_policy": "Never collect private datasets, tokens, screenshots, or full host logs.",
        "summary": {
            "workflow_count": recording["summary"]["workflow_count"],
            "record_count": recording["summary"]["record_count"],
            "missing_workflow_count": recording["summary"]["missing_workflow_count"],
        },
        "attempt_lanes": [
            {
                "workflow_id": lane["workflow_id"],
                "attempt_status": lane["attempt_status"],
                "issue_template": lane["issue_template"],
                "record_command": lane["record_command"],
                "acceptance_note": lane["acceptance_note"],
            }
            for lane in recording["recording_lanes"]
        ],
        "post_attempt_commands": [
            "uv run python scripts/validate_beta_validation_records.py",
            "uv run python scripts/export_beta_validation_status.py --output docs/BETA_VALIDATION_STATUS.md",
            "uv run python scripts/export_beta_to_backlog_triage.py --output docs/BETA_TO_BACKLOG_TRIAGE.md",
            "uv run python scripts/check_release_readiness.py",
        ],
        "source_docs": [
            "docs/BETA_VALIDATION_RECORDING_PACK.md",
            "docs/BETA_VALIDATION_LOOP.md",
            "docs/BETA_VALIDATION_RECORDS.json",
        ],
    }


def render_beta_attempt_capture_kit_markdown(kit: dict[str, Any]) -> str:
    """Render the beta attempt capture kit as Markdown."""
    lines = [
        "# Beta Attempt Capture Kit",
        "",
        f"Kit status: `{kit['kit_status']}`",
        f"Records path: `{kit['records_path']}`",
        "",
        "## Privacy Policy",
        "",
        kit["privacy_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in kit["summary"].items())
    lines.extend(
        [
            "",
            "## Attempt Lanes",
            "",
            "| Workflow | Attempt Status | Issue Template | Record Command | Acceptance Note |",
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
        for lane in kit["attempt_lanes"]
    )
    lines.extend(["", "## Record Writer", "", "`scripts/record_beta_validation.py` is the only beta attempt writer."])
    lines.extend(["", "## Post-Attempt Commands", ""])
    lines.extend(f"- `{command}`" for command in kit["post_attempt_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in kit["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for beta attempt capture kit exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_beta_attempt_capture_kit_markdown(build_beta_attempt_capture_kit())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
