"""Record or replace one privacy-safe beta feedback report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_beta_feedback_records import (
    BetaFeedbackRecord,
    BetaFeedbackRecords,
    FeedbackStatus,
    TriageBucket,
    WorkflowId,
    validate_beta_feedback_records,
)


def record_beta_feedback(
    *,
    path: Path = Path("docs/BETA_FEEDBACK_RECORDS.json"),
    record: BetaFeedbackRecord,
) -> BetaFeedbackRecords:
    """Add or replace one beta feedback record and return the validated payload."""
    current = validate_beta_feedback_records(path) if path.exists() else BetaFeedbackRecords()
    by_id = {item.feedback_id: item for item in current.records}
    by_id[record.feedback_id] = record
    updated = BetaFeedbackRecords(records=sorted(by_id.values(), key=lambda item: item.feedback_id))
    _write_beta_feedback_records(path, updated)
    return updated


def main() -> None:
    """CLI entrypoint for recording redacted beta feedback."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path("docs/BETA_FEEDBACK_RECORDS.json"))
    parser.add_argument("--feedback-id", required=True)
    parser.add_argument("--workflow-id", choices=get_args(WorkflowId), required=True)
    parser.add_argument("--triage-bucket", choices=get_args(TriageBucket), required=True)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--reporter-role", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--artifact-ref", action="append", default=[])
    parser.add_argument("--status", choices=get_args(FeedbackStatus), default="new")
    args = parser.parse_args()

    try:
        record_beta_feedback(
            path=args.path,
            record=BetaFeedbackRecord(
                feedback_id=args.feedback_id,
                workflow_id=args.workflow_id,
                triage_bucket=args.triage_bucket,
                report_date=args.report_date,
                reporter_role=args.reporter_role,
                summary=args.summary,
                artifact_refs=args.artifact_ref,
                private_data_included=False,
                status=args.status,
            ),
        )
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc
    sys.stdout.write(f"recorded beta feedback {args.feedback_id} in {args.path}\n")


def _write_beta_feedback_records(path: Path, payload: BetaFeedbackRecords) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
