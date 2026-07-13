import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.record_host_manual_run import (
    FirstTenMinutesReplayEvidence,
    record_first_10_minutes_replay,
    record_host_manual_run,
)
from scripts.validate_host_manual_runs import validate_host_manual_runs


def test_repository_records_claude_desktop_manual_acceptance() -> None:
    report = validate_host_manual_runs()

    record = next(item for item in report.manual_host_ui if item.host == "Claude Desktop")
    receipt = Path("docs/host-evidence/claude-desktop-2026-07-13.md")

    assert record.status == "passed"
    assert record.model_dump(mode="json")["date"] == "2026-07-13"
    assert "preview_ready=true" in record.evidence
    assert receipt.is_file()
    assert "resource reads" in receipt.read_text(encoding="utf-8")


def test_host_manual_runs_validator_accepts_dated_records(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text(
        json.dumps(
            {
                "manual_host_ui": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-06-19",
                        "evidence": "Codex app listed tools and ran run_host_smoke_check.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = validate_host_manual_runs(manual_runs_path)

    assert report.manual_host_ui[0].host == "Codex"
    assert report.manual_host_ui[0].status == "passed"
    assert report.manual_host_ui[0].model_dump(mode="json")["date"] == "2026-06-19"


def test_host_manual_runs_validator_accepts_first_10_minutes_replay_records(tmp_path: Path) -> None:
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
                        "evidence": "Codex completed smoke, validated preview, rendered baseline and candidate, "
                        "compared runs, and exported Python.",
                        "artifacts": [
                            "docs/assets/demo/demo_report.md",
                            "docs/assets/demo/comparison_contact_sheet.png",
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = validate_host_manual_runs(manual_runs_path)
    replay = report.first_10_minutes_replay[0]

    assert replay.host == "Codex"
    assert replay.status == "passed"
    assert replay.artifacts == [
        "docs/assets/demo/demo_report.md",
        "docs/assets/demo/comparison_contact_sheet.png",
    ]


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (
            {
                "host": "Unknown Host",
                "status": "passed",
                "date": "2026-06-19",
                "evidence": "invalid host",
            },
            "host",
        ),
        (
            {
                "host": "Codex",
                "status": "done",
                "date": "2026-06-19",
                "evidence": "invalid status",
            },
            "status",
        ),
        (
            {
                "host": "Codex",
                "status": "passed",
                "date": "19-06-2026",
                "evidence": "invalid date",
            },
            "date",
        ),
        (
            {
                "host": "Codex",
                "status": "passed",
                "date": "2026-06-19",
                "evidence": "extra property",
                "unexpected": True,
            },
            "unexpected",
        ),
    ],
)
def test_host_manual_runs_validator_rejects_invalid_records(
    tmp_path: Path,
    record: dict[str, object],
    message: str,
) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text(json.dumps({"manual_host_ui": [record]}), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        validate_host_manual_runs(manual_runs_path)


def test_host_manual_runs_validator_rejects_duplicate_hosts(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text(
        json.dumps(
            {
                "manual_host_ui": [
                    {
                        "host": "Codex",
                        "status": "passed",
                        "date": "2026-06-19",
                        "evidence": "first record",
                    },
                    {
                        "host": "Codex",
                        "status": "blocked",
                        "date": "2026-06-20",
                        "evidence": "second record",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate manual host UI record"):
        validate_host_manual_runs(manual_runs_path)


def test_host_manual_runs_validator_rejects_duplicate_first_10_minutes_hosts(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    replay = {
        "host": "Codex",
        "status": "passed",
        "date": "2026-06-22",
        "evidence": "first replay",
        "artifacts": ["docs/assets/demo/demo_report.md"],
    }
    manual_runs_path.write_text(
        json.dumps({"manual_host_ui": [], "first_10_minutes_replay": [replay, {**replay, "evidence": "second"}]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate first 10 minutes replay record"):
        validate_host_manual_runs(manual_runs_path)


def test_record_host_manual_run_adds_and_replaces_records_in_canonical_order(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text(
        json.dumps(
            {
                "manual_host_ui": [
                    {
                        "host": "Codex",
                        "status": "blocked",
                        "date": "2026-06-18",
                        "evidence": "initial Codex note",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    record_host_manual_run(
        path=manual_runs_path,
        host="Cursor",
        status="passed",
        run_date="2026-06-19",
        evidence="Cursor listed tools and completed run_host_smoke_check.",
    )
    report = record_host_manual_run(
        path=manual_runs_path,
        host="Codex",
        status="passed",
        run_date="2026-06-20",
        evidence="Codex listed tools and completed run_host_smoke_check.",
    )

    records = [record.model_dump(mode="json") for record in report.manual_host_ui]

    assert [record["host"] for record in records] == ["Cursor", "Codex"]
    assert records[0]["status"] == "passed"
    assert records[1]["date"] == "2026-06-20"
    assert "initial Codex note" not in manual_runs_path.read_text(encoding="utf-8")


def test_record_host_manual_run_preserves_first_10_minutes_replay_records(tmp_path: Path) -> None:
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
                        "evidence": "Codex completed the first 10 minutes path.",
                        "artifacts": ["docs/assets/demo/demo_report.md"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = record_host_manual_run(
        path=manual_runs_path,
        host="Codex",
        status="passed",
        run_date="2026-06-23",
        evidence="Codex completed the broader host UI flow.",
    )

    assert report.manual_host_ui[0].evidence == "Codex completed the broader host UI flow."
    assert report.first_10_minutes_replay[0].evidence == "Codex completed the first 10 minutes path."
    assert report.first_10_minutes_replay[0].artifacts == ["docs/assets/demo/demo_report.md"]


def test_record_host_manual_run_cli_writes_valid_json(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text('{"manual_host_ui": []}', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/record_host_manual_run.py",
            "--path",
            str(manual_runs_path),
            "--host",
            "Codex",
            "--status",
            "passed",
            "--date",
            "2026-06-19",
            "--evidence",
            "Codex listed tools and completed run_host_smoke_check.",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = validate_host_manual_runs(manual_runs_path)

    assert "recorded Codex passed on 2026-06-19" in result.stdout
    assert report.manual_host_ui[0].host == "Codex"


def test_record_first_10_minutes_replay_adds_records_in_canonical_order(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}', encoding="utf-8")

    record_first_10_minutes_replay(
        path=manual_runs_path,
        replay=FirstTenMinutesReplayEvidence(
            host="Codex",
            status="blocked",
            run_date="2026-06-21",
            evidence="Codex could not access the configured artifact root.",
            artifacts=[],
        ),
    )
    report = record_first_10_minutes_replay(
        path=manual_runs_path,
        replay=FirstTenMinutesReplayEvidence(
            host="Cursor",
            status="passed",
            run_date="2026-06-22",
            evidence="Cursor completed smoke, preview, comparison, and export.",
            artifacts=["docs/assets/demo/demo_report.md"],
        ),
    )

    records = [record.model_dump(mode="json") for record in report.first_10_minutes_replay]

    assert [record["host"] for record in records] == ["Cursor", "Codex"]
    assert records[0]["status"] == "passed"
    assert records[0]["artifacts"] == ["docs/assets/demo/demo_report.md"]


def test_record_first_10_minutes_replay_cli_writes_valid_json(tmp_path: Path) -> None:
    manual_runs_path = tmp_path / "HOST_MANUAL_RUNS.json"
    manual_runs_path.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/record_host_manual_run.py",
            "--kind",
            "first-10-minutes",
            "--path",
            str(manual_runs_path),
            "--host",
            "Codex",
            "--status",
            "passed",
            "--date",
            "2026-06-22",
            "--evidence",
            "Codex completed smoke, preview, comparison, and export.",
            "--artifact",
            "docs/assets/demo/demo_report.md",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = validate_host_manual_runs(manual_runs_path)

    assert "recorded first-10-minutes Codex passed on 2026-06-22" in result.stdout
    assert report.first_10_minutes_replay[0].host == "Codex"
    assert report.first_10_minutes_replay[0].artifacts == ["docs/assets/demo/demo_report.md"]
