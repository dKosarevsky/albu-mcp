from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_beta_report_summarizes_records_triage_and_privacy(tmp_path: Path) -> None:
    records_path = tmp_path / "BETA_VALIDATION_RECORDS.json"
    subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "record-attempt",
            "--path",
            str(records_path),
            "--workflow-id",
            "noisy_preview_tuning",
            "--status",
            "needs_followup",
            "--attempt-date",
            "2026-06-29",
            "--participant-role",
            "ML practitioner",
            "--summary",
            "Noisy preview tuning found one candidate that made objects hard to recognize.",
            "--triage-bucket",
            "review_agent_v3_gap",
            "--artifact-ref",
            "docs/assets/demo/contact_sheet.png",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "report",
            "--path",
            str(records_path),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["report_status"] == "beta_signal_recorded"
    assert payload["privacy_status"] == "redacted"
    assert payload["summary"]["record_count"] == 1
    assert payload["summary"]["candidate_backlog_item_count"] == 1
    assert payload["product_depth_allowed"] is False
    assert payload["decisions"][0]["decision"] == "candidate_backlog_item"
    assert payload["decisions"][0]["triage_bucket"] == "review_agent_v3_gap"
    assert payload["next_actions"][0].startswith("Run remaining beta workflows")


def test_beta_report_text_output_is_concise(tmp_path: Path) -> None:
    records_path = tmp_path / "BETA_VALIDATION_RECORDS.json"
    records_path.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "report",
            "--path",
            str(records_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == "beta report blocked_until_beta_signal (records=0, candidate_backlog_items=0)\n"


def test_beta_campaign_plan_lists_privacy_safe_trials_and_recording_commands(tmp_path: Path) -> None:
    records_path = tmp_path / "BETA_VALIDATION_RECORDS.json"
    records_path.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "campaign-plan",
            "--path",
            str(records_path),
            "--target-participants",
            "5",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["campaign_status"] == "blocked_until_beta_signal"
    assert payload["target_participant_count"] == 5
    assert payload["privacy_policy"] == "redacted_only"
    assert payload["workflow_trial_count"] == 3
    assert [trial["workflow_id"] for trial in payload["workflow_trials"]] == [
        "dataset_health_before_training",
        "noisy_preview_tuning",
        "robustness_distortion_variants",
    ]
    assert payload["workflow_trials"][0]["recording_command"].startswith("albu-mcp beta record-attempt")
    assert payload["next_actions"][0] == "Recruit external CV users for every listed workflow trial."


def test_beta_trial_pack_provides_external_user_prompt_and_redaction_checklist(tmp_path: Path) -> None:
    records_path = tmp_path / "BETA_VALIDATION_RECORDS.json"
    records_path.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "trial-pack",
            "--path",
            str(records_path),
            "--workflow-id",
            "noisy_preview_tuning",
            "--participant-role",
            "CV engineer",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["pack_status"] == "ready_to_send"
    assert payload["workflow_id"] == "noisy_preview_tuning"
    assert payload["participant_role"] == "CV engineer"
    assert "example 8 is too noisy" in payload["participant_prompt"]
    assert payload["redaction_checklist"] == [
        "Remove private image paths and dataset names.",
        "Summarize visual findings without uploading private images.",
        "Link only safe generated artifacts or docs assets.",
        "Record private_data_included=false.",
    ]
    assert payload["expected_workflow"][0] == "Connect an MCP host with bounded --allowed-root and --artifact-root."
    assert payload["recording_command"].startswith("albu-mcp beta record-attempt")
    assert "--workflow-id noisy_preview_tuning" in payload["recording_command"]
