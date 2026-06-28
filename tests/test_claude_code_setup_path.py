from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_claude_code_setup_path import (
    build_claude_code_setup_path,
    render_claude_code_setup_path_markdown,
)


def test_claude_code_setup_path_builds_blocked_setup_checks() -> None:
    setup = build_claude_code_setup_path()

    assert setup["setup_status"] == "blocked_until_claude_cli_visible"
    assert setup["host"] == "Claude Code"
    assert setup["failure_class"] == "claude_cli_missing"
    assert setup["cli_required"] is True
    assert setup["rc_reopen_allowed"] is False
    assert setup["summary"] == {
        "affected_gate_count": 2,
        "blocked_gate_count": 2,
        "setup_check_count": 6,
    }
    assert setup["mcp_config"]["command"] == "uvx"
    assert "--allowed-root" in setup["mcp_config"]["args"]
    assert setup["setup_checks"][0] == "command -v claude"
    assert any("claude mcp add-json" in check for check in setup["setup_checks"])
    assert [gate["gate"] for gate in setup["affected_gates"]] == [
        "first_10_minutes_replay",
        "manual_host_ui",
    ]


def test_claude_code_setup_path_markdown_is_operator_focused() -> None:
    markdown = render_claude_code_setup_path_markdown(build_claude_code_setup_path())

    assert markdown.startswith("# Claude Code Setup Path\n")
    assert "Setup status: `blocked_until_claude_cli_visible`" in markdown
    assert "Do not replay Claude Code P0 gates until the `claude` CLI is visible" in markdown
    assert '"command": "uvx"' in markdown
    assert "`claude --version` succeeds in the operator shell" in markdown
    assert "run_host_smoke_check completes in Claude Code with preview_ready=true" in markdown


def test_committed_claude_code_setup_path_is_current() -> None:
    setup_path = Path("docs/CLAUDE_CODE_SETUP_PATH.md")

    assert setup_path.read_text(encoding="utf-8") == render_claude_code_setup_path_markdown(
        build_claude_code_setup_path()
    )


def test_claude_code_setup_path_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "claude-code-setup-path.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_claude_code_setup_path.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Claude Code Setup Path\n")
