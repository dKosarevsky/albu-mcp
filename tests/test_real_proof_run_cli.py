from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_activation_real_proof_run_reports_three_no_write_points(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "real-proof-run",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--release-tag",
            "v1.15.0-rc.1",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["run_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["release_tag"] == "v1.15.0-rc.1"
    assert payload["point_count"] == 3
    assert [point["id"] for point in payload["points"]] == [
        "real_host_proof_run",
        "beta_acquisition_loop",
        "p1_host_onboarding_gate",
    ]
    assert payload["points"][0]["status"] == "blocked_until_real_host_evidence"
    assert payload["points"][1]["status"] == "blocked_until_beta_validation"
    assert payload["points"][2]["implementation_allowed"] is False
    assert payload["next_action"] == "run_real_host_handoff"
    assert "Generated real-proof-run files do not count as evidence" in payload["non_fabrication_policy"]
    assert host_records.read_text(encoding="utf-8") == '{"manual_host_ui": [], "first_10_minutes_replay": []}\n'
    assert beta_records.read_text(encoding="utf-8") == '{"records": []}\n'


def test_activation_real_proof_run_writes_operator_artifacts(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    output_dir = tmp_path / "real-proof-run-1"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "real-proof-run",
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
        "real-proof-run-1-index.md",
        "real-host-proof-run.md",
        "beta-acquisition-loop.md",
        "p1-host-onboarding-gate.md",
    }
    index = (output_dir / "real-proof-run-1-index.md").read_text(encoding="utf-8")
    real_host = (output_dir / "real-host-proof-run.md").read_text(encoding="utf-8")
    beta = (output_dir / "beta-acquisition-loop.md").read_text(encoding="utf-8")
    p1_gate = (output_dir / "p1-host-onboarding-gate.md").read_text(encoding="utf-8")

    assert result.stdout == f"wrote activation real-proof-run with {len(expected_files)} artifacts to {output_dir}\n"
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "# Real Proof Run 1" in index
    assert "Writes records: `false`" in index
    assert "albu-mcp activation execution-workspace" in real_host
    assert "albu-mcp evidence session-folder" in real_host
    assert "albu-mcp evidence import-manifest" in real_host
    assert "https://albumentations.ai/docs/integrations/mcp/" in beta
    assert "albu-mcp beta response-import-dir" in beta
    assert "Implementation allowed: `false`" in p1_gate
    assert "external gates" in p1_gate
