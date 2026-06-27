from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_v1_rc_cutover_checklist import (
    build_v1_rc_cutover_checklist,
    render_v1_rc_cutover_checklist_markdown,
)


def test_v1_rc_cutover_checklist_is_blocked_by_p0_evidence() -> None:
    checklist = build_v1_rc_cutover_checklist()

    assert checklist["cutover_status"] == "blocked"
    assert checklist["rc_decision"] == "hold_rc"
    assert checklist["release_candidate_allowed"] is False
    assert checklist["required_hosts"] == ["Codex", "Claude Code"]
    assert checklist["hard_gates"][0] == "P0 real host evidence passed for Codex and Claude Code."
    assert "Do not create or push an RC tag while cutover_status is blocked." in checklist["no_go_rules"]
    assert "git tag vX.Y.Z-rc.1" in checklist["ready_commands"]


def test_v1_rc_cutover_checklist_markdown_is_release_operator_focused() -> None:
    markdown = render_v1_rc_cutover_checklist_markdown(build_v1_rc_cutover_checklist())

    assert markdown.startswith("# V1 RC Cutover Checklist\n")
    assert "Cutover status: `blocked`" in markdown
    assert "Release candidate allowed: `false`" in markdown
    assert "## No-Go Rules" in markdown
    assert "Do not create or push an RC tag while cutover_status is blocked." in markdown
    assert "## Ready Commands" in markdown
    assert "`uv run python scripts/check_release_readiness.py`" in markdown
    assert "`git tag vX.Y.Z-rc.1`" in markdown


def test_committed_v1_rc_cutover_checklist_is_current() -> None:
    checklist_path = Path("docs/V1_RC_CUTOVER_CHECKLIST.md")

    assert checklist_path.read_text(encoding="utf-8") == render_v1_rc_cutover_checklist_markdown(
        build_v1_rc_cutover_checklist()
    )
    assert "[docs/V1_RC_CUTOVER_CHECKLIST.md](docs/V1_RC_CUTOVER_CHECKLIST.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_v1_rc_cutover_checklist_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "v1-rc-cutover-checklist.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_v1_rc_cutover_checklist.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# V1 RC Cutover Checklist\n")
