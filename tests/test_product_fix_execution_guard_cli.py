from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_product_fix_implementation_plan_cli import _write_empty_records, _write_ready_records


def test_activation_product_fix_execution_guard_blocks_without_tdd_plan(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-execution-guard",
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

    assert payload["guard_status"] == "blocked_until_tdd_plan"
    assert payload["plan_status"] == "blocked_until_first_product_fix"
    assert payload["writes_records"] is False
    assert payload["execution_allowed"] is False
    assert payload["branch_scaffold"] is None
    assert payload["command_groups"] == {}
    assert payload["execution_checklist"] == []
    assert payload["blocked_reasons"] == [
        "p0_host_evidence_missing_or_blocked",
        "beta_validation_records_missing",
    ]
    assert "albu-mcp activation product-fix-implementation-plan --host Codex --format json" in payload["next_commands"]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_activation_product_fix_execution_guard_builds_ready_branch_scaffold(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-execution-guard",
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
    branch_scaffold = payload["branch_scaffold"]
    command_groups = payload["command_groups"]
    checklist = payload["execution_checklist"]

    assert payload["guard_status"] == "ready_for_branch_scaffold"
    assert payload["plan_status"] == "ready_for_tdd"
    assert payload["execution_allowed"] is True
    assert payload["selected_fix"]["product_area"] == "preview_review_agent"
    assert branch_scaffold["branch_name"] == "codex/product-fix-preview-review-agent-review-agent-v3-gap"
    assert branch_scaffold["base_branch"] == "main"
    assert branch_scaffold["allowed_source_files"] == [
        "src/albumentationsx_mcp/policy_assistant.py",
        "src/albumentationsx_mcp/review_agent.py",
        "src/albumentationsx_mcp/first_preview.py",
    ]
    assert branch_scaffold["allowed_test_files"] == [
        "tests/test_policy_assistant_runtime.py",
        "tests/test_review_agent.py",
    ]
    assert branch_scaffold["first_commands"] == [
        "git checkout -b codex/product-fix-preview-review-agent-review-agent-v3-gap",
        "uv run pytest tests/test_policy_assistant_runtime.py tests/test_review_agent.py -q",
    ]
    assert "Do not edit host or beta evidence records in the implementation branch." in branch_scaffold["constraints"]
    assert command_groups["red"] == [
        "uv run pytest tests/test_policy_assistant_runtime.py tests/test_review_agent.py -q"
    ]
    assert command_groups["green"] == [
        "uv run pytest tests/test_policy_assistant_runtime.py tests/test_review_agent.py -q"
    ]
    assert "uv run python scripts/check_release_readiness.py" in command_groups["verification"]
    assert [item["id"] for item in checklist] == [
        "create_branch",
        "red_tests",
        "minimal_implementation",
        "verification",
        "pull_request",
        "merge",
    ]
    assert checklist[1]["status"] == "required_before_code"
    assert "Run RED tests before implementation." in checklist[1]["objective"]

    markdown_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-execution-guard",
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

    assert "Guard status: `ready_for_branch_scaffold`" in markdown_result.stdout
    assert "codex/product-fix-preview-review-agent-review-agent-v3-gap" in markdown_result.stdout


def test_activation_product_fix_execution_guard_writes_markdown_artifacts(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    output_dir = tmp_path / "product-fix-execution-guard"
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-execution-guard",
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
        "branch-scaffold.md",
        "execution-checklist.md",
        "product-fix-execution-guard-index.md",
    }
    index = (output_dir / "product-fix-execution-guard-index.md").read_text(encoding="utf-8")
    branch_scaffold = (output_dir / "branch-scaffold.md").read_text(encoding="utf-8")
    execution_checklist = (output_dir / "execution-checklist.md").read_text(encoding="utf-8")

    assert (
        result.stdout
        == f"wrote activation product-fix-execution-guard with {len(expected_files)} artifacts to {output_dir}\n"
    )
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "Guard status: `ready_for_branch_scaffold`" in index
    assert "Branch name: `codex/product-fix-preview-review-agent-review-agent-v3-gap`" in index
    assert "src/albumentationsx_mcp/review_agent.py" in branch_scaffold
    assert "tests/test_review_agent.py" in branch_scaffold
    assert "Run RED tests before implementation." in execution_checklist
    assert "Merge only after local verification and CI are both green." in execution_checklist
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
