from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_governed_iteration_execution_report import (
    build_governed_iteration_execution_report,
    render_governed_iteration_execution_report_markdown,
)


def test_governed_iteration_execution_report_stops_after_second_blocked_iteration() -> None:
    report = build_governed_iteration_execution_report()

    assert report["requested_iteration_count"] == 100
    assert report["executed_iteration_count"] == 2
    assert report["stopped_at_iteration"] == 2
    assert report["stop_reason"] == "current_priority_gate_blocked"
    assert report["completed_path_count"] == 10
    assert report["completed_plan_point_count"] == 10
    assert report["completed_plan_points"] == [
        "Added evidence execution-packet for host-specific real MCP runs.",
        "Added evidence artifact-doctor for artifact completeness and synthetic-only checks.",
        "Added beta trial-pack for privacy-safe external user handoffs.",
        "Added trust next and RC reopen rehearsal v2 report-only commands.",
        "Stopped 100 follow-up iterations at the blocked real-host and beta validation gates.",
        "Added evidence operator-packet for host-specific markdown/json operator artifacts.",
        "Added evidence validate-import for dry-run evidence import validation before record writes.",
        "Added beta intake-wizard for privacy-safe beta response capture.",
        "Added trust dashboard and RC candidate-packet report-only release views.",
        "Stopped the next 100 analogous implementation iterations at the same external evidence and beta gates.",
    ]


def test_governed_iteration_execution_report_markdown_explains_stop() -> None:
    markdown = render_governed_iteration_execution_report_markdown(build_governed_iteration_execution_report())

    assert markdown.startswith("# Governed 100-Iteration Execution Report\n")
    assert "Requested iterations: `100`" in markdown
    assert "Executed iterations: `2`" in markdown
    assert "`current_priority_gate_blocked`" in markdown
    assert "evidence execution-packet" in markdown
    assert "artifact-doctor" in markdown
    assert "beta trial-pack" in markdown
    assert "evidence operator-packet" in markdown
    assert "beta intake-wizard" in markdown
    assert "`p0_host_evidence_missing_or_blocked`" in markdown
    assert "RC reopen rehearsal v2" in markdown
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
