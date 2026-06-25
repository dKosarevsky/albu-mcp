from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.export_v1_decision_report import build_v1_decision_report, render_v1_decision_report_markdown


def test_v1_decision_report_holds_v1_until_host_evidence_passes() -> None:
    report = build_v1_decision_report()

    assert report["decision"] == "hold_v1"
    assert report["release_candidate_allowed"] is False
    assert report["ready_for_v1"] is False
    assert report["host_blocker_count"] == 8
    assert "manual_host_ui_pending" in report["blocking_codes"]
    assert "first_10_minutes_replay_pending" in report["blocking_codes"]
    assert "Do not cut v1 from synthetic or generated host evidence." in report["decision_policy"]
    assert "Run host evidence sprint queue and record real host UI evidence." in report["required_before_v1"]
    assert "uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md" in report[
        "next_decision_checks"
    ]


def test_v1_decision_report_markdown_is_clear() -> None:
    markdown = render_v1_decision_report_markdown(build_v1_decision_report())

    assert markdown.startswith("# V1 Decision Report\n")
    assert "Decision: `hold_v1`" in markdown
    assert "Release candidate allowed: `false`" in markdown
    assert "Host blocker count: `8`" in markdown
    assert "## Required Before V1" in markdown
    assert "Run host evidence sprint queue and record real host UI evidence." in markdown
    assert "## Non-Goals" in markdown
    assert "Do not reduce the supported host set only to make the gate pass." in markdown


def test_v1_decision_report_cli_outputs_json_and_markdown(tmp_path: Path) -> None:
    json_result = subprocess.run(
        [sys.executable, "scripts/export_v1_decision_report.py", "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(json_result.stdout)["decision"] == "hold_v1"

    output_path = tmp_path / "v1-decision.md"
    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_v1_decision_report.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Decision: `hold_v1`" in output_path.read_text(encoding="utf-8")


def test_committed_v1_decision_report_is_current() -> None:
    report_path = Path("docs/V1_DECISION_REPORT.md")

    assert report_path.read_text(encoding="utf-8") == render_v1_decision_report_markdown(
        build_v1_decision_report()
    )
    assert "[docs/V1_DECISION_REPORT.md](docs/V1_DECISION_REPORT.md)" in Path("README.md").read_text(encoding="utf-8")
