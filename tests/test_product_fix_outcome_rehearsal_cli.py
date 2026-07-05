from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_product_fix_implementation_plan_cli import _write_empty_records, _write_ready_records
from tests.test_product_fix_outcome_import_guard_cli import _write_post_fix_draft


def test_activation_product_fix_outcome_rehearsal_blocks_without_capture_ready(tmp_path: Path) -> None:
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
            "product-fix-outcome-rehearsal",
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

    assert payload["rehearsal_status"] == "blocked_until_capture_ready"
    assert payload["capture_status"] == "blocked_until_product_fix_validation"
    assert payload["import_guard_status"] is None
    assert payload["projected_outcome_status"] is None
    assert payload["writes_records"] is False
    assert payload["import_allowed"] is False
    assert "capture_status_not_ready" in payload["stop_conditions"]
    assert "albu-mcp activation product-fix-validation --host Codex --format json" in payload["next_commands"]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_activation_product_fix_outcome_rehearsal_projects_ready_import_outcome(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    draft_path = _write_post_fix_draft(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome-rehearsal",
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

    assert payload["rehearsal_status"] == "ready_for_guarded_import"
    assert payload["capture_status"] == "ready_to_capture"
    assert payload["import_guard_status"] == "ready_to_import"
    assert payload["projected_outcome_status"] == "accepted"
    assert payload["writes_records"] is False
    assert payload["import_allowed"] is True
    assert payload["selected_fix"]["triage_bucket"] == "review_agent_v3_gap"
    assert payload["input_path"] == str(draft_path)
    assert payload["stop_conditions"] == []
    assert [step["id"] for step in payload["rehearsal_steps"]] == [
        "capture_ready",
        "draft_import_guard",
        "projected_outcome",
        "guarded_import",
    ]
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
            "product-fix-outcome-rehearsal",
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

    assert "Rehearsal status: `ready_for_guarded_import`" in markdown_result.stdout
    assert "Projected outcome: `accepted`" in markdown_result.stdout


def test_activation_product_fix_outcome_rehearsal_blocks_placeholder_draft(tmp_path: Path) -> None:
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
            "product-fix-outcome-rehearsal",
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

    assert payload["rehearsal_status"] == "blocked_until_post_fix_import_guard"
    assert payload["capture_status"] == "ready_to_capture"
    assert payload["import_guard_status"] == "blocked_until_post_fix_draft_ready"
    assert payload["projected_outcome_status"] is None
    assert payload["import_allowed"] is False
    assert "post_fix_summary_placeholder" in payload["stop_conditions"]
    assert "post_fix_summary_placeholder" in payload["source_import_guard"]["blocked_reasons"]


def test_activation_product_fix_outcome_rehearsal_writes_artifacts_without_records(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    draft_path = _write_post_fix_draft(tmp_path)
    output_dir = tmp_path / "product-fix-outcome-rehearsal"
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-outcome-rehearsal",
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
        "product-fix-outcome-rehearsal-index.md",
        "rehearsal-steps.md",
        "stop-conditions.md",
    }
    index = (output_dir / "product-fix-outcome-rehearsal-index.md").read_text(encoding="utf-8")
    steps = (output_dir / "rehearsal-steps.md").read_text(encoding="utf-8")
    stops = (output_dir / "stop-conditions.md").read_text(encoding="utf-8")

    assert (
        result.stdout
        == f"wrote activation product-fix-outcome-rehearsal with {len(expected_files)} artifacts to {output_dir}\n"
    )
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "Rehearsal status: `ready_for_guarded_import`" in index
    assert "Projected outcome: `accepted`" in index
    assert "draft_import_guard" in steps
    assert "No active stop conditions." in stops
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
