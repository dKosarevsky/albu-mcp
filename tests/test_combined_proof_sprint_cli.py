from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_activation_proof_sprint_reports_three_blocked_points_without_writing_records(tmp_path: Path) -> None:
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
            "proof-sprint",
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

    assert payload["sprint_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["release_tag"] == "v1.15.0-rc.1"
    assert payload["point_count"] == 3
    assert [point["id"] for point in payload["points"]] == [
        "real_host_evidence_sprint",
        "beta_validation_sprint",
        "host_onboarding_depth",
    ]
    assert payload["points"][0]["status"] == "blocked_until_real_host_evidence"
    assert "albu-mcp evidence session-folder" in payload["points"][0]["next_commands"]
    assert "albu-mcp evidence import-manifest" in payload["points"][0]["next_commands"]
    assert "albu-mcp evidence close-host" in payload["points"][0]["next_commands"]
    assert "https://albumentations.ai/docs/integrations/mcp/" in payload["points"][1]["source_links"]
    assert payload["points"][2]["implementation_allowed"] is False
    assert payload["next_action"] == "collect_real_host_and_beta_evidence"
    assert host_records.read_text(encoding="utf-8") == '{"manual_host_ui": [], "first_10_minutes_replay": []}\n'
    assert beta_records.read_text(encoding="utf-8") == '{"records": []}\n'
