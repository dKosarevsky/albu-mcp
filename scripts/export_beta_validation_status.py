"""Export beta validation status from committed redacted attempt records."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_validation_sprint import build_beta_validation_sprint
from scripts.validate_beta_validation_records import BetaValidationRecords, validate_beta_validation_records

_DEFAULT_RECORDS_PATH = Path("docs/BETA_VALIDATION_RECORDS.json")
_NON_BLOCKED_STATUSES = {"passed", "needs_followup"}


def build_beta_validation_status(records_path: Path = _DEFAULT_RECORDS_PATH) -> dict[str, Any]:
    """Build beta validation status without claiming missing beta attempts."""
    records = validate_beta_validation_records(records_path) if records_path.exists() else BetaValidationRecords()
    sprint = build_beta_validation_sprint()
    workflows = sorted(slot["workflow_id"] for slot in sprint["participant_slots"])
    workflow_statuses = [_workflow_status(workflow_id=workflow, records=records) for workflow in workflows]
    bucket_counts = Counter(record.triage_bucket for record in records.records)
    covered_count = sum(item["attempt_status"] != "missing" for item in workflow_statuses)
    non_blocked_count = sum(item["attempt_status"] in _NON_BLOCKED_STATUSES for item in workflow_statuses)
    validation_status = (
        "ready_for_depth_triage"
        if covered_count == len(workflows) and non_blocked_count == len(workflows)
        else "manual_beta_required"
    )
    return {
        "records_path": str(records_path),
        "validation_status": validation_status,
        "privacy_policy": sprint["privacy_policy"],
        "minimum_signal": sprint["minimum_signal"],
        "summary": {
            "record_count": len(records.records),
            "workflow_count": len(workflows),
            "covered_workflow_count": covered_count,
            "non_blocked_workflow_count": non_blocked_count,
            "private_data_record_count": sum(record.private_data_included for record in records.records),
        },
        "workflow_statuses": workflow_statuses,
        "triage_bucket_counts": {bucket: bucket_counts.get(bucket, 0) for bucket in sprint["triage_buckets"]},
        "next_actions": _next_actions(validation_status=validation_status),
    }


def render_beta_validation_status_markdown(status: dict[str, Any]) -> str:
    """Render beta validation status as Markdown."""
    lines = [
        "# Beta Validation Status",
        "",
        f"Records path: `{status['records_path']}`",
        f"Validation status: `{status['validation_status']}`",
        "",
        "## Privacy Policy",
        "",
        status["privacy_policy"],
        "",
        "## Minimum Signal",
        "",
        status["minimum_signal"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in status["summary"].items())
    lines.extend(
        [
            "",
            "## Workflow Status",
            "",
            "| Workflow | Attempt Status | Attempt Date | Triage Bucket | Summary |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"`{item['workflow_id']}` | "
        f"`{item['attempt_status']}` | "
        f"`{item['attempt_date']}` | "
        f"`{item['triage_bucket']}` | "
        f"{item['summary']} |"
        for item in status["workflow_statuses"]
    )
    lines.extend(["", "## Triage Bucket Counts", ""])
    lines.extend(f"- `{bucket}`: `{count}`" for bucket, count in status["triage_bucket_counts"].items())
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in status["next_actions"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for beta validation status exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=_DEFAULT_RECORDS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_beta_validation_status_markdown(build_beta_validation_status(args.records))
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _workflow_status(*, workflow_id: str, records: BetaValidationRecords) -> dict[str, str]:
    workflow_records = [record for record in records.records if record.workflow_id == workflow_id]
    if not workflow_records:
        return {
            "workflow_id": workflow_id,
            "attempt_status": "missing",
            "attempt_date": "not_recorded",
            "triage_bucket": "not_recorded",
            "summary": "No real beta workflow attempt recorded.",
        }
    latest = max(workflow_records, key=lambda record: record.attempt_date)
    return {
        "workflow_id": latest.workflow_id,
        "attempt_status": latest.status,
        "attempt_date": latest.attempt_date.isoformat(),
        "triage_bucket": latest.triage_bucket,
        "summary": latest.summary,
    }


def _next_actions(*, validation_status: str) -> list[str]:
    if validation_status == "ready_for_depth_triage":
        return [
            "Review repeated beta validation findings.",
            "Promote only reproduced product-depth gaps into implementation plans.",
            "Keep private datasets and full host logs out of committed records.",
        ]
    return [
        "Run at least one real attempt for each beta workflow.",
        "Record only redacted workflow symptoms and artifact references.",
        "Keep product-depth reprioritization blocked until every beta workflow has signal.",
    ]


if __name__ == "__main__":
    main()
