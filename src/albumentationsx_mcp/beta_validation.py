"""Privacy-safe beta validation recording primitives for CLI adapters."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

WorkflowId = Literal["robustness_distortion_variants", "noisy_preview_tuning", "dataset_health_before_training"]
TriageBucket = Literal["host_setup_gap", "review_agent_v3_gap", "dataset_quality_gap", "docs_gap", "workflow_fit_gap"]
ValidationStatus = Literal["passed", "blocked", "needs_followup"]
_WORKFLOW_IDS: tuple[WorkflowId, ...] = (
    "dataset_health_before_training",
    "noisy_preview_tuning",
    "robustness_distortion_variants",
)
_TRIAGE_BUCKETS: tuple[TriageBucket, ...] = (
    "host_setup_gap",
    "review_agent_v3_gap",
    "dataset_quality_gap",
    "docs_gap",
    "workflow_fit_gap",
)
_PRODUCT_AREAS: dict[TriageBucket, str] = {
    "host_setup_gap": "host_onboarding",
    "review_agent_v3_gap": "policy_and_review_agent",
    "dataset_quality_gap": "dataset_quality",
    "docs_gap": "documentation",
    "workflow_fit_gap": "workflow_templates",
}
_NON_BLOCKED_STATUSES = {"passed", "needs_followup"}


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
    write_beta_validation_records(path, updated)
    return updated


def write_beta_validation_records(path: Path, payload: BetaValidationRecords) -> None:
    """Write beta validation records in the canonical JSON representation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(content, encoding="utf-8")


def summarize_beta_validation_records(records: BetaValidationRecords) -> str:
    """Return a compact human-readable beta validation record count."""
    return f"beta validation records are valid (records={len(records.records)})"


def build_beta_attempt_triage(records: BetaValidationRecords) -> dict[str, Any]:
    """Map redacted beta attempts to backlog lanes without opening product-depth gates prematurely."""
    bucket_counts = Counter(record.triage_bucket for record in records.records)
    covered_workflows = {record.workflow_id for record in records.records}
    non_blocked_workflows = {record.workflow_id for record in records.records if record.status in _NON_BLOCKED_STATUSES}
    product_depth_allowed = len(covered_workflows) == len(_WORKFLOW_IDS) and len(non_blocked_workflows) == len(
        _WORKFLOW_IDS
    )
    triage_lanes = [
        {
            "triage_bucket": bucket,
            "signal_count": bucket_counts.get(bucket, 0),
            "product_area": _PRODUCT_AREAS[bucket],
            "recommendation_status": _recommendation_status(
                signal_count=bucket_counts.get(bucket, 0),
                product_depth_allowed=product_depth_allowed,
            ),
        }
        for bucket in _TRIAGE_BUCKETS
    ]
    return {
        "triage_status": "beta_signal_recorded" if records.records else "blocked_until_beta_signal",
        "product_depth_allowed": product_depth_allowed,
        "summary": {
            "record_count": len(records.records),
            "workflow_count": len(_WORKFLOW_IDS),
            "covered_workflow_count": len(covered_workflows),
            "non_blocked_workflow_count": len(non_blocked_workflows),
        },
        "triage_lanes": triage_lanes,
        "next_actions": _triage_next_actions(product_depth_allowed=product_depth_allowed),
    }


def _record_key(record: BetaValidationRecord) -> tuple[str, object, str]:
    return (record.workflow_id, record.attempt_date, record.summary)


def _recommendation_status(*, signal_count: int, product_depth_allowed: bool) -> str:
    if signal_count == 0:
        return "blocked_no_beta_signal"
    if product_depth_allowed:
        return "ready_for_depth_plan"
    return "candidate_backlog_item"


def _triage_next_actions(*, product_depth_allowed: bool) -> list[str]:
    if product_depth_allowed:
        return [
            "Promote repeated beta findings into product-depth implementation plans.",
            "Keep private beta datasets and full logs out of committed records.",
        ]
    return [
        "Record at least one privacy-safe attempt for every beta workflow.",
        "Review candidate backlog lanes without starting product-depth implementation yet.",
    ]
