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
    assert "Generated evidence-first-cycle files do not count as evidence" in payload["non_fabrication_policy"]
    assert host_records.read_text(encoding="utf-8") == '{"manual_host_ui": [], "first_10_minutes_replay": []}\n'
    assert beta_records.read_text(encoding="utf-8") == '{"records": []}\n'
