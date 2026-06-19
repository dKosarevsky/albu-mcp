import json
import subprocess
import sys
from pathlib import Path

from scripts.check_manual_host_acceptance import check_manual_host_acceptance


def test_manual_host_acceptance_reports_missing_hosts(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text('{"manual_host_ui": []}', encoding="utf-8")

    report = check_manual_host_acceptance(manual_runs_path)

    assert report.ok is False
    assert [check.host for check in report.checks] == ["Claude Desktop", "Claude Code", "Cursor", "Codex"]
    assert {check.status for check in report.checks} == {"pending"}
    assert all("manual UI run not recorded" in check.message for check in report.checks)


def test_manual_host_acceptance_accepts_all_required_hosts(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text(
        json.dumps(
            {
                "manual_host_ui": [
                    {
                        "host": host,
                        "status": "passed",
                        "date": "2026-06-19",
                        "evidence": f"{host} listed tools and completed the distortion review flow.",
                    }
                    for host in ["Claude Desktop", "Claude Code", "Cursor", "Codex"]
                ]
            }
        ),
        encoding="utf-8",
    )

    report = check_manual_host_acceptance(manual_runs_path)

    assert report.ok is True
    assert all(check.status == "passed" for check in report.checks)


def test_manual_host_acceptance_cli_prints_missing_hosts(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text('{"manual_host_ui": []}', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture path.
        [
            sys.executable,
            "scripts/check_manual_host_acceptance.py",
            "--path",
            str(manual_runs_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "[Claude Desktop]" in result.stderr
    assert "[Codex]" in result.stderr
    assert "manual UI run not recorded" in result.stderr
