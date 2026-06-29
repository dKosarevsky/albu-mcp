from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_rc_reopen_holds_when_evidence_or_beta_is_missing(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "rc",
            "reopen",
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

    assert payload["rc_decision"] == "hold_rc"
    assert payload["publish_allowed"] is False
    assert payload["publish_commands"] == []
    assert payload["blocked_reasons"] == [
        "p0_host_evidence_missing_or_blocked",
        "beta_validation_incomplete",
    ]
    assert payload["next_action"].startswith("Do not tag or publish")


def test_rc_reopen_reports_ready_plan_without_executing_publish(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text(
        json.dumps(
            {
                "manual_host_ui": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-06-29",
                        "evidence": "Codex completed reviewer-observed host UI flow.",
                    },
                    {
                        "host": "Claude Code",
                        "status": "passed",
                        "date": "2026-06-29",
                        "evidence": "Claude Code completed reviewer-observed host UI flow.",
                    },
                ],
                "first_10_minutes_replay": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-06-29",
                        "evidence": "Codex completed first preview replay.",
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    },
                    {
                        "host": "Claude Code",
                        "status": "passed",
                        "date": "2026-06-29",
                        "evidence": "Claude Code completed first preview replay.",
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    beta_records.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "workflow_id": "dataset_health_before_training",
                        "status": "passed",
                        "attempt_date": "2026-06-29",
                        "participant_role": "Researcher",
                        "summary": "Dataset health workflow completed with redacted notes.",
                        "triage_bucket": "dataset_quality_gap",
                        "private_data_included": False,
                    },
                    {
                        "workflow_id": "noisy_preview_tuning",
                        "status": "needs_followup",
                        "attempt_date": "2026-06-29",
                        "participant_role": "ML practitioner",
                        "summary": "Noisy preview workflow produced feedback tags.",
                        "triage_bucket": "review_agent_v3_gap",
                        "private_data_included": False,
                    },
                    {
                        "workflow_id": "robustness_distortion_variants",
                        "status": "passed",
                        "attempt_date": "2026-06-29",
                        "participant_role": "CV engineer",
                        "summary": "Robustness workflow completed with contact sheet artifacts.",
                        "triage_bucket": "workflow_fit_gap",
                        "private_data_included": False,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "rc",
            "reopen",
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

    assert payload["rc_decision"] == "ready_for_rc_reopen"
    assert payload["publish_allowed"] is True
    assert payload["blocked_reasons"] == []
    assert payload["publish_commands"] == [
        "git tag v1.15.0-rc.1",
        "git push origin v1.15.0-rc.1",
        "gh release create v1.15.0-rc.1 --prerelease --generate-notes",
    ]
    assert payload["execution_policy"] == "Report only; this command does not create tags, releases, or uploads."
