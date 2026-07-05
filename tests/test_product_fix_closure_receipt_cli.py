from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_product_fix_implementation_plan_cli import _write_ready_records
from tests.test_product_fix_outcome_import_guard_cli import _write_post_fix_draft


def _copy_beta_records(before_beta_records: Path) -> Path:
    after_beta_records = before_beta_records.with_name("AFTER_BETA_VALIDATION_RECORDS.json")
    after_beta_records.write_text(before_beta_records.read_text(encoding="utf-8"), encoding="utf-8")
    return after_beta_records


def _guarded_import(*, host_records: Path, beta_records: Path, draft_path: Path, snapshot_dir: Path) -> Path:
    subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-import",
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
            "--confirm-import-ready",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return snapshot_dir / "before-beta-validation-records.json"


def test_activation_product_fix_closure_receipt_reports_ready_after_guarded_import(tmp_path: Path) -> None:
    host_records, before_beta_records = _write_ready_records(tmp_path)
    after_beta_records = _copy_beta_records(before_beta_records)
    draft_path = _write_post_fix_draft(tmp_path)
    snapshot_path = _guarded_import(
        host_records=host_records,
        beta_records=after_beta_records,
        draft_path=draft_path,
        snapshot_dir=tmp_path / "product-fix-closure-snapshot",
    )
    before_beta_before = snapshot_path.read_text(encoding="utf-8")
    after_beta_before = after_beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-receipt",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--before-beta-records",
            str(snapshot_path),
            "--beta-records",
            str(after_beta_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["receipt_status"] == "ready"
    assert payload["writes_records"] is False
    assert payload["writes_snapshot"] is False
    assert payload["snapshot_path"] == str(snapshot_path)
    assert payload["before_record_count"] == 3
    assert payload["after_record_count"] == 4
    assert payload["new_record_count"] == 1
    assert payload["imported_record"]["summary"].startswith("Post-fix retry kept example 8")
    assert payload["closure_status"] == "closed_accepted"
    assert payload["before_outcome_status"] == "needs_more_evidence"
    assert payload["after_outcome_status"] == "accepted"
    assert payload["selected_fix"]["triage_bucket"] == "review_agent_v3_gap"
    assert payload["blocked_reasons"] == []
    assert "product-fix-closure-pack" in payload["closure_command"]
    assert "product-fix-outcome" in payload["final_outcome_command"]
    assert payload["next_commands"] == [payload["closure_command"], payload["final_outcome_command"]]
    assert snapshot_path.read_text(encoding="utf-8") == before_beta_before
    assert after_beta_records.read_text(encoding="utf-8") == after_beta_before

    markdown_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-receipt",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--before-beta-records",
            str(snapshot_path),
            "--beta-records",
            str(after_beta_records),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Receipt status: `ready`" in markdown_result.stdout
    assert "Writes records: `false`" in markdown_result.stdout
    assert "Imported record: `present`" in markdown_result.stdout
    assert "New records: `1`" in markdown_result.stdout
    assert "Post-fix retry kept example 8" in markdown_result.stdout


def test_activation_product_fix_closure_receipt_blocks_without_import(tmp_path: Path) -> None:
    host_records, before_beta_records = _write_ready_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-receipt",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--before-beta-records",
            str(before_beta_records),
            "--beta-records",
            str(before_beta_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["receipt_status"] == "blocked_until_post_fix_outcome_import"
    assert payload["writes_records"] is False
    assert payload["writes_snapshot"] is False
    assert payload["before_record_count"] == 3
    assert payload["after_record_count"] == 3
    assert payload["new_record_count"] == 0
    assert payload["imported_record"] is None
    assert "post_fix_outcome_not_closed" in payload["blocked_reasons"]
    assert "post_fix_import_record_missing" in payload["blocked_reasons"]


def test_activation_product_fix_closure_receipt_writes_markdown_artifacts(tmp_path: Path) -> None:
    host_records, before_beta_records = _write_ready_records(tmp_path)
    after_beta_records = _copy_beta_records(before_beta_records)
    draft_path = _write_post_fix_draft(tmp_path)
    snapshot_path = _guarded_import(
        host_records=host_records,
        beta_records=after_beta_records,
        draft_path=draft_path,
        snapshot_dir=tmp_path / "product-fix-closure-snapshot",
    )
    output_dir = tmp_path / "product-fix-closure-receipt"
    before_beta_before = snapshot_path.read_text(encoding="utf-8")
    after_beta_before = after_beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-receipt",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--before-beta-records",
            str(snapshot_path),
            "--beta-records",
            str(after_beta_records),
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
        "follow-up-commands.md",
        "imported-record.md",
        "product-fix-closure-receipt-index.md",
    }
    index = (output_dir / "product-fix-closure-receipt-index.md").read_text(encoding="utf-8")
    imported_record = (output_dir / "imported-record.md").read_text(encoding="utf-8")
    commands = (output_dir / "follow-up-commands.md").read_text(encoding="utf-8")

    assert result.stdout == f"wrote activation product-fix-closure-receipt with 3 artifacts to {output_dir}\n"
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "Receipt status: `ready`" in index
    assert "Writes records: `false`" in index
    assert "Post-fix retry kept example 8" in imported_record
    assert "product-fix-closure-pack" in commands
    assert "product-fix-outcome" in commands
    assert snapshot_path.read_text(encoding="utf-8") == before_beta_before
    assert after_beta_records.read_text(encoding="utf-8") == after_beta_before
