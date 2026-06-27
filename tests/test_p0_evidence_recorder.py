from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_p0_evidence_recorder import build_p0_evidence_recorder, render_p0_evidence_recorder_markdown


def test_p0_evidence_recorder_exposes_safe_recording_contract() -> None:
    recorder = build_p0_evidence_recorder()

    assert recorder["target_hosts"] == ["Codex", "Claude Code"]
    assert recorder["recording_policy"] == "Record only redacted, reviewer-observed host UI evidence."
    assert recorder["required_fields"] == ["host", "gate", "status", "date", "evidence", "artifact"]
    assert [item["host"] for item in recorder["records"]] == ["Codex", "Claude Code"]
    assert set(recorder["records"][0]["gates"]) == {"first_10_minutes_replay", "manual_host_ui"}
    assert "record_host_manual_run.py --host Codex --status passed" in recorder["records"][0]["commands"][
        "manual_host_ui"
    ]["passed"]
    assert "--kind first-10-minutes --host Codex --status blocked" in recorder["records"][0]["commands"][
        "first_10_minutes_replay"
    ]["blocked"]


def test_p0_evidence_recorder_markdown_is_copyable() -> None:
    markdown = render_p0_evidence_recorder_markdown(build_p0_evidence_recorder())

    assert markdown.startswith("# P0 Evidence Recorder\n")
    assert "## Recording Policy" in markdown
    assert "Record only redacted, reviewer-observed host UI evidence." in markdown
    assert "## Required Fields" in markdown
    assert "`artifact`" in markdown
    assert "### Codex" in markdown
    assert "### Claude Code" in markdown
    assert "status passed" in markdown
    assert "status blocked" in markdown
    assert "status pending" in markdown
    assert "Do not record private screenshots, prompts, tokens, or full host logs." in markdown


def test_committed_p0_evidence_recorder_is_current() -> None:
    recorder_path = Path("docs/P0_EVIDENCE_RECORDER.md")

    assert recorder_path.read_text(encoding="utf-8") == render_p0_evidence_recorder_markdown(
        build_p0_evidence_recorder()
    )
    assert "[docs/P0_EVIDENCE_RECORDER.md](docs/P0_EVIDENCE_RECORDER.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_p0_evidence_recorder_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "p0-evidence-recorder.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_p0_evidence_recorder.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# P0 Evidence Recorder\n")
