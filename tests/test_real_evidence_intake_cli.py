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


def _write_ready_records(tmp_path: Path) -> tuple[Path, Path]:
    host_records = tmp_path / "READY_HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "READY_BETA_VALIDATION_RECORDS.json"
    host_records.write_text(
        json.dumps(
            {
                "manual_host_ui": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-07-01",
                        "evidence": "Reviewer observed real Codex MCP host UI.",
                    },
                    {
                        "host": "Claude Code",
                        "status": "passed",
                        "date": "2026-07-01",
                        "evidence": "Reviewer observed real Claude Code MCP host UI.",
                    },
                ],
                "first_10_minutes_replay": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-07-01",
                        "evidence": "Reviewer observed real Codex first-10-minutes replay.",
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    },
                    {
                        "host": "Claude Code",
                        "status": "passed",
                        "date": "2026-07-01",
                        "evidence": "Reviewer observed real Claude Code first-10-minutes replay.",
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    },
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    beta_records.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "workflow_id": "dataset_health_before_training",
                        "status": "needs_followup",
                        "attempt_date": "2026-07-01",
                        "participant_role": "ML practitioner",
                        "summary": "redacted dataset health workflow completed without private paths",
                        "triage_bucket": "dataset_quality_gap",
                        "artifact_refs": ["docs/assets/demo/demo_report.md"],
                        "private_data_included": False,
                    },
                    {
                        "workflow_id": "noisy_preview_tuning",
                        "status": "needs_followup",
                        "attempt_date": "2026-07-01",
                        "participant_role": "ML practitioner",
                        "summary": "redacted noisy preview tuning workflow completed without private paths",
                        "triage_bucket": "review_agent_v3_gap",
                        "artifact_refs": ["docs/assets/demo/demo_report.md"],
                        "private_data_included": False,
                    },
                    {
                        "workflow_id": "robustness_distortion_variants",
                        "status": "needs_followup",
                        "attempt_date": "2026-07-01",
                        "participant_role": "ML practitioner",
                        "summary": "redacted robustness workflow completed without private paths",
                        "triage_bucket": "workflow_fit_gap",
                        "artifact_refs": ["docs/assets/demo/demo_report.md"],
                        "private_data_included": False,
                    },
                ]
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
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


def test_trust_gate_transition_reports_closed_gates(tmp_path: Path) -> None:
    before_host_records, before_beta_records = _write_empty_records(tmp_path)
    after_host_records, after_beta_records = _write_ready_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "trust",
            "gate-transition",
            "--before-host-records",
            str(before_host_records),
            "--before-beta-records",
            str(before_beta_records),
            "--after-host-records",
            str(after_host_records),
            "--after-beta-records",
            str(after_beta_records),
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
    closed_gates = {transition["gate"] for transition in payload["gate_transitions"] if transition["closed_gate"]}

    assert payload["transition_status"] == "ready_for_rc_reopen"
    assert payload["before"]["dashboard_status"] == "action_required"
    assert payload["after"]["dashboard_status"] == "ready"
    assert payload["before_trust_score"] == 0
    assert payload["after_trust_score"] == 100
    assert closed_gates == {"p0_host_evidence", "beta_validation", "distribution"}
    assert payload["rc_progress_status"] == "ready_for_release_owner_review"


def test_rc_release_owner_packet_blocks_publish_commands_until_go(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "rc",
            "release-owner-packet",
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

    assert payload["packet_status"] == "blocked"
    assert payload["publish_allowed"] is False
    assert payload["allowed_publish_commands"] == []
    assert "git tag v1.15.0-rc.1" in payload["do_not_run_commands"]
    assert "trust_gate_transition_report" in payload["required_attachments"]
    assert "release_owner_checklist" in payload
    assert "albu-mcp activation runbook --format markdown" in payload["manual_commands"]
    assert payload["execution_policy"].startswith("Report only")
