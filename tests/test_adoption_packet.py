from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_adoption_packet import build_adoption_packet, render_adoption_packet_markdown


def test_adoption_packet_contains_public_launch_copy() -> None:
    packet = build_adoption_packet()
    markdown = render_adoption_packet_markdown(packet)

    assert packet["package"] == "albumentationsx-mcp"
    assert packet["version"] == "1.17.1"
    assert "uvx --from albumentationsx-mcp albumentationsx-mcp" in markdown
    assert "MCP Registry" in markdown
    assert "Launch Kit" in markdown
    assert "AlbumentationsX#289" in markdown
    assert "inspect_dataset_quality" in markdown
    assert "build_review_packet" in markdown
    assert "render_preview_batch" in markdown
    assert "interpret_preview_feedback" in markdown
    assert "plan_preview_review" in markdown
    assert "export_preview_report" in markdown


def test_committed_adoption_packet_is_current() -> None:
    packet_path = Path("docs/ADOPTION_PACKET.md")

    assert packet_path.read_text(encoding="utf-8") == render_adoption_packet_markdown(build_adoption_packet())
    assert "[docs/ADOPTION_PACKET.md](docs/ADOPTION_PACKET.md)" in Path("README.md").read_text(encoding="utf-8")


def test_adoption_packet_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "adoption.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_adoption_packet.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# AlbumentationsX MCP Adoption Packet\n")
    assert "Claude Desktop" in content
    assert "Cursor" in content
    assert "Codex" in content
