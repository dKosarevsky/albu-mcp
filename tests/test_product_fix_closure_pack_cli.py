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


def _import_post_fix_response(*, draft_path: Path, beta_records: Path) -> None:
    subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "response-import",
            "--input",
            str(draft_path),
            "--path",
            str(beta_records),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_activation_product_fix_closure_pack_closes_accepted_after_import(tmp_path: Path) -> None:
    host_records, before_beta_records = _write_ready_records(tmp_path)
    after_beta_records = _copy_beta_records(before_beta_records)
    draft_path = _write_post_fix_draft(tmp_path)
    _import_post_fix_response(draft_path=draft_path, beta_records=after_beta_records)
    host_before = host_records.read_text(encoding="utf-8")
    before_beta_before = before_beta_records.read_text(encoding="utf-8")
    after_beta_before = after_beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-pack",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--before-beta-records",
            str(before_beta_records),
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

    assert payload["closure_status"] == "closed_accepted"
    assert payload["writes_records"] is False
    assert payload["before_outcome_status"] == "needs_more_evidence"
    assert payload["after_outcome_status"] == "accepted"
    assert payload["selected_fix"]["product_area"] == "preview_review_agent"
    assert payload["selected_fix"]["triage_bucket"] == "review_agent_v3_gap"
    assert payload["evidence_diff"]["before_record_count"] == 1
    assert payload["evidence_diff"]["after_record_count"] == 2
    assert payload["evidence_diff"]["new_record_count"] == 1
    assert payload["evidence_diff"]["status_count_delta"]["passed"] == 1
    assert payload["evidence_diff"]["new_records"][0]["summary"].startswith("Post-fix retry kept example 8")
    assert payload["closure_summary"]["summary_status"] == "ready"
    assert payload["closure_summary"]["private_data_included"] is False
    assert "preview_review_agent" in payload["closure_summary"]["changelog_entry"]
    assert "Post-fix retry kept example 8" in payload["closure_summary"]["release_note"]
    assert payload["next_commands"] == [
        "albu-mcp activation evidence-product-loop --host Codex --format json",
        "albu-mcp activation product-fix-outcome --host Codex --format markdown",
    ]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert before_beta_records.read_text(encoding="utf-8") == before_beta_before
    assert after_beta_records.read_text(encoding="utf-8") == after_beta_before

    markdown_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-pack",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--before-beta-records",
            str(before_beta_records),
            "--beta-records",
            str(after_beta_records),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Closure status: `closed_accepted`" in markdown_result.stdout
    assert "After outcome: `accepted`" in markdown_result.stdout
    assert "New records: `1`" in markdown_result.stdout


def test_activation_product_fix_closure_pack_blocks_until_import(tmp_path: Path) -> None:
    host_records, before_beta_records = _write_ready_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-pack",
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

    assert payload["closure_status"] == "blocked_until_post_fix_outcome_import"
    assert payload["before_outcome_status"] == "needs_more_evidence"
    assert payload["after_outcome_status"] == "needs_more_evidence"
    assert payload["evidence_diff"]["new_record_count"] == 0
    assert "post_fix_outcome_not_closed" in payload["blocked_reasons"]
    assert "post_fix_import_record_missing" in payload["blocked_reasons"]
    assert "albu-mcp activation product-fix-outcome-capture --host Codex --format json" in payload["next_commands"]


def test_activation_product_fix_closure_pack_writes_markdown_artifacts(tmp_path: Path) -> None:
    host_records, before_beta_records = _write_ready_records(tmp_path)
    after_beta_records = _copy_beta_records(before_beta_records)
    draft_path = _write_post_fix_draft(tmp_path)
    _import_post_fix_response(draft_path=draft_path, beta_records=after_beta_records)
    output_dir = tmp_path / "product-fix-closure-pack"
    before_beta_before = before_beta_records.read_text(encoding="utf-8")
    after_beta_before = after_beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-closure-pack",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--before-beta-records",
            str(before_beta_records),
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
        "evidence-diff.md",
        "product-fix-closure-pack-index.md",
        "release-summary.md",
    }
    index = (output_dir / "product-fix-closure-pack-index.md").read_text(encoding="utf-8")
    diff = (output_dir / "evidence-diff.md").read_text(encoding="utf-8")
    summary = (output_dir / "release-summary.md").read_text(encoding="utf-8")

    assert result.stdout == f"wrote activation product-fix-closure-pack with 3 artifacts to {output_dir}\n"
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "Closure status: `closed_accepted`" in index
    assert "New records: `1`" in diff
    assert "preview_review_agent" in summary
    assert "Post-fix retry kept example 8" in summary
    assert before_beta_records.read_text(encoding="utf-8") == before_beta_before
    assert after_beta_records.read_text(encoding="utf-8") == after_beta_before
