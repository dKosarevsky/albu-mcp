from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_beta_campaign_execution import (
    build_beta_campaign_execution,
    render_beta_campaign_execution_markdown,
)


def test_beta_campaign_execution_keeps_manual_validation_required() -> None:
    execution = build_beta_campaign_execution()

    assert execution["execution_status"] == "ready_to_invite"
    assert execution["validation_status"] == "manual_beta_required"
    assert execution["summary"] == {
        "workflow_count": 3,
        "missing_workflow_count": 3,
        "recorded_workflow_count": 0,
        "target_beta_records": 5,
    }
    assert [lane["workflow_id"] for lane in execution["invite_lanes"]] == [
        "robustness_distortion_variants",
        "noisy_preview_tuning",
        "dataset_health_before_training",
    ]
    assert all(lane["next_action"] == "invite_beta_user" for lane in execution["invite_lanes"])
    assert all("record_beta_validation.py" in lane["validation_record_command"] for lane in execution["invite_lanes"])


def test_beta_campaign_execution_markdown_is_copyable() -> None:
    markdown = render_beta_campaign_execution_markdown(build_beta_campaign_execution())

    assert markdown.startswith("# Beta Campaign Execution\n")
    assert "Execution status: `ready_to_invite`" in markdown
    assert "Validation status: `manual_beta_required`" in markdown
    assert "| `robustness_distortion_variants` | `missing` | `invite_beta_user` |" in markdown
    assert "Do not request private datasets, raw images, private paths, or credentials." in markdown
    assert "record_beta_validation.py" in markdown


def test_committed_beta_campaign_execution_is_current() -> None:
    execution_path = Path("docs/BETA_CAMPAIGN_EXECUTION.md")

    assert execution_path.read_text(encoding="utf-8") == render_beta_campaign_execution_markdown(
        build_beta_campaign_execution()
    )


def test_beta_campaign_execution_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "beta-campaign-execution.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_beta_campaign_execution.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Beta Campaign Execution\n")
