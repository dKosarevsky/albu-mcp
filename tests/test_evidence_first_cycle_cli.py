from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_activation_evidence_first_cycle_reports_five_no_write_tracks(tmp_path: Path) -> None:
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
            "evidence-first-cycle",
            "--host",
            "Codex",
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

    assert payload["cycle_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["release_tag"] == "v1.15.0-rc.1"
    assert payload["track_count"] == 5
    assert [track["id"] for track in payload["tracks"]] == [
        "evidence_first_result_pack",
        "beta_acquisition_loop",
        "gate_transition_release_readiness",
        "p1_host_onboarding_gate",
        "distribution_adoption_handoff",
    ]
    assert payload["next_action"] == "run_evidence_first_result_pack"
    assert payload["readiness_summary"] == {
        "gate_transition_status": "blocked_until_gate_transition",
        "p1_implementation_allowed": False,
        "publish_allowed": False,
        "release_readiness_command": "albu-mcp distribution readiness --format json",
    }
    assert payload["tracks"][2]["status"] == "blocked_until_gate_transition"
    assert "albu-mcp trust gate-transition" in payload["tracks"][2]["next_commands"][0]
    assert "albu-mcp rc go-check --format markdown" in payload["tracks"][2]["next_commands"]
    assert "albu-mcp distribution readiness --format json" in payload["tracks"][2]["next_commands"]
    assert payload["tracks"][4]["publish_allowed"] is False
    assert payload["tracks"][4]["status"] == "blocked_until_release_gates"
    assert "Generated evidence-first-cycle files do not count as evidence" in payload["non_fabrication_policy"]
    assert host_records.read_text(encoding="utf-8") == '{"manual_host_ui": [], "first_10_minutes_replay": []}\n'
    assert beta_records.read_text(encoding="utf-8") == '{"records": []}\n'


def test_activation_evidence_first_cycle_writes_five_handoff_artifacts(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    output_dir = tmp_path / "evidence-first-cycle"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "evidence-first-cycle",
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
        "evidence-first-cycle-index.md",
        "evidence-first-result-pack.md",
        "beta-acquisition-loop.md",
        "gate-transition-release-readiness.md",
        "p1-host-onboarding-gate.md",
        "distribution-adoption-handoff.md",
    }
    index = (output_dir / "evidence-first-cycle-index.md").read_text(encoding="utf-8")
    evidence = (output_dir / "evidence-first-result-pack.md").read_text(encoding="utf-8")
    beta = (output_dir / "beta-acquisition-loop.md").read_text(encoding="utf-8")
    gate = (output_dir / "gate-transition-release-readiness.md").read_text(encoding="utf-8")
    p1_gate = (output_dir / "p1-host-onboarding-gate.md").read_text(encoding="utf-8")
    adoption = (output_dir / "distribution-adoption-handoff.md").read_text(encoding="utf-8")

    assert (
        result.stdout == f"wrote activation evidence-first-cycle with {len(expected_files)} artifacts to {output_dir}\n"
    )
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "# Evidence First Cycle" in index
    assert "Writes records: `false`" in index
    assert "albu-mcp evidence validate-manifest" in evidence
    assert "albu-mcp evidence import-manifest" in evidence
    assert "albu-mcp evidence close-host" in evidence
    assert "https://albumentations.ai/docs/integrations/mcp/" in beta
    assert "albu-mcp beta response-import-dir" in beta
    assert "albu-mcp trust gate-transition" in gate
    assert "albu-mcp rc go-check" in gate
    assert "albu-mcp distribution readiness" in gate
    assert "Implementation allowed: `false`" in p1_gate
    assert "external gates" in p1_gate
    assert "MCP Registry" in adoption
    assert "PyPI" in adoption
    assert "upstream Albumentations docs" in adoption
