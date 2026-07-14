from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_adoption_triage_report import build_adoption_triage_report, render_adoption_triage_report_markdown


def test_adoption_triage_report_is_privacy_safe_and_actionable() -> None:
    report = build_adoption_triage_report()
    markdown = render_adoption_triage_report_markdown(report)

    assert report["telemetry_policy"] == "No automatic telemetry; use explicit GitHub issues and redacted artifacts."
    assert {metric["id"] for metric in report["manual_metrics"]} == {
        "host_acceptance_runs",
        "first_run_failures",
        "review_feedback_tags",
        "dataset_health_findings",
        "release_response_items",
    }
    assert ".github/ISSUE_TEMPLATE/host-acceptance.yml" in report["intake_templates"]
    assert ".github/ISSUE_TEMPLATE/workflow-feedback.yml" in report["intake_templates"]
    assert ".github/ISSUE_TEMPLATE/dataset-health.yml" in report["intake_templates"]
    assert "weekly triage" in markdown.lower()
    assert "interpret_preview_feedback" in markdown
    assert "dataset_unknown_category_annotations" in markdown


def test_committed_adoption_triage_report_is_current() -> None:
    report_path = Path("docs/ADOPTION_TRIAGE_REPORT.md")

    assert report_path.read_text(encoding="utf-8") == render_adoption_triage_report_markdown(
        build_adoption_triage_report()
    )
    assert "[ADOPTION_TRIAGE_REPORT.md](ADOPTION_TRIAGE_REPORT.md)" in Path("docs/INDEX.md").read_text(encoding="utf-8")
    assert "docs/ADOPTION_TRIAGE_REPORT.md" in Path("docs/PUBLIC_ADOPTION_LOOP.md").read_text(encoding="utf-8")


def test_adoption_triage_report_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "adoption-triage-report.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_adoption_triage_report.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# Adoption Triage Report\n")
    assert "No automatic telemetry" in content
