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


def test_preview_first_pack_cli_returns_short_no_render_handoff(tmp_path: Path) -> None:
    dataset_path = tmp_path / "images"
    artifact_root = tmp_path / "artifacts"
    dataset_path.mkdir()

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "preview",
            "first-pack",
            "--dataset-path",
            str(dataset_path),
            "--allowed-root",
            str(tmp_path),
            "--artifact-root",
            str(artifact_root),
            "--task",
            "classification",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["pack_status"] == "ready_to_run"
    assert payload["writes_records"] is False
    assert payload["renders_images"] is False
    assert payload["dataset_path"] == str(dataset_path)
    assert [step["tool"] for step in payload["mcp_sequence"]] == [
        "run_host_smoke_check",
        "plan_dataset_onboarding",
        "build_review_packet",
        "validate_preview_request",
        "render_preview_batch",
        "compare_preview_runs",
        "plan_preview_review",
        "export_pipeline",
    ]
    assert payload["mcp_sequence"][3]["gate"] == "continue only when valid=true"
    assert payload["bounded_roots"]["allowed_root"] == str(tmp_path)
    assert "albumentationsx://examples/first-preview" in payload["host_instruction"]


def test_beta_loop_pack_cli_writes_privacy_safe_operator_files(tmp_path: Path) -> None:
    records_path = tmp_path / "BETA_VALIDATION_RECORDS.json"
    output_dir = tmp_path / "beta-loop"
    records_path.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "loop-pack",
            "--path",
            str(records_path),
            "--output-dir",
            str(output_dir),
            "--participant-role",
            "CV engineer",
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    expected_files = {
        "beta-loop-index.md",
        "beta-invite-copy.md",
        "beta-privacy-checklist.md",
        "beta-import-instructions.md",
        "beta-status-summary.md",
        "dataset-health-before-training-beta-response.json",
        "noisy-preview-tuning-beta-response.json",
        "robustness-distortion-variants-beta-response.json",
    }
    index = (output_dir / "beta-loop-index.md").read_text(encoding="utf-8")
    template = json.loads((output_dir / "noisy-preview-tuning-beta-response.json").read_text(encoding="utf-8"))

    assert result.stdout == f"wrote beta loop-pack with {len(expected_files)} artifacts to {output_dir}\n"
    assert expected_files <= {path.name for path in output_dir.iterdir()}
    assert "redacted beta attempts" in index
    assert "albu-mcp beta response-import-dir" in (output_dir / "beta-import-instructions.md").read_text(
        encoding="utf-8"
    )
    assert template["participant_role"] == "CV engineer"
    assert template["private_data_included"] is False
    assert records_path.read_text(encoding="utf-8") == '{"records": []}\n'
