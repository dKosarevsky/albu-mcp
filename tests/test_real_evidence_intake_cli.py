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


def test_activation_runbook_json_lists_manual_evidence_path(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "runbook",
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
    commands = [step["command"] for step in payload["operator_scenario"]]

    assert payload["runbook_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["release_tag"] == "v1.15.0-rc.1"
    assert "activation command-center" in commands[0]
    assert any("evidence packet-bundle" in command for command in commands)
    assert any("evidence import-checklist --host Codex" in command for command in commands)
    assert any("evidence validate-import" in command for command in commands)
    assert any("evidence import-artifacts" in command for command in commands)
    assert any("trust dashboard" in command for command in commands)
    assert any("rc candidate-packet" in command for command in commands)
    assert "demo fixture output is not P0 evidence" in payload["non_fabrication_policy"]
    assert payload["expected_outputs"][0]["status_when_blocked"] == "blocked"


def test_evidence_replay_fixture_pack_writes_non_evidence_markdown(tmp_path: Path) -> None:
    output_dir = tmp_path / "fixture-pack"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "replay-fixture-pack",
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    pack_path = output_dir / "real-host-replay-fixture-pack.md"
    content = pack_path.read_text(encoding="utf-8")

    assert result.stdout == f"wrote evidence replay-fixture-pack to {pack_path}\n"
    assert "# Real Host Replay Fixture Pack" in content
    assert "This fixture pack is not P0 evidence" in content
    assert "run_host_smoke_check" in content
    assert "render_preview_batch" in content
    assert "docs/assets/demo/demo_report.md" in content
    assert "expected_preview_flow" in content


def test_beta_response_template_writes_all_workflow_json_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "beta-templates"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "response-template",
            "--output-dir",
            str(output_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    expected_files = [
        "dataset-health-before-training-beta-response.json",
        "noisy-preview-tuning-beta-response.json",
        "robustness-distortion-variants-beta-response.json",
    ]

    assert result.stdout == f"wrote 3 beta response-template files to {output_dir}\n"
    for filename in expected_files:
        payload = json.loads((output_dir / filename).read_text(encoding="utf-8"))
        assert payload["private_data_included"] is False
        assert payload["status"] == "needs_followup"
        assert payload["participant_role"] == "ML practitioner"
        assert "redacted" in payload["summary"]
        assert payload["artifact_refs"] == ["docs/assets/demo/demo_report.md"]
