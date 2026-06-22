import json
import subprocess
import sys
from pathlib import Path

from scripts.check_first_10_minutes_replay import check_first_10_minutes_replay


def test_first_10_minutes_replay_reports_missing_hosts(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}', encoding="utf-8")

    report = check_first_10_minutes_replay(manual_runs_path, required_hosts=("Codex", "Cursor"))

    assert report.ok is False
    assert [check.host for check in report.checks] == ["Codex", "Cursor"]
    assert {check.status for check in report.checks} == {"pending"}
    assert all("first 10 minutes replay not recorded" in check.message for check in report.checks)


def test_first_10_minutes_replay_accepts_passed_required_hosts(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text(
        json.dumps(
            {
                "manual_host_ui": [],
                "first_10_minutes_replay": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-06-22",
                        "evidence": "Codex completed smoke, preview validation, render, compare, and export.",
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = check_first_10_minutes_replay(manual_runs_path, required_hosts=("Codex",))

    assert report.ok is True
    assert report.checks[0].host == "Codex"
    assert report.checks[0].status == "passed"
    assert report.checks[0].artifacts == ["docs/assets/demo/demo_report.md"]


def test_first_10_minutes_replay_cli_prints_missing_hosts(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture path.
        [
            sys.executable,
            "scripts/check_first_10_minutes_replay.py",
            "--path",
            str(manual_runs_path),
            "--host",
            "Codex",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "[Codex]" in result.stderr
    assert "first 10 minutes replay not recorded" in result.stderr


def test_first_10_minutes_replay_cli_outputs_json(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text(
        json.dumps(
            {
                "manual_host_ui": [],
                "first_10_minutes_replay": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-06-22",
                        "evidence": "Codex completed smoke, preview validation, render, compare, and export.",
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture path.
        [
            sys.executable,
            "scripts/check_first_10_minutes_replay.py",
            "--path",
            str(manual_runs_path),
            "--host",
            "Codex",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["checks"][0]["host"] == "Codex"
    assert payload["checks"][0]["artifacts"] == ["docs/assets/demo/demo_report.md"]
