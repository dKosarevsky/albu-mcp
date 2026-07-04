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


def test_activation_real_adoption_cycle_writes_operator_artifacts(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    output_dir = tmp_path / "real-adoption-cycle"

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
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    expected_files = {
        "real-adoption-cycle-index.md",
        "real-evidence-intake.md",
        "beta-signal-sprint.md",
        "first-product-fix-gate.md",
    }
    index = (output_dir / "real-adoption-cycle-index.md").read_text(encoding="utf-8")
    real_evidence = (output_dir / "real-evidence-intake.md").read_text(encoding="utf-8")
    beta_signal = (output_dir / "beta-signal-sprint.md").read_text(encoding="utf-8")
    product_fix = (output_dir / "first-product-fix-gate.md").read_text(encoding="utf-8")

    assert (
        result.stdout == f"wrote activation real-adoption-cycle with {len(expected_files)} artifacts to {output_dir}\n"
    )
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "# Real Adoption Cycle" in index
    assert "Writes records: `false`" in index
    assert "albu-mcp evidence import-manifest" in real_evidence
    assert "albu-mcp beta loop-pack" in beta_signal
    assert "blocked_until_external_evidence" in product_fix
