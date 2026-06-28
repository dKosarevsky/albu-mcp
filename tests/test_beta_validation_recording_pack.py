from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_beta_validation_recording_pack import (
    build_beta_validation_recording_pack,
    render_beta_validation_recording_pack_markdown,
)


def test_beta_validation_recording_pack_keeps_manual_records_required() -> None:
    pack = build_beta_validation_recording_pack()

    assert pack["recording_status"] == "manual_records_required"
    assert pack["validation_status"] == "manual_beta_required"
    assert pack["summary"] == {
        "record_count": 0,
        "workflow_count": 3,
        "missing_workflow_count": 3,
        "covered_workflow_count": 0,
        "private_data_record_count": 0,
    }
    assert pack["accepted_statuses"] == ["passed", "blocked", "needs_followup"]
    assert [lane["workflow_id"] for lane in pack["recording_lanes"]] == [
        "robustness_distortion_variants",
        "noisy_preview_tuning",
        "dataset_health_before_training",
    ]
    assert all("record_beta_validation.py" in lane["record_command"] for lane in pack["recording_lanes"])


def test_beta_validation_recording_pack_markdown_is_privacy_safe() -> None:
    markdown = render_beta_validation_recording_pack_markdown(build_beta_validation_recording_pack())

    assert markdown.startswith("# Beta Validation Recording Pack\n")
    assert "Recording status: `manual_records_required`" in markdown
    assert "Record only real beta attempts" in markdown
    assert "`needs_followup`" in markdown
    assert "| `dataset_health_before_training` | `missing` | `.github/ISSUE_TEMPLATE/dataset-health.yml` |" in markdown
    assert "validate_beta_validation_records.py" in markdown


def test_committed_beta_validation_recording_pack_is_current() -> None:
    pack_path = Path("docs/BETA_VALIDATION_RECORDING_PACK.md")

    assert pack_path.read_text(encoding="utf-8") == render_beta_validation_recording_pack_markdown(
        build_beta_validation_recording_pack()
    )


def test_beta_validation_recording_pack_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "beta-validation-recording-pack.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_beta_validation_recording_pack.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Beta Validation Recording Pack\n")
