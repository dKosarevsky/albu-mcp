from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_evidence_first_cycle_report import (
    build_evidence_first_cycle_report,
    render_evidence_first_cycle_report_markdown,
)


def test_evidence_first_cycle_report_stops_at_blocked_iteration_one() -> None:
    report = build_evidence_first_cycle_report()

    assert report["cycle_status"] == "blocked_before_rc"
    assert report["completed_point_count"] == 5
    assert report["rc_decision"] == "hold_rc"
    assert report["publish_allowed"] is False
    assert report["iteration_execution"] == {
        "requested_iteration_count": 100,
        "executed_iteration_count": 1,
        "stopped_at_iteration": 1,
        "stop_reason": "current_priority_gate_blocked",
    }
    assert report["blocked_reasons"] == [
        "p0_host_evidence_missing_or_blocked",
        "beta_validation_records_missing",
    ]


def test_evidence_first_cycle_report_markdown_documents_non_fabrication() -> None:
    markdown = render_evidence_first_cycle_report_markdown(build_evidence_first_cycle_report())

    assert markdown.startswith("# Evidence First Cycle Report\n")
    assert "Cycle status: `blocked_before_rc`" in markdown
    assert "No `passed` P0 evidence or beta record was fabricated." in markdown
    assert "100 requested iterations stopped at iteration `1`" in markdown
    assert "`current_priority_gate_blocked`" in markdown


def test_committed_evidence_first_cycle_report_is_current() -> None:
    doc_path = Path("docs/EVIDENCE_FIRST_CYCLE_REPORT.md")

    assert doc_path.read_text(encoding="utf-8") == render_evidence_first_cycle_report_markdown(
        build_evidence_first_cycle_report()
    )


def test_evidence_first_cycle_report_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "evidence-first-cycle-report.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_evidence_first_cycle_report.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Evidence First Cycle Report\n")
