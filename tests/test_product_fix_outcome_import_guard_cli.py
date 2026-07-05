from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_product_fix_implementation_plan_cli import _write_empty_records, _write_ready_records


def _write_post_fix_draft(
    tmp_path: Path,
    *,
    overrides: dict[str, object] | None = None,
) -> Path:
    draft_path = tmp_path / "post-fix-noisy-preview-tuning-beta-response.json"
    payload: dict[str, object] = {
        "workflow_id": "noisy_preview_tuning",
        "status": "passed",
        "attempt_date": "2026-07-06",
        "participant_role": "CV engineer",
        "summary": "Post-fix retry kept example 8 recognizable while preserving useful variation.",
        "triage_bucket": "review_agent_v3_gap",
        "artifact_refs": ["docs/assets/demo/demo_report.md"],
        "private_data_included": False,
    }
    if overrides is not None:
        payload.update(overrides)
    draft_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return draft_path


def test_activation_product_fix_outcome_import_guard_blocks_without_validated_fix(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    draft_path = _write_post_fix_draft(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome-import-guard",
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

    assert payload["guard_status"] == "blocked_until_product_fix_validation"
    assert payload["outcome_status"] == "blocked_until_product_fix_validation"
    assert payload["writes_records"] is False
    assert payload["import_allowed"] is False
    assert payload["draft"] is None
    assert payload["draft_checks"] == []
    assert "p0_host_evidence_missing_or_blocked" in payload["blocked_reasons"]
    assert "albu-mcp activation product-fix-validation --host Codex --format json" in payload["next_commands"]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_activation_product_fix_outcome_import_guard_allows_matching_post_fix_draft(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    draft_path = _write_post_fix_draft(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome-import-guard",
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

    assert payload["guard_status"] == "ready_to_import"
    assert payload["outcome_status"] == "needs_more_evidence"
    assert payload["writes_records"] is False
    assert payload["import_allowed"] is True
    assert payload["draft"]["workflow_id"] == "noisy_preview_tuning"
    assert payload["draft"]["triage_bucket"] == "review_agent_v3_gap"
    assert payload["selected_fix"]["triage_bucket"] == "review_agent_v3_gap"
    assert [check["id"] for check in payload["draft_checks"]] == [
        "workflow_matches_selected_fix",
        "triage_bucket_matches_selected_fix",
        "summary_replaced",
        "artifact_refs_present",
        "privacy_redacted",
    ]
    assert all(check["status"] == "passed" for check in payload["draft_checks"])
    assert payload["blocked_reasons"] == []
    assert payload["import_command"] == f"albu-mcp beta response-import --input {draft_path} --path {beta_records}"
    assert payload["next_commands"] == [
        f"albu-mcp beta response-import --input {draft_path} --path {beta_records}",
        "albu-mcp activation product-fix-outcome --host Codex --format json",
    ]

    markdown_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome-import-guard",
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

    assert "Guard status: `ready_to_import`" in markdown_result.stdout
    assert "Import allowed: `true`" in markdown_result.stdout


def test_activation_product_fix_outcome_import_guard_blocks_placeholder_draft(tmp_path: Path) -> None:
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
            "product-fix-outcome-import-guard",
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

    assert payload["guard_status"] == "blocked_until_post_fix_draft_ready"
    assert payload["import_allowed"] is False
    assert "post_fix_summary_placeholder" in payload["blocked_reasons"]
    assert "albu-mcp activation product-fix-outcome-capture --host Codex --format json" in payload["next_commands"]


def test_activation_product_fix_outcome_import_guard_writes_markdown_artifacts(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    draft_path = _write_post_fix_draft(tmp_path)
    output_dir = tmp_path / "product-fix-outcome-import-guard"
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome-import-guard",
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
        "draft-checks.md",
        "guarded-import-command.md",
        "product-fix-outcome-import-guard-index.md",
    }
    index = (output_dir / "product-fix-outcome-import-guard-index.md").read_text(encoding="utf-8")
    checks = (output_dir / "draft-checks.md").read_text(encoding="utf-8")
    command = (output_dir / "guarded-import-command.md").read_text(encoding="utf-8")

    assert (
        result.stdout
        == f"wrote activation product-fix-outcome-import-guard with {len(expected_files)} artifacts to {output_dir}\n"
    )
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "Guard status: `ready_to_import`" in index
    assert "Import allowed: `true`" in index
    assert "workflow_matches_selected_fix" in checks
    assert "Status: `passed`" in checks
    assert f"albu-mcp beta response-import --input {draft_path} --path {beta_records}" in command
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
