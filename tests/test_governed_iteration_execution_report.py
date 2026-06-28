from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_governed_iteration_execution_report import (
    build_governed_iteration_execution_report,
    render_governed_iteration_execution_report_markdown,
)


def test_governed_iteration_execution_report_stops_after_first_blocked_iteration() -> None:
    report = build_governed_iteration_execution_report()

    assert report["requested_iteration_count"] == 100
    assert report["executed_iteration_count"] == 1
    assert report["stopped_at_iteration"] == 1
    assert report["stop_reason"] == "current_priority_gate_blocked"
    assert report["completed_path_count"] == 3
    assert report["completed_plan_point_count"] == 7


def test_governed_iteration_execution_report_markdown_explains_stop() -> None:
    markdown = render_governed_iteration_execution_report_markdown(build_governed_iteration_execution_report())

    assert markdown.startswith("# Governed 100-Iteration Execution Report\n")
    assert "Requested iterations: `100`" in markdown
    assert "Executed iterations: `1`" in markdown
    assert "`current_priority_gate_blocked`" in markdown
    assert "No blind implementation loop was executed." in markdown


def test_committed_governed_iteration_execution_report_is_current() -> None:
    path = Path("docs/GOVERNED_100_ITERATION_REPORT.md")

    assert path.read_text(encoding="utf-8") == render_governed_iteration_execution_report_markdown(
        build_governed_iteration_execution_report()
    )


def test_governed_iteration_execution_report_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "governed-100-iteration-report.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_governed_iteration_execution_report.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Governed 100-Iteration Execution Report\n")
