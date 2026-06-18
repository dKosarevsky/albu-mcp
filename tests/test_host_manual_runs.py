import json
from pathlib import Path

import pytest

from scripts.validate_host_manual_runs import validate_host_manual_runs


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
