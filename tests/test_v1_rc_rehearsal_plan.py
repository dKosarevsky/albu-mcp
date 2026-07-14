from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_v1_rc_rehearsal_plan import (
    build_v1_rc_rehearsal_plan,
    render_v1_rc_rehearsal_plan_markdown,
)


def test_v1_rc_rehearsal_plan_keeps_publish_blocked_without_p0_evidence() -> None:
    plan = build_v1_rc_rehearsal_plan()

    assert plan["rehearsal_status"] == "preflight_only"
    assert plan["rc_cutover_allowed"] is False
    assert plan["release_tag"] == "vX.Y.Z-rc.1"
    assert plan["dry_run_allowed"] is True
    assert plan["publish_allowed"] is False
    assert "uv run pytest -q" in plan["dry_run_commands"]
    assert "uv build" in plan["dry_run_commands"]
    assert plan["publish_commands"] == []
    assert "git tag vX.Y.Z-rc.1" in plan["blocked_publish_commands"]
    assert plan["stop_conditions"] == [
        "Any P0 host evidence gate is missing or blocked.",
        "The worktree is dirty after regenerating release reports.",
        "Any local verification command fails.",
    ]


def test_v1_rc_rehearsal_plan_markdown_is_operator_safe() -> None:
    markdown = render_v1_rc_rehearsal_plan_markdown(build_v1_rc_rehearsal_plan())

    assert markdown.startswith("# V1 RC Rehearsal Plan\n")
    assert "Rehearsal status: `preflight_only`" in markdown
    assert "Dry run allowed: `true`" in markdown
    assert "Publish allowed: `false`" in markdown
    assert "## Dry-Run Commands" in markdown
    assert "`uv build`" in markdown
    assert "## Blocked Publish Commands" in markdown
    assert "`git tag vX.Y.Z-rc.1`" in markdown
    assert "Do not create tags, GitHub Releases, or PyPI uploads during rehearsal." in markdown


def test_committed_v1_rc_rehearsal_plan_is_current() -> None:
    plan_path = Path("docs/V1_RC_REHEARSAL_PLAN.md")

    assert plan_path.read_text(encoding="utf-8") == render_v1_rc_rehearsal_plan_markdown(build_v1_rc_rehearsal_plan())
    assert "[V1_RC_REHEARSAL_PLAN.md](V1_RC_REHEARSAL_PLAN.md)" in Path("docs/INDEX.md").read_text(encoding="utf-8")


def test_v1_rc_rehearsal_plan_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "v1-rc-rehearsal-plan.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_v1_rc_rehearsal_plan.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# V1 RC Rehearsal Plan\n")
