from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_p0_evidence_status import build_p0_evidence_status, render_p0_evidence_status_markdown


def test_p0_evidence_status_tracks_rc_hosts_and_missing_gates() -> None:
    status = build_p0_evidence_status()

    assert status["target_hosts"] == ["Codex", "Claude Code"]
    assert status["rc_decision"] == "hold_rc"
    assert status["rc_ready"] is False
    assert status["summary"] == {
        "host_count": 2,
        "passed_gate_count": 0,
        "required_gate_count": 4,
        "blocked_gate_count": 0,
        "missing_gate_count": 4,
    }
    assert [item["host"] for item in status["host_statuses"]] == ["Codex", "Claude Code"]
    assert all(gate["status"] == "missing" for item in status["host_statuses"] for gate in item["gates"])
    assert status["next_action"] == "Run P0 host runbook and record real UI evidence."


def test_p0_evidence_status_markdown_is_reviewable() -> None:
    markdown = render_p0_evidence_status_markdown(build_p0_evidence_status())

    assert markdown.startswith("# P0 Evidence Status\n")
    assert "RC decision: `hold_rc`" in markdown
    assert "RC ready: `false`" in markdown
    assert "| Codex | `first_10_minutes_replay` | `missing` |" in markdown
    assert "| Claude Code | `manual_host_ui` | `missing` |" in markdown
    assert "Run P0 host runbook and record real UI evidence." in markdown


def test_committed_p0_evidence_status_is_current() -> None:
    status_path = Path("docs/P0_EVIDENCE_STATUS.md")

    assert status_path.read_text(encoding="utf-8") == render_p0_evidence_status_markdown(build_p0_evidence_status())
    assert "[docs/P0_EVIDENCE_STATUS.md](docs/P0_EVIDENCE_STATUS.md)" in Path("README.md").read_text(encoding="utf-8")


def test_p0_evidence_status_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "p0-evidence-status.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_p0_evidence_status.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# P0 Evidence Status\n")
