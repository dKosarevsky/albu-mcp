from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.export_v1_launch_report import build_v1_launch_report, render_v1_launch_report_markdown


def test_v1_launch_report_tracks_pending_manual_host_blockers() -> None:
    report = build_v1_launch_report()

    assert report["package_version"] == "1.15.0"
    assert report["server_version"] == "1.15.0"
    assert report["ready_for_v1"] is False
    assert {blocker["code"] for blocker in report["blockers"]} == {
        "manual_host_ui_pending",
        "first_10_minutes_replay_pending",
    }
    assert {item["host"] for item in report["manual_host_ui"]} == {
        "Claude Desktop",
        "Claude Code",
        "Cursor",
        "Codex",
    }
    assert {item["status"] for item in report["manual_host_ui"]} == {"pending"}
    assert {item["status"] for item in report["first_10_minutes_replay"]} == {"pending"}


def test_v1_launch_report_markdown_is_reviewable() -> None:
    markdown = render_v1_launch_report_markdown(build_v1_launch_report())

    assert markdown.startswith("# V1 Launch Report\n")
    assert "Package version: `1.15.0`" in markdown
    assert "Ready for v1: `false`" in markdown
    assert "manual_host_ui_pending" in markdown
    assert "first_10_minutes_replay_pending" in markdown
    assert "docs/HOST_PROOF_STATUS.md" in markdown


def test_v1_launch_report_cli_outputs_json_and_markdown(tmp_path: Path) -> None:
    json_result = subprocess.run(
        [sys.executable, "scripts/export_v1_launch_report.py", "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(json_result.stdout)
    assert payload["ready_for_v1"] is False

    output_path = tmp_path / "v1-launch.md"
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "scripts/export_v1_launch_report.py",
            "--format",
            "markdown",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Ready for v1: `false`" in output_path.read_text(encoding="utf-8")


def test_committed_v1_launch_report_is_current() -> None:
    report_path = Path("docs/V1_LAUNCH_REPORT.md")

    assert "[docs/V1_LAUNCH_REPORT.md](docs/V1_LAUNCH_REPORT.md)" in Path("README.md").read_text(encoding="utf-8")
    assert "docs/V1_LAUNCH_REPORT.md" in Path("docs/V1_READINESS.md").read_text(encoding="utf-8")
    assert report_path.read_text(encoding="utf-8") == render_v1_launch_report_markdown(build_v1_launch_report())
