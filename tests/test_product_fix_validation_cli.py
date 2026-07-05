from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_product_fix_implementation_plan_cli import _write_empty_records, _write_ready_records


def test_activation_product_fix_validation_blocks_without_selected_fix(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-validation",
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

    assert payload["validation_status"] == "blocked_until_execution_guard"
    assert payload["execution_allowed"] is False
    assert payload["fix_validated"] is False
    assert payload["behavior_contract"] is None
    assert payload["validation_results"] == []
    assert "p0_host_evidence_missing_or_blocked" in payload["blocked_reasons"]
    assert "albu-mcp activation product-fix-execution-guard --host Codex --format json" in payload["next_commands"]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_activation_product_fix_validation_validates_review_agent_contract(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-validation",
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
    contract = payload["behavior_contract"]

    assert payload["validation_status"] == "validated"
    assert payload["guard_status"] == "ready_for_branch_scaffold"
    assert payload["execution_allowed"] is True
    assert payload["fix_validated"] is True
    assert payload["selected_fix"]["triage_bucket"] == "review_agent_v3_gap"
    assert contract["contract_id"] == "review_agent_v3_gap_readability_recovery"
    assert contract["feedback_note"] == "Example 8 is maybe too noisy; I can't even recognize the objects."
    assert contract["expected_candidate_order"] == [
        "minimal_change",
        "conservative",
        "review_safe",
        "balanced",
    ]
    assert contract["observed_candidate_order"] == [
        "minimal_change",
        "conservative",
        "review_safe",
        "balanced",
    ]
    assert all(result["status"] == "passed" for result in payload["validation_results"])
    assert [result["id"] for result in payload["validation_results"]] == [
        "feedback_interpretation",
        "candidate_recovery_order",
        "aggressive_candidate_removed",
        "iteration_recovery_action",
    ]
    assert "uv run pytest tests/test_policy_assistant_candidates.py -q" in payload["next_commands"]

    markdown_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-validation",
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

    assert "Validation status: `validated`" in markdown_result.stdout
    assert "review_agent_v3_gap_readability_recovery" in markdown_result.stdout


def test_activation_product_fix_validation_writes_markdown_artifacts(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    output_dir = tmp_path / "product-fix-validation"
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-validation",
            "--host",
            "Codex",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
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
        "behavior-contract.md",
        "product-fix-validation-index.md",
        "validation-results.md",
    }
    index = (output_dir / "product-fix-validation-index.md").read_text(encoding="utf-8")
    contract = (output_dir / "behavior-contract.md").read_text(encoding="utf-8")
    results = (output_dir / "validation-results.md").read_text(encoding="utf-8")

    assert (
        result.stdout
        == f"wrote activation product-fix-validation with {len(expected_files)} artifacts to {output_dir}\n"
    )
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "Validation status: `validated`" in index
    assert "Fix validated: `true`" in index
    assert "Expected candidate order" in contract
    assert "`minimal_change`" in contract
    assert "aggressive_candidate_removed" in results
    assert "Status: `passed`" in results
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
