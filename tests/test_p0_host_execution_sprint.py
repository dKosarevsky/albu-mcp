from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_p0_host_execution_sprint import (
    build_p0_host_execution_sprint,
    render_p0_host_execution_sprint_markdown,
)


def test_p0_host_execution_sprint_tracks_real_ui_gates() -> None:
    sprint = build_p0_host_execution_sprint()

    assert sprint["target_hosts"] == ["Codex", "Claude Code"]
    assert sprint["execution_status"] == "manual_evidence_required"
    assert sprint["non_fabrication_policy"] == "Never mark a host passed without reviewer-observed real UI evidence."
    assert [item["gate"] for item in sprint["gate_matrix"][0]["gates"]] == [
        "first_10_minutes_replay",
        "manual_host_ui",
    ]
    assert all(
        host["operator_packet"].startswith("uv run python scripts/export_manual_host_acceptance_packet.py")
        for host in sprint["gate_matrix"]
    )
    assert (
        "uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md"
        in sprint["after_real_ui_commands"]
    )


def test_p0_host_execution_sprint_markdown_is_operator_focused() -> None:
    markdown = render_p0_host_execution_sprint_markdown(build_p0_host_execution_sprint())

    assert markdown.startswith("# P0 Host Execution Sprint\n")
    assert "Execution status: `manual_evidence_required`" in markdown
    assert "## Non-Fabrication Policy" in markdown
    assert "Never mark a host passed without reviewer-observed real UI evidence." in markdown
    assert "| Codex | `first_10_minutes_replay` | `blocked` |" in markdown
    assert "| Claude Code | `manual_host_ui` | `blocked` |" in markdown
    assert "## Stop Conditions" in markdown
    assert "Do not tag v1 RC while any P0 gate is missing or blocked." in markdown


def test_committed_p0_host_execution_sprint_is_current() -> None:
    sprint_path = Path("docs/P0_HOST_EXECUTION_SPRINT.md")

    assert sprint_path.read_text(encoding="utf-8") == render_p0_host_execution_sprint_markdown(
        build_p0_host_execution_sprint()
    )
    assert "[docs/P0_HOST_EXECUTION_SPRINT.md](docs/P0_HOST_EXECUTION_SPRINT.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_p0_host_execution_sprint_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "p0-host-execution-sprint.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_p0_host_execution_sprint.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# P0 Host Execution Sprint\n")
