from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_host_evidence_capture_kit import (
    build_host_evidence_capture_kit,
    render_host_evidence_capture_kit_markdown,
)


def test_host_evidence_capture_kit_targets_blocked_p0_hosts_without_passing_evidence() -> None:
    kit = build_host_evidence_capture_kit()

    assert kit["kit_status"] == "operator_capture_required"
    assert kit["non_fabrication_policy"] == "Record passed only after a reviewer observes the real MCP host UI flow."
    assert kit["target_hosts"] == ["Claude Code"]
    assert kit["summary"]["blocked_gate_count"] == 2
    assert kit["summary"]["passed_gate_count"] == 2
    assert all(lane["capture_status"] == "blocked_until_operator_run" for lane in kit["capture_lanes"])
    assert "uv run python scripts/check_host_setup_probe.py --live --format json" in kit["pre_capture_commands"]


def test_host_evidence_capture_kit_markdown_is_operator_ready() -> None:
    markdown = render_host_evidence_capture_kit_markdown(build_host_evidence_capture_kit())

    assert markdown.startswith("# Host Evidence Capture Kit\n")
    assert "Kit status: `operator_capture_required`" in markdown
    assert "`scripts/record_host_manual_run.py`" in markdown
    assert "Do not record `passed` from generated smoke output." in markdown
    assert "`Claude Code`" in markdown


def test_committed_host_evidence_capture_kit_is_current() -> None:
    path = Path("docs/HOST_EVIDENCE_CAPTURE_KIT.md")

    assert path.read_text(encoding="utf-8") == render_host_evidence_capture_kit_markdown(
        build_host_evidence_capture_kit()
    )


def test_host_evidence_capture_kit_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "host-evidence-capture-kit.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_host_evidence_capture_kit.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Host Evidence Capture Kit\n")
