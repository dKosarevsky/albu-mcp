"""Export beta feedback status from committed redacted records."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_validation_sprint import build_beta_validation_sprint
from scripts.validate_beta_feedback_records import BetaFeedbackRecords, validate_beta_feedback_records

_DEFAULT_RECORDS_PATH = Path("docs/BETA_FEEDBACK_RECORDS.json")


def build_beta_feedback_status(records_path: Path = _DEFAULT_RECORDS_PATH) -> dict[str, Any]:
    """Build beta feedback status without claiming beta validation signal."""
    records = validate_beta_feedback_records(records_path) if records_path.exists() else BetaFeedbackRecords()
    sprint = build_beta_validation_sprint()
    workflows = sorted(slot["workflow_id"] for slot in sprint["participant_slots"])
    buckets = sprint["triage_buckets"]
    workflow_counts = Counter(record.workflow_id for record in records.records)
    bucket_counts = Counter(record.triage_bucket for record in records.records)
    private_count = sum(record.private_data_included for record in records.records)
    return {
        "records_path": str(records_path),
        "feedback_status": "ready_for_triage" if records.records else "waiting_for_beta_signal",
        "privacy_policy": sprint["privacy_policy"],
        "summary": {
            "record_count": len(records.records),
            "private_data_record_count": private_count,
            "triaged_record_count": sum(record.status == "triaged" for record in records.records),
            "converted_to_test_count": sum(record.status == "converted_to_test" for record in records.records),
        },
        "workflow_counts": {workflow: workflow_counts.get(workflow, 0) for workflow in workflows},
        "triage_bucket_counts": {bucket: bucket_counts.get(bucket, 0) for bucket in buckets},
        "next_actions": [
            "Record only redacted beta workflow symptoms.",
            "Map each record to one workflow and one triage bucket.",
            "Convert repeated beta reports into tests before changing behavior.",
        ],
    }


def render_beta_feedback_status_markdown(status: dict[str, Any]) -> str:
    """Render beta feedback status as Markdown."""
    lines = [
        "# Beta Feedback Status",
        "",
        f"Records path: `{status['records_path']}`",
        f"Feedback status: `{status['feedback_status']}`",
        "",
        "## Privacy Policy",
        "",
        status["privacy_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in status["summary"].items())
    lines.extend(["", "## Workflow Counts", ""])
    lines.extend(f"- `{workflow}`: `{count}`" for workflow, count in status["workflow_counts"].items())
    lines.extend(["", "## Triage Bucket Counts", ""])
    lines.extend(f"- `{bucket}`: `{count}`" for bucket, count in status["triage_bucket_counts"].items())
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in status["next_actions"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for beta feedback status exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=_DEFAULT_RECORDS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_beta_feedback_status_markdown(build_beta_feedback_status(args.records))
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
