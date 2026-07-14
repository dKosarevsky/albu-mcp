from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_launch_kit import build_launch_kit, render_launch_kit_markdown


def test_launch_kit_contains_public_distribution_assets() -> None:
    kit = build_launch_kit()
    markdown = render_launch_kit_markdown(kit)

    assert kit["package"] == "albumentationsx-mcp"
    assert kit["version"] == "1.18.0"
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


def test_launch_kit_contains_three_measurable_audience_campaigns() -> None:
    kit = build_launch_kit()

    assert {campaign["id"] for campaign in kit["campaigns"]} == {
        "classification-robustness",
        "detection-bbox-safety",
        "segmentation-mask-safety",
    }
    for campaign in kit["campaigns"]:
        assert campaign["audience"]
        assert campaign["problem"]
        assert campaign["prompt"]
        assert campaign["artifact"]
        assert campaign["destination_url"].startswith("https://albumentations.ai/docs/integrations/mcp/")
        assert f"utm_campaign={campaign['id']}" in campaign["destination_url"]
        assert campaign["success_signal"]

    markdown = render_launch_kit_markdown(kit)
    assert "## Audience Campaigns" in markdown
    assert "Publication: `manual only`" in markdown
    assert "scripts/export_growth_report.py" in markdown


def test_committed_launch_kit_is_current() -> None:
    kit_path = Path("docs/LAUNCH_KIT.md")

    assert kit_path.read_text(encoding="utf-8") == render_launch_kit_markdown(build_launch_kit())
    assert "[LAUNCH_KIT.md](LAUNCH_KIT.md)" in Path("docs/INDEX.md").read_text(encoding="utf-8")


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
