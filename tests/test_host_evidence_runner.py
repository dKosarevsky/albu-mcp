from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_host_evidence_runner import build_host_evidence_runner, render_host_evidence_runner_markdown


def test_host_evidence_runner_builds_blocked_p0_lanes() -> None:
    runner = build_host_evidence_runner()

    assert runner["runner_status"] == "blocked_until_p0_evidence_passes"
    assert runner["preflight_status"] == "passed"
    assert runner["rc_reopen_allowed"] is False
    assert runner["summary"]["target_host_count"] == 1
    assert runner["summary"]["runner_lane_count"] == 2
    assert runner["summary"]["blocked_lane_count"] == 2
    assert [lane["host"] for lane in runner["host_lanes"]] == ["Claude Code"]
    assert all(lane["lane_status"] == "blocked_evidence_required" for lane in runner["host_lanes"])
    assert all("run_host_smoke_check" in lane["operator_prompt"] for lane in runner["host_lanes"])
    assert all(
        "record_host_manual_run.py" in command
        for lane in runner["host_lanes"]
        for command in lane["blocked_record_commands"] + lane["passed_record_commands"]
    )


def test_host_evidence_runner_markdown_is_operator_focused() -> None:
    markdown = render_host_evidence_runner_markdown(build_host_evidence_runner())

    assert markdown.startswith("# Host Evidence Runner\n")
    assert "Runner status: `blocked_until_p0_evidence_passes`" in markdown
    assert "Preflight status: `passed`" in markdown
    assert "generated smoke output is not accepted as passed host evidence" in markdown
    assert "| Claude Code | `blocked_evidence_required` | `first_10_minutes_replay`, `manual_host_ui` |" in markdown
    assert "Passed evidence:" in markdown
    assert "Blocked evidence:" in markdown


def test_committed_host_evidence_runner_is_current() -> None:
    runner_path = Path("docs/HOST_EVIDENCE_RUNNER.md")

    assert runner_path.read_text(encoding="utf-8") == render_host_evidence_runner_markdown(build_host_evidence_runner())
    assert "[docs/HOST_EVIDENCE_RUNNER.md](docs/HOST_EVIDENCE_RUNNER.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_host_evidence_runner_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "host-evidence-runner.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_host_evidence_runner.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Host Evidence Runner\n")
