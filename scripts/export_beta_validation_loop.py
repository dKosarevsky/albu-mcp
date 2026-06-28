"""Export the operator loop for privacy-safe beta validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_validation_recording_pack import build_beta_validation_recording_pack
from scripts.export_beta_validation_sprint import build_beta_validation_sprint
from scripts.export_beta_validation_status import build_beta_validation_status


def build_beta_validation_loop() -> dict[str, Any]:
    """Build the beta validation loop without creating synthetic user records."""
    sprint = build_beta_validation_sprint()
    status = build_beta_validation_status()
    recording = build_beta_validation_recording_pack()
    missing_count = status["summary"]["workflow_count"] - status["summary"]["covered_workflow_count"]
    return {
        "loop_status": status["validation_status"],
        "privacy_policy": sprint["privacy_policy"],
        "records_path": status["records_path"],
        "minimum_signal": status["minimum_signal"],
        "summary": {
            "workflow_count": status["summary"]["workflow_count"],
            "record_count": status["summary"]["record_count"],
            "covered_workflow_count": status["summary"]["covered_workflow_count"],
            "missing_workflow_count": missing_count,
        },
        "next_operator_action": _next_operator_action(missing_count=missing_count),
        "workflow_lanes": [
            {
                "workflow_id": item["workflow_id"],
                "status": item["attempt_status"],
                "attempt_date": item["attempt_date"],
                "triage_bucket": item["triage_bucket"],
                "summary": item["summary"],
            }
            for item in status["workflow_statuses"]
        ],
        "recording_commands": [lane["record_command"] for lane in recording["recording_lanes"]],
        "loop_cadence": [
            "Recruit or observe one real user attempt for each missing workflow.",
            "Record only redacted symptoms and artifact references.",
            "Run validation and regenerate beta status after every record.",
            "Promote repeated findings only after the workflow has real signal.",
        ],
        "exit_criteria": sprint["exit_criteria"],
        "post_record_commands": [
            "uv run python scripts/validate_beta_validation_records.py",
            "uv run python scripts/export_beta_validation_status.py --output docs/BETA_VALIDATION_STATUS.md",
            "uv run python scripts/export_beta_to_backlog_triage.py --output docs/BETA_TO_BACKLOG_TRIAGE.md",
            "uv run python scripts/export_beta_validation_loop.py --output docs/BETA_VALIDATION_LOOP.md",
            "uv run python scripts/check_release_readiness.py",
        ],
        "source_docs": [
            "docs/BETA_VALIDATION_RECORDS.json",
            "docs/BETA_VALIDATION_RECORDING_PACK.md",
            "docs/BETA_VALIDATION_SPRINT.md",
            "docs/BETA_VALIDATION_STATUS.md",
            "docs/BETA_TO_BACKLOG_TRIAGE.md",
        ],
    }


def render_beta_validation_loop_markdown(loop: dict[str, Any]) -> str:
    """Render the beta validation loop as Markdown."""
    lines = [
        "# Beta Validation Loop",
        "",
        f"Loop status: `{loop['loop_status']}`",
        f"Records path: `{loop['records_path']}`",
        f"Next operator action: {loop['next_operator_action']}",
        "",
        "## Privacy Policy",
        "",
        loop["privacy_policy"],
        "",
        "No private datasets, tokens, screenshots, or full host logs are collected.",
        "",
        "## Minimum Signal",
        "",
        loop["minimum_signal"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in loop["summary"].items())
    lines.extend(
        [
            "",
            "## Workflow Lanes",
            "",
            "| Workflow | Status | Attempt Date | Triage Bucket | Summary |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"`{lane['workflow_id']}` | "
        f"`{lane['status']}` | "
        f"`{lane['attempt_date']}` | "
        f"`{lane['triage_bucket']}` | "
        f"{lane['summary']} |"
        for lane in loop["workflow_lanes"]
    )
    lines.extend(["", "## Recording Commands", ""])
    lines.append("`scripts/record_beta_validation.py` is the only beta validation record writer.")
    lines.append("")
    lines.extend(f"- `{command}`" for command in loop["recording_commands"])
    lines.extend(["", "## Loop Cadence", ""])
    lines.extend(f"- {item}" for item in loop["loop_cadence"])
    lines.extend(["", "## Exit Criteria", ""])
    lines.extend(f"- {item}" for item in loop["exit_criteria"])
    lines.extend(["", "## Post-Record Commands", ""])
    lines.extend(f"- `{command}`" for command in loop["post_record_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in loop["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for beta validation loop exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_beta_validation_loop_markdown(build_beta_validation_loop())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _next_operator_action(*, missing_count: int) -> str:
    if missing_count:
        return "Recruit one real user attempt for each missing beta workflow."
    return "Review repeated beta findings and promote only reproduced product-depth gaps."


if __name__ == "__main__":
    main()
