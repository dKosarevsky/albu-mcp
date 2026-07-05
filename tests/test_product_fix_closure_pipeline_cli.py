from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_product_fix_closure_receipt_cli import _copy_beta_records, _guarded_import
from tests.test_product_fix_implementation_plan_cli import _write_ready_records
from tests.test_product_fix_outcome_import_guard_cli import _write_post_fix_draft


def test_activation_product_fix_closure_pipeline_reports_closed_after_guarded_import(tmp_path: Path) -> None:
    host_records, before_beta_records = _write_ready_records(tmp_path)
    after_beta_records = _copy_beta_records(before_beta_records)
    draft_path = _write_post_fix_draft(tmp_path)
    snapshot_dir = tmp_path / "product-fix-closure-snapshot"
    snapshot_path = _guarded_import(
        host_records=host_records,
        beta_records=after_beta_records,
        draft_path=draft_path,
        snapshot_dir=snapshot_dir,
    )
    snapshot_before = snapshot_path.read_text(encoding="utf-8")
    after_beta_before = after_beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-pipeline",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(after_beta_records),
            "--input",
            str(draft_path),
            "--snapshot-dir",
            str(snapshot_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["pipeline_status"] == "closed_accepted"
    assert payload["writes_records"] is False
    assert payload["writes_snapshot"] is False
    assert payload["snapshot_path"] == str(snapshot_path)
    assert payload["snapshot_file_present"] is True
    assert payload["import_status"] == "imported"
    assert payload["receipt_status"] == "ready"
    assert payload["closure_status"] == "closed_accepted"
    assert payload["final_outcome_status"] == "accepted"
    assert payload["new_record_count"] == 1
    assert payload["imported_record"]["summary"].startswith("Post-fix retry kept example 8")
    assert payload["blocked_reasons"] == []
    assert [step["step_id"] for step in payload["steps"]] == [
        "snapshot_file",
        "operator_runbook",
        "guarded_import",
        "closure_receipt",
        "closure_pack",
        "final_outcome",
    ]
    assert all(step["status"] == "passed" for step in payload["steps"])
    assert "product-fix-closure-receipt" in payload["commands"]["receipt"]
    assert snapshot_path.read_text(encoding="utf-8") == snapshot_before
    assert after_beta_records.read_text(encoding="utf-8") == after_beta_before

    markdown_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-pipeline",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(after_beta_records),
            "--input",
            str(draft_path),
            "--snapshot-dir",
            str(snapshot_dir),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Pipeline status: `closed_accepted`" in markdown_result.stdout
    assert "Receipt status: `ready`" in markdown_result.stdout
    assert "Final outcome: `accepted`" in markdown_result.stdout
    assert "Writes records: `false`" in markdown_result.stdout
    assert "Post-fix retry kept example 8" in markdown_result.stdout


def test_activation_product_fix_closure_pipeline_blocks_until_snapshot_file(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    draft_path = _write_post_fix_draft(tmp_path)
    snapshot_dir = tmp_path / "product-fix-closure-snapshot"
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-pipeline",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--input",
            str(draft_path),
            "--snapshot-dir",
            str(snapshot_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["pipeline_status"] == "ready_for_snapshot"
    assert payload["writes_records"] is False
    assert payload["writes_snapshot"] is False
    assert payload["snapshot_file_present"] is False
    assert payload["import_status"] == "blocked_until_snapshot_file"
    assert payload["receipt_status"] is None
    assert payload["closure_status"] is None
    assert payload["final_outcome_status"] == "needs_more_evidence"
    assert payload["new_record_count"] == 0
    assert payload["imported_record"] is None
    assert "snapshot_file_missing" in payload["blocked_reasons"]
    assert payload["steps"][0] == {
        "step_id": "snapshot_file",
        "status": "operator_action_required",
        "summary": "Write the pre-import beta records snapshot before importing post-fix evidence.",
    }
    assert payload["next_commands"][0].startswith("albu-mcp activation product-fix-closure-snapshot")
    assert beta_records.read_text(encoding="utf-8") == beta_before
    assert not snapshot_dir.exists()


def test_activation_product_fix_closure_pipeline_writes_markdown_artifacts(tmp_path: Path) -> None:
    host_records, before_beta_records = _write_ready_records(tmp_path)
    after_beta_records = _copy_beta_records(before_beta_records)
    draft_path = _write_post_fix_draft(tmp_path)
    snapshot_dir = tmp_path / "product-fix-closure-snapshot"
    snapshot_path = _guarded_import(
        host_records=host_records,
        beta_records=after_beta_records,
        draft_path=draft_path,
        snapshot_dir=snapshot_dir,
    )
    output_dir = tmp_path / "product-fix-closure-pipeline"
    snapshot_before = snapshot_path.read_text(encoding="utf-8")
    after_beta_before = after_beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-pipeline",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(after_beta_records),
            "--input",
            str(draft_path),
            "--snapshot-dir",
            str(snapshot_dir),
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
        "closure-pipeline-commands.md",
        "closure-pipeline-steps.md",
        "product-fix-closure-pipeline-index.md",
    }
    index = (output_dir / "product-fix-closure-pipeline-index.md").read_text(encoding="utf-8")
    steps = (output_dir / "closure-pipeline-steps.md").read_text(encoding="utf-8")
    commands = (output_dir / "closure-pipeline-commands.md").read_text(encoding="utf-8")

    assert result.stdout == f"wrote activation product-fix-closure-pipeline with 3 artifacts to {output_dir}\n"
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "Pipeline status: `closed_accepted`" in index
    assert "Writes records: `false`" in index
    assert "closure_receipt" in steps
    assert "product-fix-closure-receipt" in commands
    assert "product-fix-closure-pack" in commands
    assert snapshot_path.read_text(encoding="utf-8") == snapshot_before
    assert after_beta_records.read_text(encoding="utf-8") == after_beta_before
