from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.validate_host_manual_runs import validate_host_manual_runs


def test_evidence_run_session_prints_guided_plan_without_writing_records(tmp_path: Path) -> None:
    records_path = tmp_path / "HOST_MANUAL_RUNS.json"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "run-session",
            "--host",
            "Codex",
            "--path",
            str(records_path),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["host"] == "Codex"
    assert payload["session_status"] == "operator_run_required"
    assert payload["non_fabrication_policy"].startswith("Record passed only after")
    assert payload["writes_records"] is False
    assert records_path.exists() is False
    assert "run_host_smoke_check" in payload["operator_steps"][1]["action"]
    assert "albu-mcp evidence import-artifacts" in payload["recording_commands"]["passed"]


def test_evidence_import_artifacts_requires_confirmation_for_passed(tmp_path: Path) -> None:
    records_path = tmp_path / "HOST_MANUAL_RUNS.json"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "import-artifacts",
            "--path",
            str(records_path),
            "--host",
            "Codex",
            "--status",
            "passed",
            "--date",
            "2026-06-29",
            "--evidence",
            "Codex preview_ready was observed in the host UI.",
            "--artifact",
            "docs/assets/demo/demo_report.md",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "--confirm-real-host-observed is required when recording passed evidence" in result.stderr
    assert records_path.exists() is False


def test_evidence_import_artifacts_records_both_required_host_gates(tmp_path: Path) -> None:
    records_path = tmp_path / "HOST_MANUAL_RUNS.json"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "import-artifacts",
            "--path",
            str(records_path),
            "--host",
            "Codex",
            "--status",
            "passed",
            "--date",
            "2026-06-29",
            "--evidence",
            "Codex listed tools, completed run_host_smoke_check, reached preview_ready, and replayed first preview.",
            "--artifact",
            "docs/assets/demo/demo_report.md",
            "--confirm-real-host-observed",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    records = validate_host_manual_runs(records_path)

    assert "imported Codex passed evidence for manual_host_ui and first_10_minutes_replay" in result.stdout
    assert records.manual_host_ui[0].status == "passed"
    assert records.first_10_minutes_replay[0].status == "passed"
    assert records.first_10_minutes_replay[0].artifacts == ["docs/assets/demo/demo_report.md"]


def test_evidence_doctor_reports_missing_hosts_and_remediation(tmp_path: Path) -> None:
    records_path = tmp_path / "HOST_MANUAL_RUNS.json"
    records_path.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "doctor",
            "--path",
            str(records_path),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["rc_reopen_allowed"] is False
    assert payload["summary"] == {
        "required_gate_count": 4,
        "passed_gate_count": 0,
        "blocked_gate_count": 0,
        "missing_gate_count": 4,
    }
    assert payload["host_statuses"]["Codex"]["overall_status"] == "missing"
    assert payload["host_statuses"]["Claude Code"]["remediation_actions"][0]["code"] == "install_or_expose_claude_cli"
    assert payload["host_statuses"]["Codex"]["remediation_actions"][0]["code"] == "run_codex_visible_tool_approval"


def test_evidence_unblock_plan_prioritizes_real_host_gaps_without_writing_records(tmp_path: Path) -> None:
    records_path = tmp_path / "HOST_MANUAL_RUNS.json"
    records_path.write_text(
        json.dumps(
            {
                "manual_host_ui": [
                    {
                        "host": "Codex",
                        "status": "blocked",
                        "date": "2026-06-28",
                        "evidence": "Codex host UI was not reviewer-observed.",
                    }
                ],
                "first_10_minutes_replay": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "unblock-plan",
            "--path",
            str(records_path),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["plan_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["blocked_host_count"] == 2
    assert payload["first_blocker"]["host"] == "Codex"
    assert payload["first_blocker"]["missing_gates"] == ["manual_host_ui", "first_10_minutes_replay"]
    assert payload["host_unblock_queue"][0]["recommended_command"].startswith("albu-mcp evidence run-session")
    assert "--confirm-real-host-observed" in payload["host_unblock_queue"][0]["acceptance_command"]
    assert payload["next_actions"][0] == "Run the first recommended_command in a real MCP host session."
