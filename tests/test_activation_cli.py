from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_evidence_operator_packet_writes_host_markdown(tmp_path: Path) -> None:
    evidence_path = tmp_path / "HOST_MANUAL_RUNS.json"
    evidence_path.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    output_dir = tmp_path / "operator-packets"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "operator-packet",
            "--path",
            str(evidence_path),
            "--host",
            "Codex",
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    packet_path = output_dir / "codex-evidence-operator-packet.md"
    packet = packet_path.read_text(encoding="utf-8")

    assert result.stdout == f"wrote evidence operator-packet for Codex to {packet_path}\n"
    assert "# Codex Evidence Operator Packet" in packet
    assert "run_host_smoke_check" in packet
    assert "albu-mcp evidence import-artifacts --host 'Codex'" in packet
    assert "Record passed only after a reviewer observes the real MCP host UI flow" in packet


def test_evidence_validate_import_rejects_unconfirmed_passed_evidence_and_does_not_write(
    tmp_path: Path,
) -> None:
    evidence_path = tmp_path / "HOST_MANUAL_RUNS.json"
    empty_records = '{"manual_host_ui": [], "first_10_minutes_replay": []}\n'
    evidence_path.write_text(empty_records, encoding="utf-8")

    rejected = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "validate-import",
            "--path",
            str(evidence_path),
            "--host",
            "Codex",
            "--status",
            "passed",
            "--date",
            "2026-06-30",
            "--evidence",
            "Reviewer observed real Codex MCP host UI.",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    accepted = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "validate-import",
            "--path",
            str(evidence_path),
            "--host",
            "Codex",
            "--status",
            "passed",
            "--date",
            "2026-06-30",
            "--evidence",
            "Reviewer observed real Codex MCP host UI.",
            "--artifact",
            "docs/assets/demo/demo_report.md",
            "--confirm-real-host-observed",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(accepted.stdout)

    assert rejected.returncode == 1
    assert "--confirm-real-host-observed is required" in rejected.stderr
    assert evidence_path.read_text(encoding="utf-8") == empty_records
    assert payload["validation_status"] == "ready_to_import"
    assert payload["writes_records"] is False
    assert payload["artifact_count"] == 1
    assert payload["required_gate_writes"] == ["manual_host_ui", "first_10_minutes_replay"]


def test_beta_intake_wizard_returns_privacy_safe_response_template() -> None:
    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled arguments.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "intake-wizard",
            "--workflow-id",
            "noisy_preview_tuning",
            "--participant-role",
            "CV reviewer",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["wizard_status"] == "ready_to_send"
    assert payload["workflow_id"] == "noisy_preview_tuning"
    assert payload["participant_role"] == "CV reviewer"
    assert payload["privacy_policy"] == "redacted_only"
    assert payload["response_template"]["private_data_included"] is False
    assert "example 8 is too noisy" in payload["participant_prompt"]
    assert "object recognizable" in " ".join(payload["acceptance_rubric"])
    assert "albu-mcp beta record-attempt" in payload["recording_command"]


def test_trust_dashboard_markdown_shows_blocked_gates_and_next_command(tmp_path: Path) -> None:
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
            "dashboard",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--release-tag",
            "v1.15.0-rc.1",
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "# AlbumentationsX MCP Trust Dashboard" in result.stdout
    assert "| Gate | Status | Detail |" in result.stdout
    assert "`p0_host_evidence_missing_or_blocked`" in result.stdout
    assert "albu-mcp evidence execution-packet" in result.stdout
    assert "Report only" in result.stdout
