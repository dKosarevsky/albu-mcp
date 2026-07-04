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


def test_activation_evidence_product_loop_reports_no_write_friction_summary(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "evidence-product-loop",
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

    assert payload["loop_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["host"] == "Codex"
    assert payload["section_count"] == 3
    assert [section["id"] for section in payload["sections"]] == [
        "real_host_evidence",
        "beta_validation",
        "product_backlog",
    ]
    assert payload["sections"][0]["status"] == "blocked_until_real_host_evidence"
    assert payload["sections"][0]["blocked_reasons"] == ["p0_host_evidence_missing_or_blocked"]
    assert payload["sections"][1]["status"] == "blocked_until_beta_validation"
    assert payload["sections"][1]["blocked_reasons"] == ["beta_validation_records_missing"]
    assert payload["sections"][2]["implementation_allowed"] is False
    assert payload["sections"][2]["blocked_reasons"] == [
        "p0_host_evidence_missing_or_blocked",
        "beta_validation_records_missing",
    ]
    assert "albu-mcp activation evidence-cockpit" in payload["sections"][0]["next_commands"][0]
    assert any(command.startswith("albu-mcp beta loop-pack") for command in payload["sections"][1]["next_commands"])
    assert payload["next_action"] == "collect_real_host_and_beta_evidence"
    assert "No generated packet" in payload["non_fabrication_policy"]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
