from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_empty_host_records(path: Path) -> None:
    path.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")


def _write_filled_manifest(path: Path, *, host: str = "Codex") -> None:
    payload = {
        "manifest_status": "filled",
        "host": host,
        "status": "passed",
        "date": "2026-07-02",
        "reviewer": "Release operator",
        "evidence": f"Reviewer observed real {host} MCP host UI and first-10-minutes replay.",
        "artifacts": ["docs/assets/demo/demo_report.md"],
        "commands_used": ["run_host_smoke_check", "render_preview_batch"],
        "confirm_real_host_observed": True,
        "private_data_included": False,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_evidence_import_manifest_imports_validated_manifest_into_both_p0_gates(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    manifest_path = tmp_path / "codex-evidence-session-manifest.json"
    _write_empty_host_records(host_records)
    _write_filled_manifest(manifest_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "import-manifest",
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
    payload = json.loads(result.stdout)
    records = json.loads(host_records.read_text(encoding="utf-8"))

    assert payload["import_status"] == "imported"
    assert payload["writes_records"] is True
    assert payload["validation_status"] == "ready_to_import"
    assert payload["required_gate_writes"] == ["manual_host_ui", "first_10_minutes_replay"]
    assert records["manual_host_ui"][0]["host"] == "Codex"
    assert records["manual_host_ui"][0]["status"] == "passed"
    assert records["first_10_minutes_replay"][0]["artifacts"] == ["docs/assets/demo/demo_report.md"]
