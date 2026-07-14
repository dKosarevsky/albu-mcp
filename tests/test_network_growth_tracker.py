from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_network_growth_tracker import build_network_growth_tracker, render_network_growth_tracker_markdown


def test_network_growth_tracker_contains_channels_and_next_actions() -> None:
    tracker = build_network_growth_tracker()
    markdown = render_network_growth_tracker_markdown(tracker)

    assert tracker["package"] == "albumentationsx-mcp"
    assert {channel["id"] for channel in tracker["channels"]} == {
        "pypi",
        "official_registry",
        "glama",
        "upstream_docs",
        "github_feedback",
    }
    assert "https://pypi.org/project/albumentationsx-mcp/" in markdown
    assert "registry.modelcontextprotocol.io" in markdown
    assert "https://glama.ai/mcp/servers/dKosarevsky/albu-mcp" in markdown
    assert "docs/LAUNCH_KIT.md" in markdown
    assert "docs/PUBLIC_ADOPTION_LOOP.md" in markdown
    assert "docs/HOST_PROOF_SPRINT_CHECKLIST.md" in markdown
    assert "dataset-health.yml" in markdown
    assert "export_public_adoption_loop.py" in markdown


def test_committed_network_growth_tracker_is_current() -> None:
    tracker_path = Path("docs/NETWORK_GROWTH_TRACKER.md")

    assert tracker_path.read_text(encoding="utf-8") == render_network_growth_tracker_markdown(
        build_network_growth_tracker()
    )
    assert "[NETWORK_GROWTH_TRACKER.md](NETWORK_GROWTH_TRACKER.md)" in Path("docs/INDEX.md").read_text(encoding="utf-8")
    assert "docs/NETWORK_GROWTH_TRACKER.md" in Path("docs/NETWORK_GROWTH.md").read_text(encoding="utf-8")


def test_network_growth_tracker_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "network-growth-tracker.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_network_growth_tracker.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# Network Growth Tracker\n")
    assert "Official MCP Registry" in content
