from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_beta_attempt_capture_kit import (
    build_beta_attempt_capture_kit,
    render_beta_attempt_capture_kit_markdown,
)


def test_beta_attempt_capture_kit_keeps_missing_workflows_manual() -> None:
    kit = build_beta_attempt_capture_kit()

    assert kit["kit_status"] == "manual_attempts_required"
    assert kit["records_path"] == "docs/BETA_VALIDATION_RECORDS.json"
    assert kit["summary"] == {
        "workflow_count": 3,
        "record_count": 0,
        "missing_workflow_count": 3,
    }
    assert len(kit["attempt_lanes"]) == 3
    assert all(lane["attempt_status"] == "missing" for lane in kit["attempt_lanes"])


def test_beta_attempt_capture_kit_markdown_documents_privacy_and_commands() -> None:
    markdown = render_beta_attempt_capture_kit_markdown(build_beta_attempt_capture_kit())

    assert markdown.startswith("# Beta Attempt Capture Kit\n")
    assert "Kit status: `manual_attempts_required`" in markdown
    assert "`scripts/record_beta_validation.py`" in markdown
    assert "Never collect private datasets, tokens, screenshots, or full host logs." in markdown
    assert "`robustness_distortion_variants`" in markdown


def test_committed_beta_attempt_capture_kit_is_current() -> None:
    path = Path("docs/BETA_ATTEMPT_CAPTURE_KIT.md")

    assert path.read_text(encoding="utf-8") == render_beta_attempt_capture_kit_markdown(
        build_beta_attempt_capture_kit()
    )


def test_beta_attempt_capture_kit_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "beta-attempt-capture-kit.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_beta_attempt_capture_kit.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Beta Attempt Capture Kit\n")
