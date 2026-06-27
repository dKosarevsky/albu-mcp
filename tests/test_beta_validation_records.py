from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.export_beta_validation_status import (
    build_beta_validation_status,
    render_beta_validation_status_markdown,
)
from scripts.validate_beta_validation_records import validate_beta_validation_records


def test_beta_validation_records_fixture_starts_empty_and_valid() -> None:
    records = validate_beta_validation_records(Path("docs/BETA_VALIDATION_RECORDS.json"))

    assert records.records == []


def test_beta_validation_records_accept_redacted_attempts(tmp_path: Path) -> None:
    records_path = tmp_path / "beta-validation-records.json"
    records_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "workflow_id": "noisy_preview_tuning",
                        "status": "needs_followup",
                        "attempt_date": "2026-06-28",
                        "participant_role": "ML practitioner",
                        "summary": (
                            "Noisy candidate feedback mapped to tags, but the adjusted pipeline still needs review."
                        ),
                        "triage_bucket": "review_agent_v3_gap",
                        "artifact_refs": ["docs/assets/demo/demo_report.md"],
                        "private_data_included": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    records = validate_beta_validation_records(records_path)

    assert records.records[0].workflow_id == "noisy_preview_tuning"
    assert records.records[0].status == "needs_followup"
    assert records.records[0].triage_bucket == "review_agent_v3_gap"


def test_beta_validation_records_reject_private_data(tmp_path: Path) -> None:
    records_path = tmp_path / "beta-validation-records.json"
    records_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "workflow_id": "dataset_health_before_training",
                        "status": "blocked",
                        "attempt_date": "2026-06-28",
                        "participant_role": "Researcher",
                        "summary": "Private screenshot was included in the report.",
                        "triage_bucket": "dataset_quality_gap",
                        "private_data_included": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="private beta validation data"):
        validate_beta_validation_records(records_path)


def test_beta_validation_records_reject_duplicate_attempts(tmp_path: Path) -> None:
    records_path = tmp_path / "beta-validation-records.json"
    attempt = {
        "workflow_id": "robustness_distortion_variants",
        "status": "passed",
        "attempt_date": "2026-06-28",
        "participant_role": "CV engineer",
        "summary": "Contact sheet and preview report were generated under artifact root.",
        "triage_bucket": "workflow_fit_gap",
        "private_data_included": False,
    }
    records_path.write_text(json.dumps({"records": [attempt, attempt]}), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate beta validation attempt"):
        validate_beta_validation_records(records_path)


def test_beta_validation_status_waits_for_all_real_workflow_attempts() -> None:
    status = build_beta_validation_status()

    assert status["validation_status"] == "manual_beta_required"
    assert status["summary"] == {
        "record_count": 0,
        "workflow_count": 3,
        "covered_workflow_count": 0,
        "non_blocked_workflow_count": 0,
        "private_data_record_count": 0,
    }
    assert status["workflow_statuses"][0]["workflow_id"] == "dataset_health_before_training"
    assert all(item["attempt_status"] == "missing" for item in status["workflow_statuses"])


def test_committed_beta_validation_status_is_current() -> None:
    status_path = Path("docs/BETA_VALIDATION_STATUS.md")

    assert status_path.read_text(encoding="utf-8") == render_beta_validation_status_markdown(
        build_beta_validation_status()
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "[docs/BETA_VALIDATION_RECORDS.json](docs/BETA_VALIDATION_RECORDS.json)" in readme
    assert "[docs/BETA_VALIDATION_STATUS.md](docs/BETA_VALIDATION_STATUS.md)" in readme


def test_beta_validation_status_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "beta-validation-status.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_beta_validation_status.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Beta Validation Status\n")
