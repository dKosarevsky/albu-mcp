from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from scripts.export_beta_feedback_status import build_beta_feedback_status, render_beta_feedback_status_markdown
from scripts.record_beta_feedback import record_beta_feedback
from scripts.validate_beta_feedback_records import BetaFeedbackRecord, validate_beta_feedback_records


def test_beta_feedback_records_fixture_starts_empty_and_valid() -> None:
    records = validate_beta_feedback_records(Path("docs/BETA_FEEDBACK_RECORDS.json"))

    assert records.records == []


def test_beta_feedback_records_reject_private_data(tmp_path: Path) -> None:
    records_path = tmp_path / "beta-feedback-records.json"
    records_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "feedback_id": "beta-001",
                        "workflow_id": "noisy_preview_tuning",
                        "triage_bucket": "review_agent_v3_gap",
                        "report_date": "2026-06-27",
                        "reporter_role": "ML practitioner",
                        "summary": "User pasted a private dataset path.",
                        "private_data_included": True,
                        "status": "new",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="private beta data"):
        validate_beta_feedback_records(records_path)


def test_record_beta_feedback_writes_sorted_valid_records(tmp_path: Path) -> None:
    records_path = tmp_path / "beta-feedback-records.json"

    record_beta_feedback(
        path=records_path,
        record=BetaFeedbackRecord(
            feedback_id="beta-002",
            workflow_id="dataset_health_before_training",
            triage_bucket="dataset_quality_gap",
            report_date=date(2026, 6, 27),
            reporter_role="Researcher",
            summary="Dataset quality report caught missing annotations before preview.",
            artifact_refs=["docs/assets/demo/demo_report.md"],
            private_data_included=False,
            status="triaged",
        ),
    )

    records = validate_beta_feedback_records(records_path)
    assert [record.feedback_id for record in records.records] == ["beta-002"]
    assert records.records[0].artifact_refs == ["docs/assets/demo/demo_report.md"]


def test_beta_feedback_status_waits_for_real_beta_signal() -> None:
    status = build_beta_feedback_status()

    assert status["feedback_status"] == "waiting_for_beta_signal"
    assert status["summary"]["record_count"] == 0
    assert status["summary"]["private_data_record_count"] == 0
    assert status["workflow_counts"] == {
        "dataset_health_before_training": 0,
        "noisy_preview_tuning": 0,
        "robustness_distortion_variants": 0,
    }


def test_committed_beta_feedback_status_is_current() -> None:
    status_path = Path("docs/BETA_FEEDBACK_STATUS.md")

    assert status_path.read_text(encoding="utf-8") == render_beta_feedback_status_markdown(build_beta_feedback_status())
    assert "[docs/BETA_FEEDBACK_RECORDS.json](docs/BETA_FEEDBACK_RECORDS.json)" in Path("README.md").read_text(
        encoding="utf-8"
    )
    assert "[docs/BETA_FEEDBACK_STATUS.md](docs/BETA_FEEDBACK_STATUS.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_beta_feedback_status_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "beta-feedback-status.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_beta_feedback_status.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Beta Feedback Status\n")
