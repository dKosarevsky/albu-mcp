from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_empty_records(tmp_path: Path) -> tuple[Path, Path]:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")
    return host_records, beta_records


def test_intake_bundle_writes_operator_artifacts(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    output_dir = tmp_path / "intake-bundle"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "intake",
            "bundle",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--output-dir",
            str(output_dir),
            "--release-tag",
            "v1.15.0-rc.1",
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    expected_files = {
        "intake-bundle-index.md",
        "manual-evidence-runbook.md",
        "real-host-replay-fixture-pack.md",
        "codex-evidence-import-checklist.md",
        "claude-code-evidence-import-checklist.md",
        "dataset-health-before-training-beta-response.json",
        "noisy-preview-tuning-beta-response.json",
        "robustness-distortion-variants-beta-response.json",
        "release-owner-packet.md",
    }
    written_files = {path.name for path in output_dir.iterdir()}
    index_content = (output_dir / "intake-bundle-index.md").read_text(encoding="utf-8")

    assert result.stdout == f"wrote intake bundle with {len(expected_files)} artifacts to {output_dir}\n"
    assert expected_files <= written_files
    assert "Generated fixtures and packets are not P0 evidence" in index_content
    assert "manual-evidence-runbook.md" in index_content
    assert "release-owner-packet.md" in index_content
    template_payload = json.loads((output_dir / "noisy-preview-tuning-beta-response.json").read_text(encoding="utf-8"))
    assert template_payload["private_data_included"] is False


def test_evidence_session_manifest_template_validates_without_writing_records(tmp_path: Path) -> None:
    host_records, _ = _write_empty_records(tmp_path)
    output_dir = tmp_path / "session"

    template_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "session-manifest",
            "--host",
            "Codex",
            "--date",
            "2026-07-01",
            "--reviewer",
            "Release operator",
            "--output-dir",
            str(output_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    manifest_path = output_dir / "codex-evidence-session-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "status": "passed",
            "evidence": "Reviewer observed real Codex MCP host UI and first-10-minutes replay.",
            "artifacts": ["docs/assets/demo/demo_report.md"],
            "confirm_real_host_observed": True,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    validate_result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "validate-manifest",
            "--input",
            str(manifest_path),
            "--path",
            str(host_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(validate_result.stdout)

    assert template_result.stdout == f"wrote evidence session-manifest for Codex to {manifest_path}\n"
    assert manifest["manifest_status"] == "template"
    assert "run_host_smoke_check" in manifest["commands_used"]
    assert any("albu-mcp evidence validate-manifest" in command for command in manifest["commands_used"])
    assert payload["validation_status"] == "ready_to_import"
    assert payload["writes_records"] is False
    assert payload["artifact_count"] == 1
    assert host_records.read_text(encoding="utf-8") == '{"manual_host_ui": [], "first_10_minutes_replay": []}\n'
