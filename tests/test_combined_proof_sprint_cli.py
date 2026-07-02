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


def test_activation_proof_sprint_writes_markdown_artifact_folder(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    output_dir = tmp_path / "proof-sprint"
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
        "combined-proof-sprint-index.md",
        "real-host-evidence-sprint.md",
        "beta-validation-sprint.md",
        "host-onboarding-depth-sprint.md",
    }
    index = (output_dir / "combined-proof-sprint-index.md").read_text(encoding="utf-8")
    beta = (output_dir / "beta-validation-sprint.md").read_text(encoding="utf-8")
    host_onboarding = (output_dir / "host-onboarding-depth-sprint.md").read_text(encoding="utf-8")

    assert result.stdout == f"wrote activation proof-sprint with {len(expected_files)} artifacts to {output_dir}\n"
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "# Combined Proof Sprint" in index
    assert "Writes records: `false`" in index
    assert "https://albumentations.ai/docs/integrations/mcp/" in beta
    assert "albu-mcp beta loop-pack" in beta
    assert "Implementation allowed: `false`" in host_onboarding
    assert "albu-mcp host setup-probe" in host_onboarding
