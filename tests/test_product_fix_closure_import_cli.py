from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_product_fix_implementation_plan_cli import _write_ready_records
from tests.test_product_fix_outcome_import_guard_cli import _write_post_fix_draft


def test_activation_product_fix_closure_import_blocks_without_confirmation(tmp_path: Path) -> None:
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
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["import_status"] == "blocked_until_confirm_import_ready"
    assert payload["runbook_status"] == "ready_for_operator_import"
    assert payload["confirm_import_ready"] is False
    assert payload["runbook_import_allowed"] is True
    assert payload["writes_records"] is False
    assert payload["writes_snapshot"] is False
    assert payload["before_record_count"] == 3
    assert payload["after_record_count"] == 3
    assert payload["post_import_outcome_status"] is None
    assert payload["blocked_reasons"] == ["confirm_import_ready_missing"]
    assert "--confirm-import-ready" in payload["next_commands"][0]
    assert beta_records.read_text(encoding="utf-8") == beta_before
    assert not (snapshot_dir / "before-beta-validation-records.json").exists()


def test_activation_product_fix_closure_import_writes_snapshot_and_imports_when_confirmed(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    draft_path = _write_post_fix_draft(tmp_path)
    snapshot_dir = tmp_path / "product-fix-closure-snapshot"
    beta_before = json.loads(beta_records.read_text(encoding="utf-8"))

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
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
    payload = json.loads(result.stdout)
    beta_after = json.loads(beta_records.read_text(encoding="utf-8"))
    snapshot = json.loads((snapshot_dir / "before-beta-validation-records.json").read_text(encoding="utf-8"))

    assert payload["import_status"] == "imported"
    assert payload["runbook_status"] == "ready_for_operator_import"
    assert payload["confirm_import_ready"] is True
    assert payload["writes_records"] is True
    assert payload["writes_snapshot"] is True
    assert payload["before_record_count"] == 3
    assert payload["after_record_count"] == 4
    assert payload["post_import_outcome_status"] == "accepted"
    assert payload["imported_record"]["summary"].startswith("Post-fix retry kept example 8")
    assert snapshot == beta_before
    assert len(beta_after["records"]) == 4
    assert any(
        record["status"] == "passed" and record["summary"].startswith("Post-fix retry")
        for record in beta_after["records"]
    )
    assert any(
        command.startswith("albu-mcp activation product-fix-closure-pack") for command in payload["next_commands"]
    )

    markdown_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
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
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Import status: `blocked_until_runbook_ready`" in markdown_result.stdout
    assert "Runbook status: `blocked_until_capture_ready`" in markdown_result.stdout


def test_activation_product_fix_closure_import_blocks_placeholder_even_when_confirmed(tmp_path: Path) -> None:
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
    snapshot_dir = tmp_path / "product-fix-closure-snapshot"
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
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
    payload = json.loads(result.stdout)

    assert payload["import_status"] == "blocked_until_runbook_ready"
    assert payload["runbook_status"] == "blocked_until_post_fix_import_guard"
    assert payload["confirm_import_ready"] is True
    assert payload["runbook_import_allowed"] is False
    assert payload["writes_records"] is False
    assert payload["writes_snapshot"] is False
    assert "post_fix_import_guard_blocked" in payload["blocked_reasons"]
    assert "post_fix_summary_placeholder" in payload["blocked_reasons"]
    assert beta_records.read_text(encoding="utf-8") == beta_before
    assert not (snapshot_dir / "before-beta-validation-records.json").exists()
