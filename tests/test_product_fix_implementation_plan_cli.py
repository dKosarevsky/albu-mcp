from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_empty_records(tmp_path: Path) -> tuple[Path, Path]:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")
    return host_records, beta_records


def _write_ready_records(tmp_path: Path) -> tuple[Path, Path]:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text(
        json.dumps(
            {
                "manual_host_ui": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-07-05",
                        "evidence": (
                            "Reviewer observed real Codex MCP host UI, listed AlbumentationsX MCP tools, "
                            "ran run_host_smoke_check, and confirmed preview_ready=true."
                        ),
                    },
                    {
                        "host": "Claude Code",
                        "status": "passed",
                        "date": "2026-07-05",
                        "evidence": (
                            "Reviewer observed real Claude Code MCP host UI, listed AlbumentationsX MCP tools, "
                            "ran run_host_smoke_check, and confirmed preview_ready=true."
                        ),
                    },
                ],
                "first_10_minutes_replay": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-07-05",
                        "evidence": "Reviewer observed real Codex first-preview replay from install to comparison.",
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    },
                    {
                        "host": "Claude Code",
                        "status": "passed",
                        "date": "2026-07-05",
                        "evidence": (
                            "Reviewer observed real Claude Code first-preview replay from install to comparison."
                        ),
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    beta_records.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "workflow_id": "dataset_health_before_training",
                        "status": "passed",
                        "attempt_date": "2026-07-05",
                        "participant_role": "ML practitioner",
                        "summary": "Dataset health attempt found class imbalance before preview rendering.",
                        "triage_bucket": "dataset_quality_gap",
                        "artifact_refs": ["docs/assets/demo/demo_report.md"],
                        "private_data_included": False,
                    },
                    {
                        "workflow_id": "noisy_preview_tuning",
                        "status": "needs_followup",
                        "attempt_date": "2026-07-05",
                        "participant_role": "ML practitioner",
                        "summary": "Noisy preview feedback identified one candidate that should be softened.",
                        "triage_bucket": "review_agent_v3_gap",
                        "artifact_refs": ["docs/assets/demo/demo_report.md"],
                        "private_data_included": False,
                    },
                    {
                        "workflow_id": "robustness_distortion_variants",
                        "status": "passed",
                        "attempt_date": "2026-07-05",
                        "participant_role": "CV engineer",
                        "summary": "Robustness variants matched the participant goal after contact sheet review.",
                        "triage_bucket": "workflow_fit_gap",
                        "artifact_refs": ["docs/assets/demo/demo_report.md"],
                        "private_data_included": False,
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return host_records, beta_records


def test_activation_product_fix_implementation_plan_blocks_without_selected_fix(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-implementation-plan",
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

    assert payload["plan_status"] == "blocked_until_first_product_fix"
    assert payload["selector_status"] == "blocked_until_external_evidence"
    assert payload["writes_records"] is False
    assert payload["implementation_allowed"] is False
    assert payload["selected_fix"] is None
    assert payload["implementation_plan"] is None
    assert payload["blocked_reasons"] == [
        "p0_host_evidence_missing_or_blocked",
        "beta_validation_records_missing",
    ]
    assert "albu-mcp activation first-product-fix --host Codex --format json" in payload["next_commands"]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_activation_product_fix_implementation_plan_builds_ready_tdd_plan(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-implementation-plan",
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
    plan = payload["implementation_plan"]

    assert payload["plan_status"] == "ready_for_tdd"
    assert payload["selector_status"] == "ready_for_implementation"
    assert payload["implementation_allowed"] is True
    assert payload["blocked_reasons"] == []
    assert payload["selected_fix"]["product_area"] == "preview_review_agent"
    assert plan["product_area"] == "preview_review_agent"
    assert plan["triage_bucket"] == "review_agent_v3_gap"
    assert plan["scope"] == "Feedback-to-adjustment planning that better handles noisy or unreadable previews."
    assert plan["success_signal"] == "Repeated noisy-preview feedback maps to safer candidate adjustments."
    assert plan["suggested_files"][:2] == [
        "src/albumentationsx_mcp/policy_assistant.py",
        "src/albumentationsx_mcp/review_agent.py",
    ]
    assert [phase["id"] for phase in plan["phases"]] == [
        "red_tests",
        "minimal_implementation",
        "verification",
        "merge",
    ]
    assert plan["phases"][0]["status"] == "write_first"
    assert plan["phases"][0]["commands"][0].startswith("uv run pytest")
    assert "tests/test_policy_assistant_runtime.py" in plan["phases"][0]["commands"][0]
    assert "tests/test_review_agent.py" in plan["phases"][0]["commands"][0]
    assert plan["phases"][2]["commands"] == [
        "uv run ruff check .",
        "uv run ruff format --check .",
        "uv run ty check",
        "uv run python scripts/check_release_readiness.py",
        "uv run pytest -q",
    ]

    markdown_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-implementation-plan",
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

    assert "preview_review_agent" in markdown_result.stdout
    assert "Write failing tests for preview_review_agent before implementation." in markdown_result.stdout


def test_activation_product_fix_implementation_plan_writes_markdown_artifacts(tmp_path: Path) -> None:
    host_records, beta_records = _write_ready_records(tmp_path)
    output_dir = tmp_path / "product-fix-implementation-plan"
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "product-fix-implementation-plan",
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
        "product-fix-implementation-plan-index.md",
        "tdd-plan.md",
        "verification-plan.md",
    }
    index = (output_dir / "product-fix-implementation-plan-index.md").read_text(encoding="utf-8")
    tdd_plan = (output_dir / "tdd-plan.md").read_text(encoding="utf-8")
    verification_plan = (output_dir / "verification-plan.md").read_text(encoding="utf-8")

    assert (
        result.stdout
        == f"wrote activation product-fix-implementation-plan with {len(expected_files)} artifacts to {output_dir}\n"
    )
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "Plan status: `ready_for_tdd`" in index
    assert "Product area: `preview_review_agent`" in index
    assert "Write failing tests for preview_review_agent before implementation." in tdd_plan
    assert "uv run pytest tests/test_policy_assistant_runtime.py tests/test_review_agent.py -q" in tdd_plan
    assert "uv run python scripts/check_release_readiness.py" in verification_plan
    assert "CI passes on every configured Python version." in verification_plan
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
