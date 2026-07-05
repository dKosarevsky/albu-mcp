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
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text(
        json.dumps(
            {
                "manual_host_ui": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-07-05",
                        "evidence": (
                            "Reviewer observed real Codex MCP host UI, listed AlbumentationsX MCP tools, "
                            "ran run_host_smoke_check, and confirmed preview_ready=true."
                        ),
                    },
                    {
                        "host": "Claude Code",
                        "status": "passed",
                        "date": "2026-07-05",
                        "evidence": (
                            "Reviewer observed real Claude Code MCP host UI, listed AlbumentationsX MCP tools, "
                            "ran run_host_smoke_check, and confirmed preview_ready=true."
                        ),
                    },
                ],
                "first_10_minutes_replay": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-07-05",
                        "evidence": "Reviewer observed real Codex first-preview replay from install to comparison.",
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    },
                    {
                        "host": "Claude Code",
                        "status": "passed",
                        "date": "2026-07-05",
                        "evidence": (
                            "Reviewer observed real Claude Code first-preview replay from install to comparison."
                        ),
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    },
                ],
            }
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
                        "status": "passed",
                        "attempt_date": "2026-07-05",
                        "participant_role": "ML practitioner",
                        "summary": "Dataset health attempt found class imbalance before preview rendering.",
                        "triage_bucket": "dataset_quality_gap",
                        "artifact_refs": ["docs/assets/demo/demo_report.md"],
                        "private_data_included": False,
                    },
                    {
                        "workflow_id": "noisy_preview_tuning",
                        "status": "needs_followup",
                        "attempt_date": "2026-07-05",
                        "participant_role": "ML practitioner",
                        "summary": "Noisy preview feedback identified one candidate that should be softened.",
                        "triage_bucket": "review_agent_v3_gap",
                        "artifact_refs": ["docs/assets/demo/demo_report.md"],
                        "private_data_included": False,
                    },
                    {
                        "workflow_id": "robustness_distortion_variants",
                        "status": "passed",
                        "attempt_date": "2026-07-05",
                        "participant_role": "CV engineer",
                        "summary": "Robustness variants matched the participant goal after contact sheet review.",
                        "triage_bucket": "workflow_fit_gap",
                        "artifact_refs": ["docs/assets/demo/demo_report.md"],
                        "private_data_included": False,
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return host_records, beta_records


def test_activation_first_product_fix_blocks_without_external_evidence(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "first-product-fix",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["selector_status"] == "blocked_until_external_evidence"
    assert payload["writes_records"] is False
    assert payload["implementation_allowed"] is False
    assert payload["selected_fix"] is None
    assert payload["implementation_packet"] is None
    assert payload["blocked_reasons"] == [
        "p0_host_evidence_missing_or_blocked",
        "beta_validation_records_missing",
    ]
    assert "albu-mcp activation real-adoption-cycle --host Codex --format json" in payload["next_commands"]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_activation_first_product_fix_selects_ready_beta_fix(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "first-product-fix",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["selector_status"] == "ready_for_implementation"
    assert payload["writes_records"] is False
    assert payload["implementation_allowed"] is True
    assert payload["blocked_reasons"] == []
    assert payload["selected_fix"]["triage_bucket"] == "review_agent_v3_gap"
    assert payload["selected_fix"]["product_area"] == "preview_review_agent"
    assert payload["implementation_packet"]["product_area"] == "preview_review_agent"
    assert (
        payload["implementation_packet"]["success_signal"]
        == "Repeated noisy-preview feedback maps to safer candidate adjustments."
    )
    assert payload["implementation_packet"]["test_strategy"][0].startswith("Write failing tests")
    assert payload["source_decisions"][0]["decision"] == "ready_for_depth_plan"

    markdown_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "first-product-fix",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "preview_review_agent" in markdown_result.stdout
    assert "Repeated noisy-preview feedback maps to safer candidate adjustments." in markdown_result.stdout
