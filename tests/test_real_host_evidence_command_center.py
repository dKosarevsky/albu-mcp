from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_real_host_evidence_command_center import (
    build_real_host_evidence_command_center,
    render_real_host_evidence_command_center_markdown,
)


def test_real_host_evidence_command_center_keeps_p0_manual_and_blocked() -> None:
    center = build_real_host_evidence_command_center()

    assert center["command_center_status"] == "blocked_until_real_host_runs"
    assert center["non_fabrication_policy"] == "Only reviewer-observed real MCP host UI runs can satisfy P0 gates."
    assert center["summary"]["blocked_gate_count"] == 2
    assert center["summary"]["passed_gate_count"] == 2
    assert center["next_operator_action"] == "Run the host setup probe live, then execute the first blocked host lane."
    assert center["blocked_hosts"] == ["Claude Code"]
    assert [lane["host"] for lane in center["host_lanes"]] == ["Claude Code"]
    assert "uv run python scripts/check_host_setup_probe.py --live --format json" in center["operator_commands"]


def test_real_host_evidence_command_center_markdown_points_to_recorders() -> None:
    markdown = render_real_host_evidence_command_center_markdown(build_real_host_evidence_command_center())

    assert markdown.startswith("# Real Host Evidence Command Center\n")
    assert "Command center status: `blocked_until_real_host_runs`" in markdown
    assert "Only reviewer-observed real MCP host UI runs can satisfy P0 gates." in markdown
    assert "`scripts/record_host_manual_run.py`" in markdown
    assert "`docs/P0_HOST_EVIDENCE_RECOVERY.md`" in markdown
    assert "`docs/HOST_SETUP_PROBE.md`" in markdown


def test_committed_real_host_evidence_command_center_is_current() -> None:
    doc_path = Path("docs/REAL_HOST_EVIDENCE_COMMAND_CENTER.md")

    assert doc_path.read_text(encoding="utf-8") == render_real_host_evidence_command_center_markdown(
        build_real_host_evidence_command_center()
    )
    assert "[REAL_HOST_EVIDENCE_COMMAND_CENTER.md](REAL_HOST_EVIDENCE_COMMAND_CENTER.md)" in Path(
        "docs/INDEX.md"
    ).read_text(encoding="utf-8")


def test_real_host_evidence_command_center_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "real-host-command-center.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_real_host_evidence_command_center.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Real Host Evidence Command Center\n")
