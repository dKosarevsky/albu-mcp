from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_product_fix_implementation_plan_cli import _write_ready_records
from tests.test_product_fix_outcome_import_guard_cli import _write_post_fix_draft

_OPERATOR_SEQUENCE_IDS = [
    "capture_post_fix_response",
    "guard_post_fix_draft",
    "rehearse_import_and_outcome",
    "snapshot_before_import",
    "import_post_fix_response",
    "build_closure_pack",
    "confirm_final_outcome",
]


def test_activation_product_fix_closure_runbook_builds_ready_operator_sequence(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    draft_path = _write_post_fix_draft(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-runbook",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--input",
            str(draft_path),
            "--snapshot-dir",
            "docs/product-fix-closure-snapshot",
            "--closure-output-dir",
            "docs/product-fix-closure-pack",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["runbook_status"] == "ready_for_operator_import"
    assert payload["writes_records"] is False
    assert payload["import_allowed"] is True
    assert payload["capture_status"] == "ready_to_capture"
    assert payload["guard_status"] == "ready_to_import"
    assert payload["rehearsal_status"] == "ready_for_guarded_import"
    assert payload["snapshot_status"] == "ready_for_import"
    assert payload["current_outcome_status"] == "needs_more_evidence"
    assert payload["selected_fix"]["triage_bucket"] == "review_agent_v3_gap"
    assert payload["input_path"] == str(draft_path)
    assert payload["snapshot_path"] == "docs/product-fix-closure-snapshot/before-beta-validation-records.json"
    assert payload["stop_conditions"] == []
    assert [step["id"] for step in payload["operator_sequence"]] == _OPERATOR_SEQUENCE_IDS
    assert f"albu-mcp beta response-import --input {draft_path} --path {beta_records}" in payload["next_commands"]
    assert any(
        command.startswith("albu-mcp activation product-fix-closure-pack") for command in payload["next_commands"]
    )
    assert payload["source_capture"]["capture_status"] == "ready_to_capture"
    assert payload["source_import_guard"]["guard_status"] == "ready_to_import"
    assert payload["source_rehearsal"]["rehearsal_status"] == "ready_for_guarded_import"
    assert payload["source_snapshot"]["snapshot_status"] == "ready_for_import"
    assert payload["source_current_outcome"]["outcome_status"] == "needs_more_evidence"

    markdown_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-runbook",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--input",
            str(draft_path),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Runbook status: `ready_for_operator_import`" in markdown_result.stdout
    assert "Import allowed: `true`" in markdown_result.stdout
    assert "snapshot_before_import" in markdown_result.stdout
    assert "albu-mcp activation product-fix-closure-snapshot" in markdown_result.stdout
    assert "albu-mcp activation product-fix-closure-pack" in markdown_result.stdout


def test_activation_product_fix_closure_runbook_blocks_placeholder_draft(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    draft_path = _write_post_fix_draft(
        tmp_path,
        overrides={
            "summary": (
                "Post-fix review_agent_v3_gap outcome; replace with a redacted reviewer-observed summary "
                "of whether the fix resolved the workflow."
            )
        },
    )

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-runbook",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--input",
            str(draft_path),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["runbook_status"] == "blocked_until_post_fix_import_guard"
    assert payload["import_allowed"] is False
    assert payload["writes_records"] is False
    assert payload["guard_status"] == "blocked_until_post_fix_draft_ready"
    assert payload["snapshot_status"] == "blocked_until_post_fix_import_guard"
    assert "post_fix_import_guard_blocked" in payload["stop_conditions"]
    assert "post_fix_summary_placeholder" in payload["stop_conditions"]
    assert not any(command.startswith("albu-mcp beta response-import") for command in payload["next_commands"])


def test_activation_product_fix_closure_runbook_writes_markdown_artifacts(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    draft_path = _write_post_fix_draft(tmp_path)
    output_dir = tmp_path / "product-fix-closure-runbook"
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-runbook",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--input",
            str(draft_path),
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
        "operator-sequence.md",
        "product-fix-closure-runbook-index.md",
        "stop-conditions.md",
    }
    index = (output_dir / "product-fix-closure-runbook-index.md").read_text(encoding="utf-8")
    sequence = (output_dir / "operator-sequence.md").read_text(encoding="utf-8")
    stops = (output_dir / "stop-conditions.md").read_text(encoding="utf-8")

    assert result.stdout == f"wrote activation product-fix-closure-runbook with 3 artifacts to {output_dir}\n"
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "Runbook status: `ready_for_operator_import`" in index
    assert "Import allowed: `true`" in index
    assert "snapshot_before_import" in sequence
    assert "albu-mcp activation product-fix-closure-snapshot" in sequence
    assert "albu-mcp activation product-fix-closure-pack" in sequence
    assert "No active stop conditions." in stops
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
