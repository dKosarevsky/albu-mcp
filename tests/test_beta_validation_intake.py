from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_beta_validation_intake import (
    build_beta_validation_intake,
    render_beta_validation_intake_markdown,
)


def test_beta_validation_intake_builds_missing_workflow_lanes() -> None:
    intake = build_beta_validation_intake()

    assert intake["intake_status"] == "collecting_beta_validation"
    assert intake["validation_status"] == "manual_beta_required"
    assert intake["summary"] == {
        "workflow_count": 3,
        "missing_workflow_count": 3,
        "recorded_workflow_count": 0,
        "target_beta_records": 5,
    }
    assert [lane["workflow_id"] for lane in intake["intake_lanes"]] == [
        "robustness_distortion_variants",
        "noisy_preview_tuning",
        "dataset_health_before_training",
    ]
    assert intake["intake_lanes"][0]["issue_template"] == ".github/ISSUE_TEMPLATE/workflow-feedback.yml"
    assert intake["intake_lanes"][2]["issue_template"] == ".github/ISSUE_TEMPLATE/dataset-health.yml"
    assert all("artifact_ref" in lane["required_record_fields"] for lane in intake["intake_lanes"])
    assert all("record_beta_validation.py" in lane["validation_record_command"] for lane in intake["intake_lanes"])


def test_beta_validation_intake_markdown_is_privacy_safe() -> None:
    markdown = render_beta_validation_intake_markdown(build_beta_validation_intake())

    assert markdown.startswith("# Beta Validation Intake\n")
    assert "Intake status: `collecting_beta_validation`" in markdown
    assert "Do not request or commit private datasets" in markdown
    assert "| `dataset_health_before_training` | `missing` | `.github/ISSUE_TEMPLATE/dataset-health.yml` |" in markdown
    assert "Record at least one privacy-safe attempt for every beta workflow" in markdown
    assert "validate_beta_validation_records.py" in markdown


def test_committed_beta_validation_intake_is_current() -> None:
    intake_path = Path("docs/BETA_VALIDATION_INTAKE.md")

    assert intake_path.read_text(encoding="utf-8") == render_beta_validation_intake_markdown(
        build_beta_validation_intake()
    )
    assert "[docs/BETA_VALIDATION_INTAKE.md](docs/BETA_VALIDATION_INTAKE.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_beta_validation_intake_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "beta-validation-intake.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_beta_validation_intake.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Beta Validation Intake\n")
