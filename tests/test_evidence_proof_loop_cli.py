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


def _write_filled_manifest(tmp_path: Path) -> Path:
    manifest = tmp_path / "codex-evidence-session-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_status": "filled",
                "host": "Codex",
                "status": "passed",
                "date": "2026-07-03",
                "reviewer": "Release operator",
                "evidence": "reviewer observed real MCP host UI and first preview replay",
                "artifacts": ["docs/assets/demo/demo_report.md"],
                "commands_used": ["albu-mcp host setup-probe --host Codex --live --format json"],
                "confirm_real_host_observed": True,
                "private_data_included": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def test_evidence_proof_runner_reports_no_write_import_flow(tmp_path: Path) -> None:
    host_records, _ = _write_empty_records(tmp_path)
    manifest = _write_filled_manifest(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "proof-runner",
            "--input",
            str(manifest),
            "--path",
            str(host_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["runner_status"] == "ready_to_import"
    assert payload["writes_records"] is False
    assert payload["host"] == "Codex"
    assert payload["manifest_validation"]["validation_status"] == "ready_to_import"
    assert payload["next_commands"] == [
        f"albu-mcp evidence validate-manifest --input {manifest} --path {host_records} --format json",
        f"albu-mcp evidence import-manifest --input {manifest} --path {host_records} --format json",
        f"albu-mcp evidence close-host --host Codex --path {host_records} --format json",
        (
            "albu-mcp trust gate-transition "
            f"--before-host-records {host_records} --before-beta-records docs/BETA_VALIDATION_RECORDS.json "
            f"--after-host-records {host_records} --after-beta-records docs/BETA_VALIDATION_RECORDS.json "
            "--format markdown"
        ),
    ]
    assert host_records.read_text(encoding="utf-8") == '{"manual_host_ui": [], "first_10_minutes_replay": []}\n'
