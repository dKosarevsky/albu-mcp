"""Validate privacy-safe beta feedback records."""

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
FeedbackStatus = Literal["new", "triaged", "converted_to_test", "insufficient_evidence"]


class BetaFeedbackRecord(BaseModel):
    """One redacted beta feedback report."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    feedback_id: str = Field(min_length=1)
    workflow_id: WorkflowId
    triage_bucket: TriageBucket
    report_date: date
    reporter_role: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    artifact_refs: list[str] = Field(default_factory=list)
    private_data_included: bool = False
    status: FeedbackStatus = "new"

    @model_validator(mode="after")
    def reject_private_data(self) -> BetaFeedbackRecord:
        """Keep beta records privacy-safe by construction."""
        if self.private_data_included:
            msg = "private beta data must be redacted before recording"
            raise ValueError(msg)
        return self


class BetaFeedbackRecords(BaseModel):
    """Committed beta feedback records."""

    model_config = ConfigDict(extra="forbid")

    records: list[BetaFeedbackRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_unique_feedback_ids(self) -> BetaFeedbackRecords:
        """Reject duplicate feedback identifiers before reports are generated."""
        seen: set[str] = set()
        for record in self.records:
            if record.feedback_id in seen:
                msg = f"Duplicate beta feedback record {record.feedback_id!r}"
                raise ValueError(msg)
            seen.add(record.feedback_id)
        return self


def validate_beta_feedback_records(path: Path = Path("docs/BETA_FEEDBACK_RECORDS.json")) -> BetaFeedbackRecords:
    """Load and validate beta feedback records."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return BetaFeedbackRecords.model_validate(payload)
    except json.JSONDecodeError as exc:
        msg = f"{path}: invalid JSON: {exc.msg}"
        raise ValueError(msg) from exc
    except ValidationError as exc:
        msg = f"{path}: invalid beta feedback records\n{exc}"
        raise ValueError(msg) from exc


def main() -> None:
    """CLI entrypoint for beta feedback validation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path("docs/BETA_FEEDBACK_RECORDS.json"))
    args = parser.parse_args()

    records = validate_beta_feedback_records(args.path)
    sys.stdout.write(f"beta feedback records are valid ({len(records.records)} records)\n")


if __name__ == "__main__":
    main()
