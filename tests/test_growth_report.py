from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from albumentationsx_mcp.growth import build_growth_report, render_growth_report_markdown

FIXTURE_PATH = Path("tests/fixtures/growth_report_input.json")


def test_growth_report_separates_release_spikes_from_weekly_demand() -> None:
    payload = _fixture()

    report = build_growth_report(payload)

    assert report["as_of"] == "2026-07-13"
    assert report["pypi"]["last_7_days"] == 280
    assert report["pypi"]["previous_7_days"] == 28
    assert report["pypi"]["week_over_week_percent"] == 900.0
    assert report["pypi"]["release_excluded_median_daily"] == 5.0
    assert report["pypi"]["baseline_sample_days"] == 22
    assert report["pypi"]["excluded_release_dates"] == [
        "2026-06-18",
        "2026-06-19",
        "2026-06-20",
        "2026-07-11",
        "2026-07-12",
        "2026-07-13",
    ]


def test_growth_report_uses_aggregate_human_reach_and_mcpb_downloads() -> None:
    report = build_growth_report(_fixture())

    assert report["github"] == {
        "traffic_available": True,
        "views": 9,
        "unique_visitors": 4,
        "stars": 5,
        "referrer_visits": 13,
        "referrer_uniques": 11,
        "top_referrers": [
            {"name": "albumentations.ai", "visits": 10, "uniques": 8},
            {"name": "Google", "visits": 3, "uniques": 3},
        ],
    }
    assert report["release_assets"] == {
        "release_count": 2,
        "mcpb_downloads_total": 9,
        "latest_release": "v1.1.0",
        "latest_release_mcpb_downloads": 7,
    }
    assert report["privacy"]["runtime_telemetry"] is False


def test_growth_report_marks_owner_traffic_unavailable_instead_of_zero() -> None:
    payload = _fixture()
    payload["github_views"] = None
    payload["github_referrers"] = None
    payload["source_errors"] = {"github_traffic": "GH_TOKEN or GITHUB_TOKEN is not set"}

    report = build_growth_report(payload)

    assert report["github"]["traffic_available"] is False
    assert report["github"]["views"] is None
    assert report["github"]["unique_visitors"] is None
    assert report["github"]["referrer_visits"] is None
    assert "github_traffic: GH_TOKEN or GITHUB_TOKEN is not set" in report["warnings"]


def test_growth_report_does_not_divide_by_zero() -> None:
    payload = _fixture()
    for row in payload["pypistats"]["data"]:
        if "2026-06-30" <= row["date"] <= "2026-07-06":
            row["downloads"] = 0

    report = build_growth_report(payload)

    assert report["pypi"]["previous_7_days"] == 0
    assert report["pypi"]["week_over_week_percent"] is None
    assert "week_over_week_percent is unavailable because the previous period is zero" in report["warnings"]


@pytest.mark.parametrize(
    ("pypistats", "message"),
    [
        ({"data": []}, "without_mirrors"),
        (
            {"data": [{"category": "without_mirrors", "date": "not-a-date", "downloads": 1}]},
            "ISO date",
        ),
        (
            {"data": [{"category": "without_mirrors", "date": "2026-07-13", "downloads": -1}]},
            "non-negative",
        ),
    ],
)
def test_growth_report_rejects_misleading_download_data(pypistats: dict[str, object], message: str) -> None:
    payload = _fixture()
    payload["pypistats"] = pypistats

    with pytest.raises(ValueError, match=message):
        build_growth_report(payload)


def test_growth_report_markdown_explains_metric_and_privacy_boundaries() -> None:
    markdown = render_growth_report_markdown(build_growth_report(_fixture()))

    assert markdown.startswith("# Aggregate Growth Report\n")
    assert "Downloads without mirrors" in markdown
    assert "Release-excluded median" in markdown
    assert "Runtime telemetry: `disabled`" in markdown
    assert "PyPI downloads are a distribution proxy, not proof of a successful preview." in markdown
    assert "albumentations.ai" in markdown


def test_growth_docs_define_private_by_default_operating_cadence() -> None:
    guide = Path("docs/GROWTH.md").read_text(encoding="utf-8")
    docs_index = Path("docs/INDEX.md").read_text(encoding="utf-8")

    assert "scripts/export_growth_report.py" in guide
    assert 'GH_TOKEN="$(gh auth token)"' in guide
    assert "release day plus the following two calendar days" in guide
    assert "No runtime telemetry" in guide
    assert "successful first preview" in guide
    assert "[GROWTH.md](GROWTH.md)" in docs_index


@pytest.mark.parametrize("output_format", ["markdown", "json"])
def test_growth_report_cli_supports_reproducible_offline_input(tmp_path: Path, output_format: str) -> None:
    output_path = tmp_path / f"growth-report.{'md' if output_format == 'markdown' else 'json'}"

    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "scripts/export_growth_report.py",
            "--input",
            str(FIXTURE_PATH),
            "--format",
            output_format,
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    if output_format == "markdown":
        assert content.startswith("# Aggregate Growth Report\n")
        assert "Last 7 days: `280`" in content
    else:
        assert json.loads(content)["pypi"]["release_excluded_median_daily"] == 5.0


def _fixture() -> dict[str, Any]:
    return deepcopy(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
