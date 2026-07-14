from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_codex_cancellation_triage import (
    build_codex_cancellation_triage,
    render_codex_cancellation_triage_markdown,
)


def test_codex_cancellation_triage_reports_recorded_codex_evidence() -> None:
    triage = build_codex_cancellation_triage()

    assert triage["triage_status"] == "codex_evidence_recorded"
    assert triage["host"] == "Codex"
    assert triage["failure_class"] == "codex_tool_call_cancelled"
    assert triage["rc_reopen_allowed"] is False
    assert triage["summary"] == {
        "affected_gate_count": 0,
        "blocked_gate_count": 0,
        "missing_gate_count": 0,
    }
    assert triage["affected_gates"] == []
    assert triage["record_commands"] == {"passed": [], "blocked": []}
    assert "No Codex cancellation recovery lane remains" in triage["triage_policy"]


def test_codex_cancellation_triage_markdown_is_operator_focused() -> None:
    markdown = render_codex_cancellation_triage_markdown(build_codex_cancellation_triage())

    assert markdown.startswith("# Codex Cancellation Triage\n")
    assert "Triage status: `codex_evidence_recorded`" in markdown
    assert "No Codex cancellation recovery lane remains" in markdown
    assert "| `none` | `recorded` | `none` | `none` |" in markdown
    assert "run_host_smoke_check completes in Codex and reports preview_ready=true" in markdown
    assert "Do not use generated smoke output as real Codex UI evidence" in markdown


def test_committed_codex_cancellation_triage_is_current() -> None:
    triage_path = Path("docs/CODEX_CANCELLATION_TRIAGE.md")

    assert triage_path.read_text(encoding="utf-8") == render_codex_cancellation_triage_markdown(
        build_codex_cancellation_triage()
    )
    assert "[CODEX_CANCELLATION_TRIAGE.md](CODEX_CANCELLATION_TRIAGE.md)" in Path("docs/INDEX.md").read_text(
        encoding="utf-8"
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
