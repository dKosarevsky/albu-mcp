from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_p0_host_evidence_recovery import (
    build_p0_host_evidence_recovery,
    render_p0_host_evidence_recovery_markdown,
)


def test_p0_host_evidence_recovery_keeps_gate_blocked_until_real_evidence() -> None:
    recovery = build_p0_host_evidence_recovery()

    assert recovery["recovery_status"] == "blocked_until_real_host_evidence"
    assert recovery["rc_ready"] is False
    assert recovery["rc_reopen_allowed"] is False
    assert recovery["summary"] == {
        "target_host_count": 2,
        "required_gate_count": 4,
        "passed_gate_count": 0,
        "blocked_gate_count": 4,
        "missing_gate_count": 0,
    }
    assert [lane["host"] for lane in recovery["host_recovery_lanes"]] == ["Codex", "Claude Code"]
    assert recovery["host_recovery_lanes"][0]["blocker"] == "codex_tool_call_cancelled"
    assert recovery["host_recovery_lanes"][1]["blocker"] == "claude_cli_missing"
    assert all(
        "record_host_manual_run.py" in command
        for lane in recovery["host_recovery_lanes"]
        for command in lane["passed_record_commands"] + lane["blocked_record_commands"]
    )


def test_p0_host_evidence_recovery_markdown_is_operator_focused() -> None:
    markdown = render_p0_host_evidence_recovery_markdown(build_p0_host_evidence_recovery())

    assert markdown.startswith("# P0 Host Evidence Recovery\n")
    assert "Recovery status: `blocked_until_real_host_evidence`" in markdown
    assert "Do not replace blocked P0 records until Codex and Claude Code complete" in markdown
    assert "| Codex | `blocked_tool_call_cancellation` | `codex_tool_call_cancelled` |" in markdown
    assert "| Claude Code | `blocked_until_claude_cli_visible` | `claude_cli_missing` |" in markdown
    assert "run_host_smoke_check" in markdown
    assert "docs/CLAUDE_CODE_SETUP_PATH.md" in markdown


def test_committed_p0_host_evidence_recovery_is_current() -> None:
    recovery_path = Path("docs/P0_HOST_EVIDENCE_RECOVERY.md")

    assert recovery_path.read_text(encoding="utf-8") == render_p0_host_evidence_recovery_markdown(
        build_p0_host_evidence_recovery()
    )


def test_p0_host_evidence_recovery_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "p0-host-evidence-recovery.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_p0_host_evidence_recovery.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# P0 Host Evidence Recovery\n")
