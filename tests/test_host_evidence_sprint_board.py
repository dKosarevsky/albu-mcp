from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_host_evidence_sprint_board import (
    build_host_evidence_sprint_board,
    render_host_evidence_sprint_board_markdown,
)


def test_host_evidence_sprint_board_prioritizes_real_host_replay() -> None:
    board = build_host_evidence_sprint_board()
    markdown = render_host_evidence_sprint_board_markdown(board)

    assert board["manual_evidence_policy"] == "Never mark a host passed until a reviewer runs the real host UI."
    assert board["summary"]["passed_manual_host_ui"] == 0
    assert board["summary"]["passed_first_10_minutes_replay"] == 0
    assert [host["host"] for host in board["hosts"]] == ["Codex", "Claude Code", "Cursor", "Claude Desktop"]
    assert [host["priority"] for host in board["hosts"][:2]] == ["p0", "p0"]
    assert all(host["next_gate"] == "first_10_minutes_replay" for host in board["hosts"])
    assert "record_host_manual_run.py --kind first-10-minutes --host Codex" in markdown
    assert "check_first_10_minutes_replay.py --host Codex" in markdown
    assert "Do not paste synthetic evidence" in markdown


def test_committed_host_evidence_sprint_board_is_current() -> None:
    board_path = Path("docs/HOST_EVIDENCE_SPRINT_BOARD.md")

    assert board_path.read_text(encoding="utf-8") == render_host_evidence_sprint_board_markdown(
        build_host_evidence_sprint_board()
    )
    assert "[docs/HOST_EVIDENCE_SPRINT_BOARD.md](docs/HOST_EVIDENCE_SPRINT_BOARD.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )
    assert "docs/HOST_EVIDENCE_SPRINT_BOARD.md" in Path("docs/HOST_PROOF_SPRINT.md").read_text(encoding="utf-8")


def test_host_evidence_sprint_board_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "host-evidence-sprint-board.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_host_evidence_sprint_board.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# Host Evidence Sprint Board\n")
    assert "Manual Evidence Policy" in content
