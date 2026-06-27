"""Validate privacy-safe beta validation attempt records."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

WorkflowId = Literal["robustness_distortion_variants", "noisy_preview_tuning", "dataset_health_before_training"]
TriageBucket = Literal["host_setup_gap", "review_agent_v3_gap", "dataset_quality_gap", "docs_gap", "workflow_fit_gap"]
ValidationStatus = Literal["passed", "blocked", "needs_followup"]


class BetaValidationRecord(BaseModel):
    """One redacted real beta workflow attempt."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    workflow_id: WorkflowId
    status: ValidationStatus
    attempt_date: date
    participant_role: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    triage_bucket: TriageBucket
    artifact_refs: list[str] = Field(default_factory=list)
    private_data_included: bool = False

    @model_validator(mode="after")
    def reject_private_data(self) -> BetaValidationRecord:
        """Keep beta validation records privacy-safe by construction."""
        if self.private_data_included:
            msg = "private beta validation data must be redacted before recording"
            raise ValueError(msg)
        return self


class BetaValidationRecords(BaseModel):
    """Committed beta validation attempts."""

    model_config = ConfigDict(extra="forbid")

    records: list[BetaValidationRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_unique_attempts(self) -> BetaValidationRecords:
        """Reject duplicate attempts before status reports are generated."""
        seen: set[tuple[str, date, str]] = set()
        for record in self.records:
            key = (record.workflow_id, record.attempt_date, record.summary)
            if key in seen:
                msg = f"Duplicate beta validation attempt for {record.workflow_id!r} on {record.attempt_date}"
                raise ValueError(msg)
            seen.add(key)
        return self


def validate_beta_validation_records(
    path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
) -> BetaValidationRecords:
    """Load and validate beta validation records."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return BetaValidationRecords.model_validate(payload)
    except json.JSONDecodeError as exc:
        msg = f"{path}: invalid JSON: {exc.msg}"
        raise ValueError(msg) from exc
    except ValidationError as exc:
        msg = f"{path}: invalid beta validation records\n{exc}"
        raise ValueError(msg) from exc


def main() -> None:
    """CLI entrypoint for beta validation record checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    args = parser.parse_args()

    records = validate_beta_validation_records(args.path)
    sys.stdout.write(f"beta validation records are valid ({len(records.records)} records)\n")


if __name__ == "__main__":
    main()
