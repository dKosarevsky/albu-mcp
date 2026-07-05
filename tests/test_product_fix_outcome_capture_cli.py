from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_product_fix_implementation_plan_cli import _write_empty_records, _write_ready_records


def test_activation_product_fix_outcome_capture_blocks_without_validated_fix(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome-capture",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--attempt-date",
            "2026-07-06",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["capture_status"] == "blocked_until_product_fix_validation"
    assert payload["outcome_status"] == "blocked_until_product_fix_validation"
    assert payload["writes_records"] is False
    assert payload["post_fix_beta_response"] is None
    assert payload["reviewer_checklist"] == []
    assert "p0_host_evidence_missing_or_blocked" in payload["blocked_reasons"]
    assert "albu-mcp activation product-fix-validation --host Codex --format json" in payload["next_commands"]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_activation_product_fix_outcome_capture_builds_post_fix_template(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome-capture",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--participant-role",
            "CV engineer",
            "--attempt-date",
            "2026-07-06",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    response = payload["post_fix_beta_response"]

    assert payload["capture_status"] == "ready_to_capture"
    assert payload["outcome_status"] == "needs_more_evidence"
    assert payload["writes_records"] is False
    assert payload["selected_fix"]["triage_bucket"] == "review_agent_v3_gap"
    assert response["workflow_id"] == "noisy_preview_tuning"
    assert response["status"] == "needs_followup"
    assert response["attempt_date"] == "2026-07-06"
    assert response["participant_role"] == "CV engineer"
    assert response["triage_bucket"] == "review_agent_v3_gap"
    assert response["private_data_included"] is False
    assert "Post-fix review_agent_v3_gap outcome" in response["summary"]
    assert payload["allowed_statuses"] == ["passed", "blocked", "needs_followup"]
    assert payload["privacy_policy"] == "redacted_only"
    assert "Set status to passed only after the post-fix retry is reviewer-observed." in payload["reviewer_checklist"]
    assert "albu-mcp beta response-validate --input" in payload["validation_commands"][0]
    assert "albu-mcp beta response-import --input" in payload["import_commands"][0]

    markdown_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome-capture",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--attempt-date",
            "2026-07-06",
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Capture status: `ready_to_capture`" in markdown_result.stdout
    assert "Post-fix beta response: `post-fix-noisy-preview-tuning-beta-response.json`" in markdown_result.stdout


def test_activation_product_fix_outcome_capture_writes_markdown_pack(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    output_dir = tmp_path / "product-fix-outcome-capture"
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome-capture",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--attempt-date",
            "2026-07-06",
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
        "capture-checklist.md",
        "capture-commands.md",
        "post-fix-noisy-preview-tuning-beta-response.json",
        "product-fix-outcome-capture-index.md",
    }
    index = (output_dir / "product-fix-outcome-capture-index.md").read_text(encoding="utf-8")
    template = json.loads((output_dir / "post-fix-noisy-preview-tuning-beta-response.json").read_text())
    checklist = (output_dir / "capture-checklist.md").read_text(encoding="utf-8")
    commands = (output_dir / "capture-commands.md").read_text(encoding="utf-8")

    assert (
        result.stdout
        == f"wrote activation product-fix-outcome-capture with {len(expected_files)} artifacts to {output_dir}\n"
    )
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "Capture status: `ready_to_capture`" in index
    assert template["workflow_id"] == "noisy_preview_tuning"
    assert template["private_data_included"] is False
    assert "reviewer-observed" in checklist
    assert "response-validate" in commands
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
