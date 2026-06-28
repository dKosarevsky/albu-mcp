from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_p0_host_runbook import build_p0_host_runbook, render_p0_host_runbook_markdown


def test_p0_host_runbook_contains_only_p0_hosts() -> None:
    runbook = build_p0_host_runbook()

    assert runbook["target_hosts"] == ["Codex", "Claude Code"]
    assert [item["host"] for item in runbook["run_queue"]] == ["Codex", "Claude Code"]
    assert all(item["priority"] == "p0" for item in runbook["run_queue"])
    assert all(item["next_action"] == "triage_blocker" for item in runbook["run_queue"])
    assert "Cursor" not in {item["host"] for item in runbook["run_queue"]}
    assert "Claude Desktop" not in {item["host"] for item in runbook["run_queue"]}
    assert (
        "uv run python scripts/export_manual_host_acceptance_packet.py --host Codex"
        in runbook["run_queue"][0]["packet_command"]
    )
    assert (
        "uv run python scripts/record_host_manual_run.py --host Codex"
        in runbook["run_queue"][0]["manual_record_command"]
    )
    assert "--kind first-10-minutes --host Codex" in runbook["run_queue"][0]["first_10_minutes_record_command"]


def test_p0_host_runbook_markdown_is_short_and_actionable() -> None:
    markdown = render_p0_host_runbook_markdown(build_p0_host_runbook())

    assert markdown.startswith("# P0 Host Runbook\n")
    assert "Target hosts: `Codex, Claude Code`" in markdown
    assert "## P0 Queue" in markdown
    assert "| 1 | Codex | `triage_blocker` |" in markdown
    assert "| 2 | Claude Code | `triage_blocker` |" in markdown
    assert "## Record Commands" in markdown
    assert "record_host_manual_run.py --host Codex" in markdown
    assert "record_host_manual_run.py --kind first-10-minutes --host Codex" in markdown
    assert "Cursor" not in markdown
    assert "Claude Desktop" not in markdown


def test_committed_p0_host_runbook_is_current() -> None:
    runbook_path = Path("docs/P0_HOST_RUNBOOK.md")

    assert runbook_path.read_text(encoding="utf-8") == render_p0_host_runbook_markdown(build_p0_host_runbook())
    assert "[docs/P0_HOST_RUNBOOK.md](docs/P0_HOST_RUNBOOK.md)" in Path("README.md").read_text(encoding="utf-8")


def test_p0_host_runbook_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "p0-host-runbook.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_p0_host_runbook.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# P0 Host Runbook\n")
