from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_host_ux_packets import build_host_ux_packets, render_host_ux_packets_markdown


def test_host_ux_packets_cover_all_hosts_and_review_agent_tools() -> None:
    packets = build_host_ux_packets()
    markdown = render_host_ux_packets_markdown(packets)

    assert [packet["host"] for packet in packets["hosts"]] == ["Claude Desktop", "Claude Code", "Cursor", "Codex"]
    assert all("run_host_smoke_check" in packet["expected_tools"] for packet in packets["hosts"])
    assert all("interpret_preview_feedback" in packet["expected_tools"] for packet in packets["hosts"])
    assert all("plan_preview_review" in packet["expected_tools"] for packet in packets["hosts"])
    assert "claude mcp add-json" in markdown
    assert "[mcp_servers.albumentationsx]" in markdown
    assert "Refresh MCP discovery" in markdown


def test_committed_host_ux_packets_are_current() -> None:
    packet_path = Path("docs/HOST_UX_PACKETS.md")

    assert packet_path.read_text(encoding="utf-8") == render_host_ux_packets_markdown(build_host_ux_packets())
    assert "[HOST_UX_PACKETS.md](HOST_UX_PACKETS.md)" in Path("docs/INDEX.md").read_text(encoding="utf-8")
    assert "docs/HOST_UX_PACKETS.md" in Path("docs/HOST_MATRIX.md").read_text(encoding="utf-8")


def test_host_ux_packets_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "host-ux-packets.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_host_ux_packets.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# Host UX Packets\n")
    assert "Claude Desktop" in content
