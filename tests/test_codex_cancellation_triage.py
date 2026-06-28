from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_codex_cancellation_triage import (
    build_codex_cancellation_triage,
    render_codex_cancellation_triage_markdown,
)


def test_codex_cancellation_triage_builds_blocked_codex_lanes() -> None:
    triage = build_codex_cancellation_triage()

    assert triage["triage_status"] == "blocked_tool_call_cancellation"
    assert triage["host"] == "Codex"
    assert triage["failure_class"] == "codex_tool_call_cancelled"
    assert triage["rc_reopen_allowed"] is False
    assert triage["summary"] == {
        "affected_gate_count": 2,
        "blocked_gate_count": 2,
        "missing_gate_count": 0,
    }
    assert [gate["gate"] for gate in triage["affected_gates"]] == [
        "first_10_minutes_replay",
        "manual_host_ui",
    ]
    assert all(gate["evidence_status"] == "blocked" for gate in triage["affected_gates"])
    assert all("run_host_smoke_check" in command for command in triage["record_commands"]["blocked"])


def test_codex_cancellation_triage_markdown_is_operator_focused() -> None:
    markdown = render_codex_cancellation_triage_markdown(build_codex_cancellation_triage())

    assert markdown.startswith("# Codex Cancellation Triage\n")
    assert "Triage status: `blocked_tool_call_cancellation`" in markdown
    assert "A cancelled Codex MCP tool call is blocking evidence" in markdown
    assert "| `first_10_minutes_replay` | `blocked` |" in markdown
    assert "run_host_smoke_check completes in Codex and reports preview_ready=true" in markdown
    assert "Do not use generated smoke output as real Codex UI evidence" in markdown


def test_committed_codex_cancellation_triage_is_current() -> None:
    triage_path = Path("docs/CODEX_CANCELLATION_TRIAGE.md")

    assert triage_path.read_text(encoding="utf-8") == render_codex_cancellation_triage_markdown(
        build_codex_cancellation_triage()
    )


def test_codex_cancellation_triage_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "codex-cancellation-triage.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_codex_cancellation_triage.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Codex Cancellation Triage\n")
