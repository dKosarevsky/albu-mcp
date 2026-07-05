from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_product_fix_implementation_plan_cli import _write_ready_records
from tests.test_product_fix_outcome_import_guard_cli import _write_post_fix_draft


def test_activation_product_fix_closure_snapshot_writes_before_snapshot_and_commands(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    draft_path = _write_post_fix_draft(tmp_path)
    output_dir = tmp_path / "product-fix-closure-snapshot"
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-snapshot",
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
        "before-beta-validation-records.json",
        "import-and-closure-commands.md",
        "product-fix-closure-snapshot-index.md",
    }
    snapshot = output_dir / "before-beta-validation-records.json"
    index = (output_dir / "product-fix-closure-snapshot-index.md").read_text(encoding="utf-8")
    commands = (output_dir / "import-and-closure-commands.md").read_text(encoding="utf-8")

    assert result.stdout == f"wrote activation product-fix-closure-snapshot with 3 artifacts to {output_dir}\n"
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert json.loads(snapshot.read_text(encoding="utf-8")) == json.loads(beta_before)
    assert "Snapshot status: `ready_for_import`" in index
    assert f"Snapshot path: `{snapshot}`" in index
    assert "Writes records: `false`" in index
    assert f"albu-mcp beta response-import --input {draft_path} --path {beta_records}" in commands
    assert (
        "albu-mcp activation product-fix-closure-pack --host Codex "
        f"--before-beta-records {snapshot} --beta-records {beta_records} "
        "--output-dir docs/product-fix-closure-pack --format markdown"
    ) in commands
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_activation_product_fix_closure_snapshot_reports_ready_json_contract(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    draft_path = _write_post_fix_draft(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-snapshot",
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
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["snapshot_status"] == "ready_for_import"
    assert payload["writes_records"] is False
    assert payload["writes_snapshot"] is True
    assert payload["import_allowed"] is True
    assert payload["snapshot_path"] == "docs/product-fix-closure-snapshot/before-beta-validation-records.json"
    assert payload["selected_fix"]["triage_bucket"] == "review_agent_v3_gap"
    assert payload["source_rehearsal"]["rehearsal_status"] == "ready_for_guarded_import"
    assert payload["next_commands"] == [
        f"albu-mcp beta response-import --input {draft_path} --path {beta_records}",
        (
            "albu-mcp activation product-fix-closure-pack --host Codex "
            "--before-beta-records docs/product-fix-closure-snapshot/before-beta-validation-records.json "
            f"--beta-records {beta_records} --output-dir docs/product-fix-closure-pack --format markdown"
        ),
    ]


def test_activation_product_fix_closure_snapshot_blocks_when_draft_guard_blocks(tmp_path: Path) -> None:
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
            "product-fix-closure-snapshot",
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

    assert payload["snapshot_status"] == "blocked_until_post_fix_import_guard"
    assert payload["writes_records"] is False
    assert payload["writes_snapshot"] is False
    assert payload["import_allowed"] is False
    assert payload["import_command"] is None
    assert payload["closure_command"] is None
    assert "post_fix_summary_placeholder" in payload["blocked_reasons"]
    assert "albu-mcp activation product-fix-outcome-capture --host Codex --format json" in payload["next_commands"]
