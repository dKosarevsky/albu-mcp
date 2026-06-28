from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.validate_beta_validation_records import validate_beta_validation_records
from scripts.validate_host_manual_runs import validate_host_manual_runs


def test_package_cli_records_host_evidence_and_prints_status(tmp_path: Path) -> None:
    evidence_path = tmp_path / "HOST_MANUAL_RUNS.json"

    host_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "record-host-ui",
            "--path",
            str(evidence_path),
            "--host",
            "Codex",
            "--status",
            "passed",
            "--date",
            "2026-06-28",
            "--evidence",
            "Codex listed MCP tools and completed run_host_smoke_check in a reviewer-observed session.",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    replay_result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "record-first-10-minutes",
            "--path",
            str(evidence_path),
            "--host",
            "Codex",
            "--status",
            "passed",
            "--date",
            "2026-06-28",
            "--evidence",
            "Codex completed the first-10-minutes replay from install to preview comparison.",
            "--artifact",
            "docs/assets/demo/demo_report.md",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    status_result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "status",
            "--path",
            str(evidence_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    records = validate_host_manual_runs(evidence_path)
    assert "recorded Codex passed" in host_result.stdout
    assert "recorded first-10-minutes Codex passed" in replay_result.stdout
    assert status_result.stdout == "host evidence records are valid (manual_host_ui=1, first_10_minutes_replay=1)\n"
    assert records.manual_host_ui[0].host == "Codex"
    assert records.first_10_minutes_replay[0].artifacts == ["docs/assets/demo/demo_report.md"]


def test_package_cli_records_beta_attempt_and_prints_status(tmp_path: Path) -> None:
    records_path = tmp_path / "BETA_VALIDATION_RECORDS.json"

    record_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "record-attempt",
            "--path",
            str(records_path),
            "--workflow-id",
            "robustness_distortion_variants",
            "--status",
            "needs_followup",
            "--attempt-date",
            "2026-06-28",
            "--participant-role",
            "CV engineer",
            "--summary",
            "Generated distorted variants, but one example was too noisy for object recognition.",
            "--triage-bucket",
            "review_agent_v3_gap",
            "--artifact-ref",
            "docs/assets/demo/contact_sheet.png",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    status_result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "status",
            "--path",
            str(records_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    records = validate_beta_validation_records(records_path)
    assert "recorded beta validation attempt robustness_distortion_variants" in record_result.stdout
    assert status_result.stdout == "beta validation records are valid (records=1)\n"
    assert records.records[0].private_data_included is False
    assert records.records[0].triage_bucket == "review_agent_v3_gap"


def test_package_cli_triages_beta_attempts_to_backlog_lanes(tmp_path: Path) -> None:
    records_path = tmp_path / "BETA_VALIDATION_RECORDS.json"
    subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "record-attempt",
            "--path",
            str(records_path),
            "--workflow-id",
            "noisy_preview_tuning",
            "--status",
            "needs_followup",
            "--attempt-date",
            "2026-06-28",
            "--participant-role",
            "ML practitioner",
            "--summary",
            "Noisy candidate feedback mapped to tags, but the adjusted pipeline still needs review.",
            "--triage-bucket",
            "review_agent_v3_gap",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    triage_result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "triage",
            "--path",
            str(records_path),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(triage_result.stdout)
    lane = next(item for item in payload["triage_lanes"] if item["triage_bucket"] == "review_agent_v3_gap")

    assert payload["triage_status"] == "beta_signal_recorded"
    assert payload["product_depth_allowed"] is False
    assert payload["summary"]["record_count"] == 1
    assert lane["signal_count"] == 1
    assert lane["recommendation_status"] == "candidate_backlog_item"


def test_readme_and_usage_document_operator_cli() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    usage = Path("docs/USAGE.md").read_text(encoding="utf-8")

    assert "albu-mcp evidence record-host-ui" in readme
    assert "albu-mcp beta triage --format json" in readme
    assert "`plan_augmentation_policy`" in readme
    assert "albu-mcp evidence status" in usage
    assert "albu-mcp beta record-attempt" in usage
    assert "`plan_augmentation_policy`" in usage
