from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_host_onboarding_depth_plan import (
    build_host_onboarding_depth_plan,
    render_host_onboarding_depth_plan_markdown,
)


def test_host_onboarding_depth_plan_is_selected_but_blocked() -> None:
    plan = build_host_onboarding_depth_plan()

    assert plan["plan_status"] == "blocked_until_depth_gate_opens"
    assert plan["implementation_allowed"] is False
    assert plan["product_area"] == "host_onboarding"
    assert plan["blocked_reasons"] == ["rc_cutover_blocked", "beta_validation_incomplete"]
    assert plan["success_signal"] == "A beta user can recover from setup failure without maintainer intervention."
    assert [item["deliverable"] for item in plan["implementation_slices"]] == [
        "host_setup_probe",
        "approval_troubleshooting",
        "blocked_evidence_capture",
    ]
    assert all(item["status"] == "planned_after_gate" for item in plan["implementation_slices"])


def test_host_onboarding_depth_plan_markdown_is_gate_aware() -> None:
    markdown = render_host_onboarding_depth_plan_markdown(build_host_onboarding_depth_plan())

    assert markdown.startswith("# Host Onboarding Depth Plan\n")
    assert "Plan status: `blocked_until_depth_gate_opens`" in markdown
    assert "Implementation allowed: `false`" in markdown
    assert "| `host_setup_probe` | `planned_after_gate` |" in markdown
    assert "`tools_not_visible`" in markdown
    assert "`uvx_startup_failed`" in markdown
    assert "Do not implement host-onboarding depth work until RC and beta gates open." in markdown


def test_committed_host_onboarding_depth_plan_is_current() -> None:
    plan_path = Path("docs/HOST_ONBOARDING_DEPTH_PLAN.md")

    assert plan_path.read_text(encoding="utf-8") == render_host_onboarding_depth_plan_markdown(
        build_host_onboarding_depth_plan()
    )


def test_host_onboarding_depth_plan_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "host-onboarding-depth-plan.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_host_onboarding_depth_plan.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Host Onboarding Depth Plan\n")
