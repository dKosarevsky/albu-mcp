from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_p0_blocker_triage import build_p0_blocker_triage, render_p0_blocker_triage_markdown


def test_p0_blocker_triage_maps_p0_gates_to_actions() -> None:
    triage = build_p0_blocker_triage()

    assert triage["source_docs"] == [
        "docs/P0_EVIDENCE_STATUS.md",
        "docs/HOST_FAILURE_COOKBOOK.md",
        "docs/HOST_UX_HARDENING_LOOP.md",
    ]
    assert [item["host"] for item in triage["triage_matrix"][:2]] == ["Claude Code", "Claude Code"]
    assert triage["triage_matrix"][0]["gate"] == "first_10_minutes_replay"
    assert triage["triage_matrix"][0]["evidence_status"] == "blocked"
    assert triage["triage_matrix"][0]["triage_action"] == "triage_blocker"
    assert triage["triage_matrix"][0]["entrypoints"] == [
        "docs/P0_HOST_RUNBOOK.md",
        "docs/P0_EVIDENCE_RECORDER.md",
        "docs/HOST_FAILURE_COOKBOOK.md",
    ]
    assert "tools_not_visible" in triage["failure_classes"]
    assert "uvx_startup_failed" in triage["failure_classes"]


def test_p0_blocker_triage_markdown_is_actionable() -> None:
    markdown = render_p0_blocker_triage_markdown(build_p0_blocker_triage())

    assert markdown.startswith("# P0 Blocker Triage Matrix\n")
    assert "## Triage Matrix" in markdown
    assert "| Claude Code | `first_10_minutes_replay` | `blocked` | `triage_blocker` |" in markdown
    assert "## Failure Classes" in markdown
    assert "`tools_not_visible`" in markdown
    assert "`uvx_startup_failed`" in markdown
    assert "## Escalation Rule" in markdown
    assert "Convert repeated blocked evidence into a regression test before changing product behavior." in markdown


def test_committed_p0_blocker_triage_is_current() -> None:
    triage_path = Path("docs/P0_BLOCKER_TRIAGE.md")

    assert triage_path.read_text(encoding="utf-8") == render_p0_blocker_triage_markdown(build_p0_blocker_triage())
    assert "[docs/P0_BLOCKER_TRIAGE.md](docs/P0_BLOCKER_TRIAGE.md)" in Path("README.md").read_text(encoding="utf-8")


def test_p0_blocker_triage_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "p0-blocker-triage.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_p0_blocker_triage.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# P0 Blocker Triage Matrix\n")
