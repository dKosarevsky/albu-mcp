from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_rc_cutover_recovery_plan import (
    build_rc_cutover_recovery_plan,
    render_rc_cutover_recovery_plan_markdown,
)


def test_rc_cutover_recovery_plan_blocks_publish_until_p0_passes() -> None:
    plan = build_rc_cutover_recovery_plan()

    assert plan["recovery_status"] == "blocked_by_p0_evidence"
    assert plan["rc_cutover_allowed"] is False
    assert plan["publish_allowed"] is False
    assert plan["p0_summary"]["recorded_gate_count"] == 2
    assert plan["p0_summary"]["blocked_gate_count"] == 2
    assert plan["safe_preflight_allowed"] is True
    assert plan["publish_commands"] == []
    assert "git tag vX.Y.Z-rc.1" in plan["blocked_publish_commands"]
    assert plan["reopen_criteria"] == [
        "Every P0 host gate has record_status `passed`.",
        "`uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json` exits 0.",
        "Distribution rollout remains unpublished until the RC tag and package are visible.",
    ]


def test_rc_cutover_recovery_plan_markdown_is_release_safe() -> None:
    markdown = render_rc_cutover_recovery_plan_markdown(build_rc_cutover_recovery_plan())

    assert markdown.startswith("# RC Cutover Recovery Plan\n")
    assert "Recovery status: `blocked_by_p0_evidence`" in markdown
    assert "Publish allowed: `false`" in markdown
    assert "Do not tag, create a GitHub Release, or publish to PyPI while recovery_status is blocked." in markdown
    assert "`uv run pytest -q`" in markdown
    assert "`git tag vX.Y.Z-rc.1`" in markdown


def test_committed_rc_cutover_recovery_plan_is_current() -> None:
    plan_path = Path("docs/RC_CUTOVER_RECOVERY_PLAN.md")

    assert plan_path.read_text(encoding="utf-8") == render_rc_cutover_recovery_plan_markdown(
        build_rc_cutover_recovery_plan()
    )


def test_rc_cutover_recovery_plan_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "rc-cutover-recovery-plan.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_rc_cutover_recovery_plan.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# RC Cutover Recovery Plan\n")
