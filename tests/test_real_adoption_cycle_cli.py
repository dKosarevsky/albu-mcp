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


def test_activation_real_adoption_cycle_reports_three_no_write_lanes(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "real-adoption-cycle",
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
    assert [lane["id"] for lane in payload["lanes"]] == [
        "real_evidence_intake",
        "beta_signal_sprint",
        "first_product_fix_gate",
    ]
    assert payload["lanes"][0]["status"] == "blocked_until_real_host_evidence"
    assert payload["lanes"][0]["blocked_reasons"] == ["p0_host_evidence_missing_or_blocked"]
    assert payload["lanes"][1]["status"] == "blocked_until_beta_signal"
    assert payload["lanes"][1]["blocked_reasons"] == ["beta_validation_records_missing"]
    assert payload["lanes"][2]["implementation_allowed"] is False
    assert payload["lanes"][2]["blocked_reasons"] == [
        "p0_host_evidence_missing_or_blocked",
        "beta_validation_records_missing",
    ]
    assert any(
        command.startswith("albu-mcp activation evidence-cockpit") for command in payload["lanes"][0]["next_commands"]
    )
    assert any(command.startswith("albu-mcp beta loop-pack") for command in payload["lanes"][1]["next_commands"])
    assert payload["next_action"] == "collect_real_evidence_and_beta_signal"
    assert "No generated packet" in payload["non_fabrication_policy"]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
