from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_v1_stabilization_plan import (
    build_v1_stabilization_plan,
    render_v1_stabilization_plan_markdown,
)


def test_v1_stabilization_plan_blocks_stable_v1_until_trust_gates_pass() -> None:
    plan = build_v1_stabilization_plan()

    assert plan["stabilization_status"] == "blocked_until_trust_gates_pass"
    assert plan["ready_for_v1"] is False
    assert plan["stable_v1_allowed"] is False
    assert plan["manual_gate_count"] == 8
    assert plan["cutover_status"] == "blocked_by_p0_evidence"
    assert plan["selected_depth_item"] == "host_onboarding"
    assert plan["feature_freeze_policy"] == (
        "Keep v1 scope frozen to release reliability, host evidence, beta validation, and documentation corrections."
    )
    assert "Do not publish a stable v1 while host_blocker_count is greater than zero." in plan["non_goals"]


def test_v1_stabilization_plan_markdown_lists_scope_and_exit_criteria() -> None:
    markdown = render_v1_stabilization_plan_markdown(build_v1_stabilization_plan())

    assert markdown.startswith("# V1 Stabilization Plan\n")
    assert "Stabilization status: `blocked_until_trust_gates_pass`" in markdown
    assert "Stable v1 allowed: `false`" in markdown
    assert "## V1 Scope" in markdown
    assert "P0 host evidence is passed for required RC hosts." in markdown
    assert "## Post-V1 Backlog" in markdown
    assert "`host_onboarding`" in markdown


def test_committed_v1_stabilization_plan_is_current() -> None:
    plan_path = Path("docs/V1_STABILIZATION_PLAN.md")

    assert plan_path.read_text(encoding="utf-8") == render_v1_stabilization_plan_markdown(
        build_v1_stabilization_plan()
    )


def test_v1_stabilization_plan_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "v1-stabilization-plan.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_v1_stabilization_plan.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# V1 Stabilization Plan\n")
