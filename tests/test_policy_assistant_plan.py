from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_policy_assistant_plan import build_policy_assistant_plan, render_policy_assistant_plan_markdown


def test_policy_assistant_plan_is_gate_aware_and_not_yet_implementation_allowed() -> None:
    plan = build_policy_assistant_plan()

    assert plan["plan_status"] == "blocked_until_rc_and_beta_signal"
    assert plan["implementation_allowed"] is False
    assert plan["product_thesis"] == "Turn AlbumentationsX MCP into an interactive augmentation-policy assistant."
    assert plan["first_slice"] == "feedback_aware_policy_recommendation"
    assert plan["blocked_reasons"] == [
        "p0_host_evidence_missing_or_blocked",
        "beta_validation_records_missing",
    ]
    assert [component["name"] for component in plan["components"]] == [
        "dataset_signal_reader",
        "policy_candidate_generator",
        "preview_feedback_loop",
        "exportable_policy_contract",
    ]


def test_policy_assistant_plan_markdown_documents_clean_boundaries() -> None:
    markdown = render_policy_assistant_plan_markdown(build_policy_assistant_plan())

    assert markdown.startswith("# Policy Assistant Plan\n")
    assert "Plan status: `blocked_until_rc_and_beta_signal`" in markdown
    assert "Turn AlbumentationsX MCP into an interactive augmentation-policy assistant." in markdown
    assert "`dataset_signal_reader`" in markdown
    assert "`exportable_policy_contract`" in markdown
    assert "Do not start runtime implementation until RC and beta gates open." in markdown


def test_committed_policy_assistant_plan_is_current() -> None:
    doc_path = Path("docs/POLICY_ASSISTANT_PLAN.md")

    assert doc_path.read_text(encoding="utf-8") == render_policy_assistant_plan_markdown(build_policy_assistant_plan())
    assert "[docs/POLICY_ASSISTANT_PLAN.md](docs/POLICY_ASSISTANT_PLAN.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_policy_assistant_plan_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "policy-assistant-plan.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_policy_assistant_plan.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Policy Assistant Plan\n")
