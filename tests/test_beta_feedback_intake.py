from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_beta_feedback_intake import build_beta_feedback_intake, render_beta_feedback_intake_markdown


def test_beta_feedback_intake_covers_beta_workflows() -> None:
    intake = build_beta_feedback_intake()

    assert [item["workflow_id"] for item in intake["workflow_intake"]] == [
        "robustness_distortion_variants",
        "noisy_preview_tuning",
        "dataset_health_before_training",
    ]
    assert intake["privacy_policy"] == "Collect workflow symptoms and redacted artifacts, never private datasets."
    assert intake["workflow_intake"][1]["expected_feedback"] == [
        "Free-form user note",
        "Structured feedback tags",
        "Recommended next MCP tool",
        "Whether the revised candidate became acceptable",
    ]
    assert "review_agent_v3_gap" in intake["triage_buckets"]
    assert "dataset_quality_gap" in intake["triage_buckets"]
    assert "Convert repeated reports into tests before changing behavior." in intake["weekly_loop"]


def test_beta_feedback_intake_markdown_is_copyable() -> None:
    markdown = render_beta_feedback_intake_markdown(build_beta_feedback_intake())

    assert markdown.startswith("# Beta Feedback Intake\n")
    assert "## Privacy Policy" in markdown
    assert "### noisy_preview_tuning" in markdown
    assert "Free-form user note" in markdown
    assert "## Triage Buckets" in markdown
    assert "`review_agent_v3_gap`" in markdown
    assert "## Weekly Loop" in markdown
    assert "Convert repeated reports into tests before changing behavior." in markdown


def test_committed_beta_feedback_intake_is_current() -> None:
    intake_path = Path("docs/BETA_FEEDBACK_INTAKE.md")

    assert intake_path.read_text(encoding="utf-8") == render_beta_feedback_intake_markdown(build_beta_feedback_intake())
    assert "[docs/BETA_FEEDBACK_INTAKE.md](docs/BETA_FEEDBACK_INTAKE.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_beta_feedback_intake_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "beta-feedback-intake.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_beta_feedback_intake.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Beta Feedback Intake\n")
