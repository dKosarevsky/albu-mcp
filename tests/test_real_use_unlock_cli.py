from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_host_setup_probe_cli_reports_one_host_operator_path(tmp_path: Path) -> None:
    allowed_root = tmp_path / "images"
    artifact_root = tmp_path / "artifacts"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "host",
            "setup-probe",
            "--host",
            "Codex",
            "--allowed-root",
            str(allowed_root),
            "--artifact-root",
            str(artifact_root),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["probe_status"] == "manual_probe_required"
    assert payload["writes_records"] is False
    assert payload["summary"]["host_count"] == 1
    assert payload["host_lanes"][0]["host"] == "Codex"
    assert payload["host_lanes"][0]["operator_command"].startswith(
        "uvx --from albumentationsx-mcp albumentationsx-mcp"
    )
    assert "claude_cli" not in payload["host_lanes"][0]["blocking_checks"]
    assert payload["next_action"] == "run_live_probe"


def test_evidence_collect_cli_builds_no_write_operator_wizard(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "collect",
            "--host",
            "Codex",
            "--path",
            str(host_records),
            "--date",
            "2026-07-02",
            "--reviewer",
            "Release operator",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["wizard_status"] == "operator_run_required"
    assert payload["writes_records"] is False
    assert payload["host"] == "Codex"
    assert payload["current_host_status"]["overall_status"] == "missing"
    assert [step["code"] for step in payload["steps"]] == [
        "setup_probe",
        "host_smoke",
        "first_preview_replay",
        "session_manifest",
        "validate_manifest",
        "import_artifacts",
        "privacy_doctor",
        "rc_go_check",
    ]
    assert payload["steps"][0]["command"].startswith("albu-mcp host setup-probe --host Codex")
    assert "--confirm-real-host-observed" in payload["steps"][5]["command"]
    assert "reviewer-observed real MCP host UI" in payload["non_fabrication_policy"]
    assert host_records.read_text(encoding="utf-8") == '{"manual_host_ui": [], "first_10_minutes_replay": []}\n'
