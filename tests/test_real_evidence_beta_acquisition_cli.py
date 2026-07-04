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


def test_activation_acquisition_cycle_reports_real_evidence_lane(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "acquisition-cycle",
            "--host",
            "Codex",
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

    assert payload["cycle_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["host"] == "Codex"
    assert payload["lane_count"] == 3
    assert payload["lanes"][0]["id"] == "real_evidence_acquisition"
    assert payload["lanes"][0]["status"] == "blocked_until_real_host_evidence"
    assert payload["lanes"][0]["writes_records"] is False
    assert "albu-mcp evidence transcript-template" in payload["lanes"][0]["next_commands"]
    assert "albu-mcp evidence proof-runner" in payload["lanes"][0]["next_commands"]
    assert "albu-mcp evidence import-manifest" in payload["lanes"][0]["next_commands"]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
