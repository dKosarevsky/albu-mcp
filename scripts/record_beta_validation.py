"""Record or replace one privacy-safe beta validation attempt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_beta_validation_records import (
    BetaValidationRecord,
    BetaValidationRecords,
    TriageBucket,
    ValidationStatus,
    WorkflowId,
    validate_beta_validation_records,
)


def record_beta_validation(
    *,
    path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    record: BetaValidationRecord,
) -> BetaValidationRecords:
    """Add or replace one beta validation attempt and return the validated payload."""
    current = validate_beta_validation_records(path) if path.exists() else BetaValidationRecords()
    by_key = {_record_key(item): item for item in current.records}
    by_key[_record_key(record)] = record
    updated = BetaValidationRecords(
        records=sorted(by_key.values(), key=lambda item: (item.attempt_date, item.workflow_id, item.summary))
    )
    _write_beta_validation_records(path, updated)
    return updated


def main() -> None:
    """CLI entrypoint for recording redacted beta validation attempts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    parser.add_argument("--workflow-id", choices=get_args(WorkflowId), required=True)
    parser.add_argument("--status", choices=get_args(ValidationStatus), required=True)
    parser.add_argument("--attempt-date", required=True)
    parser.add_argument("--participant-role", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--triage-bucket", choices=get_args(TriageBucket), required=True)
    parser.add_argument("--artifact-ref", action="append", default=[])
    args = parser.parse_args()

    try:
        record_beta_validation(
            path=args.path,
            record=BetaValidationRecord(
                workflow_id=args.workflow_id,
                status=args.status,
                attempt_date=args.attempt_date,
                participant_role=args.participant_role,
                summary=args.summary,
                triage_bucket=args.triage_bucket,
                artifact_refs=args.artifact_ref,
                private_data_included=False,
            ),
        )
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc
    sys.stdout.write(f"recorded beta validation attempt {args.workflow_id} in {args.path}\n")


def _record_key(record: BetaValidationRecord) -> tuple[str, object, str]:
    return (record.workflow_id, record.attempt_date, record.summary)


def _write_beta_validation_records(path: Path, payload: BetaValidationRecords) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
