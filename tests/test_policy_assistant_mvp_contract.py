from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_policy_assistant_mvp_contract import (
    build_policy_assistant_mvp_contract,
    render_policy_assistant_mvp_contract_markdown,
)


def test_policy_assistant_mvp_contract_is_blocked_behind_gates() -> None:
    contract = build_policy_assistant_mvp_contract()

    assert contract["contract_status"] == "blocked_until_rc_and_beta_signal"
    assert contract["runtime_implementation_allowed"] is False
    assert contract["safe_runtime_mvp_available"] is True
    assert contract["production_policy_acceptance_allowed"] is False
    assert contract["first_slice"] == "feedback_aware_policy_recommendation"
    assert contract["blocked_reasons"] == [
        "p0_host_evidence_missing_or_blocked",
        "beta_validation_records_missing",
    ]
    assert [item["name"] for item in contract["interfaces"]] == [
        "policy_context",
        "feedback_signal",
        "recommendation_result",
        "candidate_set",
    ]
    assert contract["runtime_tools"] == [
        "plan_augmentation_policy",
        "plan_augmentation_policy_candidates",
        "plan_policy_iteration",
    ]


def test_policy_assistant_mvp_contract_markdown_defines_clean_interfaces() -> None:
    markdown = render_policy_assistant_mvp_contract_markdown(build_policy_assistant_mvp_contract())

    assert markdown.startswith("# Policy Assistant MVP Contract\n")
    assert "Runtime implementation allowed: `false`" in markdown
    assert "Safe runtime MVP available: `true`" in markdown
    assert "Production policy acceptance allowed: `false`" in markdown
    assert "`policy_context`" in markdown
    assert "`recommendation_result`" in markdown
    assert "`candidate_set`" in markdown
    assert "`plan_augmentation_policy_candidates`" in markdown
    assert "`plan_policy_iteration`" in markdown
    assert "starter candidates only" in markdown


def test_committed_policy_assistant_mvp_contract_is_current() -> None:
    path = Path("docs/POLICY_ASSISTANT_MVP_CONTRACT.md")

    assert path.read_text(encoding="utf-8") == render_policy_assistant_mvp_contract_markdown(
        build_policy_assistant_mvp_contract()
    )


def test_policy_assistant_mvp_contract_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "policy-assistant-mvp-contract.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_policy_assistant_mvp_contract.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Policy Assistant MVP Contract\n")
