from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_v1_growth_cutover_report import (
    build_v1_growth_cutover_report,
    render_v1_growth_cutover_report_markdown,
)


def test_v1_growth_cutover_report_holds_rc_but_keeps_growth_ready() -> None:
    report = build_v1_growth_cutover_report()

    assert report["cutover_status"] == "blocked_by_p0_evidence"
    assert report["rc_publish_allowed"] is False
    assert report["beta_campaign_status"] == "ready_to_invite"
    assert report["growth_status"] == "ready"
    assert report["blocking_gates"] == ["p0_host_evidence"]
    assert "Official MCP Registry" in [channel["name"] for channel in report["growth_channels"]]
    assert report["next_cutover_actions"][0] == "Record real Codex and Claude Code P0 host evidence."


def test_v1_growth_cutover_report_markdown_links_cutover_and_growth() -> None:
    markdown = render_v1_growth_cutover_report_markdown(build_v1_growth_cutover_report())

    assert markdown.startswith("# V1 Growth Cutover Report\n")
    assert "Cutover status: `blocked_by_p0_evidence`" in markdown
    assert "RC publish allowed: `false`" in markdown
    assert "Beta campaign status: `ready_to_invite`" in markdown
    assert "## Growth Channels" in markdown
    assert "Official MCP Registry" in markdown
    assert "Record real Codex and Claude Code P0 host evidence." in markdown


def test_committed_v1_growth_cutover_report_is_current() -> None:
    report_path = Path("docs/V1_GROWTH_CUTOVER_REPORT.md")

    assert report_path.read_text(encoding="utf-8") == render_v1_growth_cutover_report_markdown(
        build_v1_growth_cutover_report()
    )
    assert "[V1_GROWTH_CUTOVER_REPORT.md](V1_GROWTH_CUTOVER_REPORT.md)" in Path("docs/ARCHIVE.md").read_text(
        encoding="utf-8"
    )


def test_v1_growth_cutover_report_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "v1-growth-cutover-report.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_v1_growth_cutover_report.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# V1 Growth Cutover Report\n")
