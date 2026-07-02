from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_activation_execution_workspace_reports_three_no_write_steps(tmp_path: Path) -> None:
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
            "execution-workspace",
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

    assert payload["workspace_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["release_tag"] == "v1.15.0-rc.1"
    assert payload["step_count"] == 3
    assert [step["id"] for step in payload["steps"]] == [
        "execution_workspace",
        "real_host_execution",
        "beta_execution",
    ]
    assert payload["steps"][0]["status"] == "ready_to_write_artifacts"
    assert payload["steps"][1]["status"] == "blocked_until_real_host_evidence"
    assert payload["steps"][2]["status"] == "blocked_until_beta_validation"
    assert payload["next_action"] == "run_workspace_artifacts"
    assert "Generated execution workspace files do not count as evidence" in payload["non_fabrication_policy"]
    assert host_records.read_text(encoding="utf-8") == '{"manual_host_ui": [], "first_10_minutes_replay": []}\n'
    assert beta_records.read_text(encoding="utf-8") == '{"records": []}\n'
