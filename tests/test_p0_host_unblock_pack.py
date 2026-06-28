from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_p0_host_unblock_pack import build_p0_host_unblock_pack, render_p0_host_unblock_pack_markdown


def test_p0_host_unblock_pack_maps_blocked_hosts_to_recovery_lanes() -> None:
    pack = build_p0_host_unblock_pack()

    assert pack["pack_status"] == "blocked_evidence_triage_required"
    assert pack["rc_reopen_allowed"] is False
    assert pack["summary"] == {
        "lane_count": 4,
        "blocked_lane_count": 4,
        "missing_lane_count": 0,
    }
    assert {lane["host"] for lane in pack["recovery_lanes"]} == {"Codex", "Claude Code"}
    assert {lane["failure_class"] for lane in pack["recovery_lanes"]} == {
        "codex_tool_call_cancelled",
        "claude_cli_missing",
    }
    assert all(lane["acceptance_criterion"].startswith("Replace this blocked record") for lane in pack["recovery_lanes"])
    assert all("record_host_manual_run.py" in lane["record_command"] for lane in pack["recovery_lanes"])


def test_p0_host_unblock_pack_markdown_is_operator_focused() -> None:
    markdown = render_p0_host_unblock_pack_markdown(build_p0_host_unblock_pack())

    assert markdown.startswith("# P0 Host Evidence Unblock Pack\n")
    assert "Pack status: `blocked_evidence_triage_required`" in markdown
    assert "RC reopen allowed: `false`" in markdown
    assert "| Codex | `first_10_minutes_replay` | `codex_tool_call_cancelled` |" in markdown
    assert "| Claude Code | `manual_host_ui` | `claude_cli_missing` |" in markdown
    assert "Do not mark any P0 gate as passed until a real host run completes" in markdown


def test_committed_p0_host_unblock_pack_is_current() -> None:
    pack_path = Path("docs/P0_HOST_UNBLOCK_PACK.md")

    assert pack_path.read_text(encoding="utf-8") == render_p0_host_unblock_pack_markdown(
        build_p0_host_unblock_pack()
    )


def test_p0_host_unblock_pack_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "p0-host-unblock-pack.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_p0_host_unblock_pack.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# P0 Host Evidence Unblock Pack\n")
