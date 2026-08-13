from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_launch_kit import (
    build_campaign_launch_pack,
    build_launch_kit,
    render_campaign_launch_pack_markdown,
    render_launch_kit_markdown,
)


def test_launch_kit_contains_public_distribution_assets() -> None:
    kit = build_launch_kit()
    markdown = render_launch_kit_markdown(kit)

    assert kit["package"] == "albumentationsx-mcp"
    assert kit["version"] == "1.21.1"
    assert "https://pypi.org/project/albumentationsx-mcp/" in markdown
    assert "registry.modelcontextprotocol.io" in markdown
    assert "AlbumentationsX#289" in markdown
    assert "docs/assets/demo/contact_sheet.png" in markdown
    assert "inspect_dataset_quality" in markdown
    assert "docs/HOST_PROOF_SPRINT.md" in markdown
    assert "docs/HOST_PROOF_SPRINT_CHECKLIST.md" in markdown
    assert "docs/STATUS.md" in markdown
    assert "docs/V1_LAUNCH_REPORT.md" not in kit["proof_docs"]
    assert "docs/NETWORK_GROWTH_TRACKER.md" in markdown
    assert "docs/PUBLIC_ADOPTION_LOOP.md" in markdown
    assert "dataset-health.yml" in markdown
    assert kit["lifecycle"]["release_health"]["status"] == "unknown"
    assert kit["lifecycle"]["host_evidence"]["status"] == "partial"
    assert kit["lifecycle"]["adoption_experiment"]["status"] == "measuring"
    assert "Ready for v1" not in markdown
    assert "Release health: `unknown`" in markdown
    assert "Adoption experiment: `measuring`" in markdown


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
        assert f"utm_campaign={campaign['id']}" in campaign["destination_url"]
        assert campaign["success_signal"]

    classification = next(campaign for campaign in kit["campaigns"] if campaign["id"] == "classification-robustness")
    assert classification["destination_url"].startswith(
        "https://github.com/dKosarevsky/albu-mcp/blob/main/docs/use-cases/CLASSIFICATION_ROBUSTNESS.md"
    )
    assert all(
        campaign["destination_url"].startswith("https://albumentations.ai/docs/integrations/mcp/")
        for campaign in kit["campaigns"]
        if campaign["id"] != "classification-robustness"
    )

    markdown = render_launch_kit_markdown(kit)
    assert "## Audience Campaigns" in markdown
    assert "Publication: `manual only`" in markdown
    assert "scripts/export_growth_report.py" in markdown
    assert "fixed for 14 days" in markdown
    assert "Three voluntary accepted-after-adjustment reports from three distinct submitters" in markdown
    assert "scripts/export_campaign_activation_report.py" in markdown


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


def test_classification_launch_pack_has_one_destination_and_bounded_channel_copy() -> None:
    pack = build_campaign_launch_pack("classification-robustness")
    markdown = render_campaign_launch_pack_markdown(pack)

    assert pack["id"] == "classification-robustness"
    assert pack["use_case_url"] == (
        "https://github.com/dKosarevsky/albu-mcp/blob/main/docs/use-cases/CLASSIFICATION_ROBUSTNESS.md"
    )
    assert {post["channel"] for post in pack["posts"]} == {
        "albumentations-discord",
        "x-twitter",
        "generic-community",
    }
    assert all(pack["use_case_url"] in post["copy"] for post in pack["posts"])
    x_post = next(post for post in pack["posts"] if post["channel"] == "x-twitter")
    assert len(x_post["copy"]) <= 280
    assert "No telemetry" in markdown
    assert "manual only" in markdown
    assert "accepted-after-adjustment" in markdown


def test_committed_classification_launch_pack_is_current() -> None:
    path = Path("docs/campaigns/CLASSIFICATION_ROBUSTNESS_LAUNCH.md")

    assert path.read_text(encoding="utf-8") == render_campaign_launch_pack_markdown(
        build_campaign_launch_pack("classification-robustness")
    )
    assert "[campaigns/CLASSIFICATION_ROBUSTNESS_LAUNCH.md]" in Path("docs/INDEX.md").read_text(encoding="utf-8")


def test_launch_kit_cli_writes_focused_campaign_pack(tmp_path: Path) -> None:
    output_path = tmp_path / "classification-launch.md"

    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "scripts/export_launch_kit.py",
            "--campaign",
            "classification-robustness",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Classification Robustness Launch Pack\n")
