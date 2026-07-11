from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_p0_host_run_session import build_p0_host_run_session, render_p0_host_run_session_markdown


def test_p0_host_run_session_tracks_real_host_sessions_without_evidence_claims() -> None:
    session = build_p0_host_run_session()

    assert session["session_status"] == "manual_evidence_required"
    assert session["required_hosts"] == ["Codex", "Claude Code"]
    assert session["non_fabrication_policy"] == "Record only reviewer-observed real host UI evidence."
    assert session["summary"]["missing_gate_count"] == 0
    assert session["summary"]["recorded_gate_count"] == 2
    assert session["summary"]["blocked_gate_count"] == 2
    assert [item["host"] for item in session["host_sessions"]] == ["Codex", "Claude Code"]
    assert [item["session_status"] for item in session["host_sessions"]] == ["passed", "blocked"]
    assert all("run_host_smoke_check" in item["host_prompt"] for item in session["host_sessions"])
    assert all(
        "scripts/record_host_manual_run.py" in command
        for item in session["host_sessions"]
        for command in item["record_commands"]
    )
    assert all(
        set(item["evidence_candidate_templates"]) == {"first_10_minutes_replay", "manual_host_ui"}
        for item in session["host_sessions"]
    )
    assert session["host_sessions"][0]["evidence_candidate_templates"]["manual_host_ui"] == {
        "host": "Codex",
        "status": "passed",
        "date": "YYYY-MM-DD",
        "evidence": "Redacted reviewer-observed Codex host UI evidence summary.",
    }
    assert session["host_sessions"][0]["evidence_candidate_templates"]["first_10_minutes_replay"] == {
        "host": "Codex",
        "status": "passed",
        "date": "YYYY-MM-DD",
        "evidence": "Redacted reviewer-observed Codex first-10-minutes replay summary.",
        "artifacts": ["docs/assets/demo/demo_report.md"],
    }


def test_p0_host_run_session_markdown_is_copyable() -> None:
    markdown = render_p0_host_run_session_markdown(build_p0_host_run_session())

    assert markdown.startswith("# P0 Host Run Session\n")
    assert "Session status: `manual_evidence_required`" in markdown
    assert "Record only reviewer-observed real host UI evidence." in markdown
    assert "## Codex Session" in markdown
    assert "## Claude Code Session" in markdown
    assert "run_host_smoke_check" in markdown
    assert "scripts/record_host_manual_run.py" in markdown
    assert "Evidence candidate templates:" in markdown
    assert '"host": "Codex"' in markdown
    assert '"artifacts": [' in markdown


def test_committed_p0_host_run_session_is_current() -> None:
    session_path = Path("docs/P0_HOST_RUN_SESSION.md")

    assert session_path.read_text(encoding="utf-8") == render_p0_host_run_session_markdown(build_p0_host_run_session())
    assert "[docs/P0_HOST_RUN_SESSION.md](docs/P0_HOST_RUN_SESSION.md)" in Path("README.md").read_text(encoding="utf-8")


def test_p0_host_run_session_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "p0-host-run-session.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_p0_host_run_session.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# P0 Host Run Session\n")
