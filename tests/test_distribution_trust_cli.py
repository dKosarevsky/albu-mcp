from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_distribution_readiness_blocks_public_release_without_trust_gates(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "distribution",
            "readiness",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["distribution_status"] == "blocked"
    assert payload["publish_allowed"] is False
    assert payload["channels"]["pypi"]["status"] == "blocked"
    assert payload["channels"]["mcp_registry"]["status"] == "blocked"
    assert "rc_reopen_not_allowed" in payload["channels"]["github_release"]["blocked_reasons"]
    assert payload["next_actions"][0] == "Do not publish public release artifacts until trust gates pass."


def test_trust_audit_reports_next_safest_command(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "trust",
            "audit",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["audit_status"] == "action_required"
    assert payload["trust_score"] == 0
    assert payload["evidence"]["plan_status"] == "blocked"
    assert payload["beta"]["campaign_status"] == "blocked_until_beta_signal"
    assert payload["distribution"]["distribution_status"] == "blocked"
    assert payload["recommended_next_command"] == "albu-mcp evidence unblock-plan --format json"


def test_trust_next_returns_machine_readable_blocked_gate(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "trust",
            "next",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["next_status"] == "blocked"
    assert payload["blocked_gate"] == "p0_host_evidence"
    assert payload["reason_code"] == "p0_host_evidence_missing_or_blocked"
    assert payload["recommended_command"] == "albu-mcp evidence execution-packet --host Codex --format json"
    assert payload["follow_up_command"] == "albu-mcp evidence artifact-doctor --format json"


def test_rc_rehearsal_v2_reports_hold_scenario_without_publish_commands(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "rc",
            "rehearse",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--release-tag",
            "v1.15.0-rc.1",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["rehearsal_status"] == "hold"
    assert payload["release_tag"] == "v1.15.0-rc.1"
    assert payload["execution_policy"] == "report_only"
    assert payload["allowed_publish_commands"] == []
    assert payload["release_note_artifacts"] == [
        "docs/RC_RELEASE_DECISION_REPORT.md",
        "docs/GOVERNED_100_ITERATION_REPORT.md",
        "docs/POLICY_ASSISTANT_MVP_CONTRACT.md",
    ]
    assert payload["next_actions"][0] == "Do not tag or publish during rehearsal while gates are blocked."
