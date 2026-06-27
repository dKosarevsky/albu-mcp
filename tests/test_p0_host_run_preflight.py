from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.check_p0_host_run_preflight import (
    P0HostRunPreflightConfig,
    check_p0_host_run_preflight,
    render_p0_host_run_preflight_markdown,
)


def test_p0_host_run_preflight_accepts_current_workspace() -> None:
    report = check_p0_host_run_preflight()

    assert report.ok is True
    assert [check.name for check in report.checks] == [
        "package_import",
        "allowed_root",
        "artifact_root",
        "demo_assets",
        "host_prompts",
        "run_session_doc",
        "manual_records",
    ]
    assert report.by_name["allowed_root"].message.endswith("docs/assets/demo/inputs")
    assert all(check.message for check in report.checks)


def test_p0_host_run_preflight_reports_missing_run_session_doc(tmp_path: Path) -> None:
    report = check_p0_host_run_preflight(P0HostRunPreflightConfig(run_session_path=tmp_path / "missing-session.md"))

    assert report.ok is False
    assert report.by_name["run_session_doc"].ok is False
    assert "missing-session.md" in report.by_name["run_session_doc"].message


def test_p0_host_run_preflight_markdown_is_current() -> None:
    markdown = render_p0_host_run_preflight_markdown(check_p0_host_run_preflight())

    assert markdown.startswith("# P0 Host Run Preflight\n")
    assert "Preflight status: `passed`" in markdown
    assert "| package_import | passed |" in markdown
    assert "Record real host UI evidence only after this preflight passes." in markdown


def test_p0_host_run_preflight_cli_outputs_json() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_p0_host_run_preflight.py", "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["checks"][0]["name"] == "package_import"


def test_p0_host_run_preflight_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "p0-host-run-preflight.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/check_p0_host_run_preflight.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# P0 Host Run Preflight\n")
