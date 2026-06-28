from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_beta_validation_loop import build_beta_validation_loop, render_beta_validation_loop_markdown


def test_beta_validation_loop_requires_real_attempts_for_every_workflow() -> None:
    loop = build_beta_validation_loop()

    assert loop["loop_status"] == "manual_beta_required"
    assert loop["privacy_policy"] == "Collect workflow symptoms and redacted artifacts, never private datasets."
    assert loop["summary"] == {
        "workflow_count": 3,
        "record_count": 0,
        "covered_workflow_count": 0,
        "missing_workflow_count": 3,
    }
    assert loop["next_operator_action"] == "Recruit one real user attempt for each missing beta workflow."
    assert len(loop["workflow_lanes"]) == 3
    assert all(lane["status"] == "missing" for lane in loop["workflow_lanes"])


def test_beta_validation_loop_markdown_has_scriptable_recording_commands() -> None:
    markdown = render_beta_validation_loop_markdown(build_beta_validation_loop())

    assert markdown.startswith("# Beta Validation Loop\n")
    assert "Loop status: `manual_beta_required`" in markdown
    assert "`scripts/record_beta_validation.py`" in markdown
    assert "`docs/BETA_VALIDATION_RECORDS.json`" in markdown
    assert "No private datasets, tokens, screenshots, or full host logs are collected." in markdown


def test_committed_beta_validation_loop_is_current() -> None:
    doc_path = Path("docs/BETA_VALIDATION_LOOP.md")

    assert doc_path.read_text(encoding="utf-8") == render_beta_validation_loop_markdown(build_beta_validation_loop())
    assert "[docs/BETA_VALIDATION_LOOP.md](docs/BETA_VALIDATION_LOOP.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_beta_validation_loop_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "beta-validation-loop.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_beta_validation_loop.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Beta Validation Loop\n")
