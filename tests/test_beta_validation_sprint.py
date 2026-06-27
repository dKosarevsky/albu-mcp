from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_beta_validation_sprint import build_beta_validation_sprint, render_beta_validation_sprint_markdown


def test_beta_validation_sprint_schedules_all_beta_workflows() -> None:
    sprint = build_beta_validation_sprint()

    assert sprint["validation_status"] == "manual_beta_required"
    assert sprint["privacy_policy"] == "Collect workflow symptoms and redacted artifacts, never private datasets."
    assert [slot["workflow_id"] for slot in sprint["participant_slots"]] == [
        "robustness_distortion_variants",
        "noisy_preview_tuning",
        "dataset_health_before_training",
    ]
    assert (
        sprint["minimum_signal"]
        == "At least one real user attempt per beta workflow before product-depth reprioritization."
    )
    assert "review_agent_v3_gap" in sprint["triage_buckets"]
    assert "Convert repeated beta reports into tests before changing behavior." in sprint["weekly_cadence"]


def test_beta_validation_sprint_markdown_is_researcher_ready() -> None:
    markdown = render_beta_validation_sprint_markdown(build_beta_validation_sprint())

    assert markdown.startswith("# Beta Validation Sprint\n")
    assert "Validation status: `manual_beta_required`" in markdown
    assert "## Participant Slots" in markdown
    assert "### noisy_preview_tuning" in markdown
    assert "Whether the revised candidate became acceptable" in markdown
    assert "## Exit Criteria" in markdown
    assert "No private datasets, tokens, screenshots, or full host logs are collected." in markdown


def test_committed_beta_validation_sprint_is_current() -> None:
    sprint_path = Path("docs/BETA_VALIDATION_SPRINT.md")

    assert sprint_path.read_text(encoding="utf-8") == render_beta_validation_sprint_markdown(
        build_beta_validation_sprint()
    )
    assert "[docs/BETA_VALIDATION_SPRINT.md](docs/BETA_VALIDATION_SPRINT.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_beta_validation_sprint_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "beta-validation-sprint.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_beta_validation_sprint.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Beta Validation Sprint\n")
