from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from albumentationsx_mcp.growth import build_growth_report, render_growth_report_markdown
from scripts import export_growth_report

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
        "traffic_window_days": 14,
        "views": 9,
        "unique_visitors": 4,
        "stars": 5,
        "top_referrer_visits": 13,
        "top_referrer_count": 2,
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


def test_growth_report_orders_same_day_releases_by_full_timestamp() -> None:
    payload = _fixture()
    payload["github_releases"] = [
        {"tag_name": "v1.9.0", "published_at": "2026-07-01T01:00:00Z", "assets": []},
        {"tag_name": "v1.10.0", "published_at": "2026-07-01T23:00:00Z", "assets": []},
    ]

    report = build_growth_report(payload)

    assert report["release_assets"]["latest_release"] == "v1.10.0"


def test_growth_report_labels_github_traffic_window_and_top_referrer_subset() -> None:
    report = build_growth_report(_fixture())
    markdown = render_growth_report_markdown(report)

    assert report["collected_at"] == "2026-07-14T09:00:00+00:00"
    assert report["github"]["traffic_window_days"] == 14
    assert report["github"]["top_referrer_visits"] == 13
    assert report["github"]["top_referrer_count"] == 2
    assert "referrer_visits" not in report["github"]
    assert "GitHub views (rolling 14 days)" in markdown
    assert "Top-referrer visits (top 10, rolling 14 days)" in markdown


def test_growth_report_marks_owner_traffic_unavailable_instead_of_zero() -> None:
    payload = _fixture()
    payload["github_views"] = None
    payload["github_referrers"] = None
    payload["source_errors"] = {"github_traffic": "GH_TOKEN or GITHUB_TOKEN is not set"}

    report = build_growth_report(payload)

    assert report["github"]["traffic_available"] is False
    assert report["github"]["views"] is None
    assert report["github"]["unique_visitors"] is None
    assert report["github"]["top_referrer_visits"] is None
    assert "github_traffic: GH_TOKEN or GITHUB_TOKEN is not set" in report["warnings"]


def test_growth_report_distinguishes_empty_referrers_from_unavailable_source() -> None:
    payload = _fixture()
    payload["github_referrers"] = []

    report = build_growth_report(payload)
    markdown = render_growth_report_markdown(report)

    assert report["github"]["traffic_available"] is True
    assert report["github"]["top_referrer_visits"] == 0
    assert report["github"]["top_referrer_count"] == 0
    assert "- None reported" in markdown


def test_growth_report_does_not_divide_by_zero() -> None:
    payload = _fixture()
    for row in payload["pypistats"]["data"]:
        if "2026-06-30" <= row["date"] <= "2026-07-06":
            row["downloads"] = 0

    report = build_growth_report(payload)

    assert report["pypi"]["previous_7_days"] == 0
    assert report["pypi"]["week_over_week_percent"] is None
    assert "week_over_week_percent is unavailable because the previous period is zero" in report["warnings"]


def test_growth_report_marks_sparse_release_excluded_baseline_unavailable() -> None:
    payload = _fixture()
    payload["pypistats"]["data"] = [payload["pypistats"]["data"][-1]]
    payload["github_releases"] = []

    report = build_growth_report(payload, baseline_days=14)
    markdown = render_growth_report_markdown(report)

    assert report["pypi"]["release_excluded_median_daily"] is None
    assert report["pypi"]["baseline_complete"] is False
    assert report["pypi"]["baseline_sample_days"] == 1
    assert report["pypi"]["baseline_eligible_days"] == 14
    assert any("baseline contains 1 of 14 eligible dates" in warning for warning in report["warnings"])
    assert "Release-excluded median: `unavailable`" in markdown


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
    assert "rolling 14-day Traffic window" in guide
    assert "top 10 referrers" in guide
    assert "unless every non-excluded date" in guide
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


def test_live_growth_report_fetches_every_github_release_page(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = [
        [{"tag_name": f"v1.0.{index}"} for index in range(100)],
        [{"tag_name": "v1.0.100"}],
    ]
    requested_urls: list[str] = []

    def fake_fetch_json(url: str, *, headers: dict[str, str]) -> object:
        requested_urls.append(url)
        assert headers == {"Accept": "application/vnd.github+json"}
        return pages[len(requested_urls) - 1]

    monkeypatch.setattr(export_growth_report, "_fetch_json", fake_fetch_json)

    releases = export_growth_report._fetch_github_releases(
        "dKosarevsky/albu-mcp",
        headers={"Accept": "application/vnd.github+json"},
    )

    assert len(releases) == 101
    assert requested_urls == [
        "https://api.github.com/repos/dKosarevsky/albu-mcp/releases?per_page=100&page=1",
        "https://api.github.com/repos/dKosarevsky/albu-mcp/releases?per_page=100&page=2",
    ]


def _fixture() -> dict[str, Any]:
    return deepcopy(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
