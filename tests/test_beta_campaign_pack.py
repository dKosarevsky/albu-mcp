from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_beta_campaign_pack import build_beta_campaign_pack, render_beta_campaign_pack_markdown


def test_beta_campaign_pack_is_ready_to_invite_without_claiming_feedback() -> None:
    pack = build_beta_campaign_pack()

    assert pack["campaign_status"] == "ready_to_invite"
    assert pack["feedback_status"] == "waiting_for_beta_signal"
    assert pack["privacy_guard"] == "Do not request private datasets, raw images, private paths, or credentials."
    assert pack["target_beta_records"] == 5
    assert [workflow["workflow_id"] for workflow in pack["workflow_cards"]] == [
        "robustness_distortion_variants",
        "noisy_preview_tuning",
        "dataset_health_before_training",
    ]
    assert all("record_beta_feedback.py" in workflow["record_command"] for workflow in pack["workflow_cards"])


def test_beta_campaign_pack_markdown_contains_copyable_outreach_and_commands() -> None:
    markdown = render_beta_campaign_pack_markdown(build_beta_campaign_pack())

    assert markdown.startswith("# Beta Campaign Pack\n")
    assert "Campaign status: `ready_to_invite`" in markdown
    assert "Feedback status: `waiting_for_beta_signal`" in markdown
    assert "Do not request private datasets, raw images, private paths, or credentials." in markdown
    assert "## Outreach Copy" in markdown
    assert "## Workflow Cards" in markdown
    assert "scripts/record_beta_feedback.py" in markdown


def test_committed_beta_campaign_pack_is_current() -> None:
    pack_path = Path("docs/BETA_CAMPAIGN_PACK.md")

    assert pack_path.read_text(encoding="utf-8") == render_beta_campaign_pack_markdown(build_beta_campaign_pack())
    assert "[docs/BETA_CAMPAIGN_PACK.md](docs/BETA_CAMPAIGN_PACK.md)" in Path("README.md").read_text(encoding="utf-8")


def test_beta_campaign_pack_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "beta-campaign-pack.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_beta_campaign_pack.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Beta Campaign Pack\n")
