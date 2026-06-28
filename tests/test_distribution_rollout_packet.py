from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_distribution_rollout_packet import (
    build_distribution_rollout_packet,
    render_distribution_rollout_packet_markdown,
)


def test_distribution_rollout_packet_blocks_public_rollout_until_rc() -> None:
    packet = build_distribution_rollout_packet()

    assert packet["rollout_status"] == "blocked_until_rc_distribution"
    assert packet["public_announcement_allowed"] is False
    assert packet["distribution_status"] == "blocked_until_rc_cutover"
    assert packet["release_tag"] == "vX.Y.Z-rc.1"
    assert [channel["id"] for channel in packet["rollout_channels"]] == [
        "pypi",
        "github_release",
        "official_registry",
        "upstream_docs",
        "github_feedback",
    ]
    assert packet["announcement_policy"] == "Announce only after RC tag, release, package, and visibility checks pass."
    assert packet["next_actions"][0] == "Complete P0 host evidence and RC cutover before public rollout."


def test_distribution_rollout_packet_markdown_is_channel_focused() -> None:
    markdown = render_distribution_rollout_packet_markdown(build_distribution_rollout_packet())

    assert markdown.startswith("# Distribution Rollout Packet\n")
    assert "Rollout status: `blocked_until_rc_distribution`" in markdown
    assert "Public announcement allowed: `false`" in markdown
    assert "## Rollout Channels" in markdown
    assert "PyPI" in markdown
    assert "GitHub Release" in markdown
    assert "Official MCP Registry" in markdown
    assert "AlbumentationsX upstream docs" in markdown


def test_committed_distribution_rollout_packet_is_current() -> None:
    packet_path = Path("docs/DISTRIBUTION_ROLLOUT_PACKET.md")

    assert packet_path.read_text(encoding="utf-8") == render_distribution_rollout_packet_markdown(
        build_distribution_rollout_packet()
    )
    assert "[docs/DISTRIBUTION_ROLLOUT_PACKET.md](docs/DISTRIBUTION_ROLLOUT_PACKET.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_distribution_rollout_packet_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "distribution-rollout-packet.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_distribution_rollout_packet.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Distribution Rollout Packet\n")
