from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_rc_release_decision_report import (
    build_rc_release_decision_report,
    render_rc_release_decision_report_markdown,
)


def test_rc_release_decision_report_blocks_rc_tagging() -> None:
    report = build_rc_release_decision_report()

    assert report["decision"] == "no_go"
    assert report["release_tag"] == "v1.15.0-rc.1"
    assert report["publish_allowed"] is False
    assert report["cutover_allowed"] is False
    assert report["blocked_reasons"] == [
        "p0_host_evidence_missing_or_blocked",
        "beta_validation_records_missing",
    ]
    assert report["completed_enablers"] == [
        "package_evidence_cli",
        "package_beta_triage_cli",
        "preview_gated_policy_assistant_tool",
    ]


def test_rc_release_decision_report_markdown_lists_blocked_commands() -> None:
    markdown = render_rc_release_decision_report_markdown(build_rc_release_decision_report())

    assert markdown.startswith("# RC Release Decision Report\n")
    assert "Decision: `no_go`" in markdown
    assert "`git tag v1.15.0-rc.1`" in markdown
    assert "`preview_gated_policy_assistant_tool`" in markdown
    assert "Do not create tags, GitHub Releases, PyPI uploads, or public announcements." in markdown


def test_committed_rc_release_decision_report_is_current() -> None:
    path = Path("docs/RC_RELEASE_DECISION_REPORT.md")

    assert path.read_text(encoding="utf-8") == render_rc_release_decision_report_markdown(
        build_rc_release_decision_report()
    )


def test_rc_release_decision_report_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "rc-release-decision-report.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_rc_release_decision_report.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# RC Release Decision Report\n")
