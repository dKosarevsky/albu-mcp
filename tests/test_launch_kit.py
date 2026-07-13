from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_launch_kit import build_launch_kit, render_launch_kit_markdown


def test_launch_kit_contains_public_distribution_assets() -> None:
    kit = build_launch_kit()
    markdown = render_launch_kit_markdown(kit)

    assert kit["package"] == "albumentationsx-mcp"
    assert kit["version"] == "1.17.0"
    assert "https://pypi.org/project/albumentationsx-mcp/" in markdown
    assert "registry.modelcontextprotocol.io" in markdown
    assert "AlbumentationsX#289" in markdown
    assert "docs/assets/demo/contact_sheet.png" in markdown
    assert "inspect_dataset_quality" in markdown
    assert "docs/HOST_PROOF_SPRINT.md" in markdown
    assert "docs/HOST_PROOF_SPRINT_CHECKLIST.md" in markdown
    assert "docs/NETWORK_GROWTH_TRACKER.md" in markdown
    assert "docs/PUBLIC_ADOPTION_LOOP.md" in markdown
    assert "dataset-health.yml" in markdown


def test_committed_launch_kit_is_current() -> None:
    kit_path = Path("docs/LAUNCH_KIT.md")

    assert kit_path.read_text(encoding="utf-8") == render_launch_kit_markdown(build_launch_kit())
    assert "[docs/LAUNCH_KIT.md](docs/LAUNCH_KIT.md)" in Path("README.md").read_text(encoding="utf-8")


def test_launch_kit_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "launch-kit.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_launch_kit.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# AlbumentationsX MCP Launch Kit\n")
    assert "Short Launch Copy" in content
