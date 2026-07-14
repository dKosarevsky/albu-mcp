"""Privacy-safe aggregate growth analysis for package maintainers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import median
from typing import Any

_MIN_BASELINE_DAYS = 14


@dataclass(frozen=True)
class _ReleaseRecord:
    """Normalized release data used by demand and asset analysis."""

    tag: str
    published_on: date
    mcpb_downloads: int


def build_growth_report(
    payload: Mapping[str, Any],
    *,
    baseline_days: int = 28,
    release_exclusion_days: int = 2,
) -> dict[str, Any]:
    """Build a release-aware report from aggregate PyPI and GitHub payloads."""
    if baseline_days < _MIN_BASELINE_DAYS:
        msg = "baseline_days must be at least 14"
        raise ValueError(msg)
    if release_exclusion_days < 0:
        msg = "release_exclusion_days must be non-negative"
        raise ValueError(msg)

    downloads = _parse_downloads(_required_mapping(payload, "pypistats"))
    releases = _parse_releases(payload.get("github_releases"))
    as_of = max(downloads)
    warnings = _source_warnings(payload.get("source_errors"))

    current_dates = _date_window(as_of=as_of, days=7)
    previous_dates = _date_window(as_of=as_of - timedelta(days=7), days=7)
    current_total, current_complete = _period_total(downloads, current_dates)
    previous_total, previous_complete = _period_total(downloads, previous_dates)
    if not current_complete:
        warnings.append("last_7_days is incomplete because one or more PyPI dates are missing")
    if not previous_complete:
        warnings.append("previous_7_days is incomplete because one or more PyPI dates are missing")

    if previous_total == 0:
        week_over_week_percent: float | None = None
        warnings.append("week_over_week_percent is unavailable because the previous period is zero")
    else:
        week_over_week_percent = round(((current_total - previous_total) / previous_total) * 100, 1)

    baseline_window = _date_window(as_of=as_of, days=baseline_days)
    excluded_dates = _release_window_dates(releases, days_after_release=release_exclusion_days)
    excluded_in_baseline = sorted(set(baseline_window) & excluded_dates)
    baseline_values = [downloads[day] for day in baseline_window if day in downloads and day not in excluded_dates]
    if not baseline_values:
        msg = "no release-independent PyPI days remain in the baseline window"
        raise ValueError(msg)

    github = _build_github_summary(
        views=payload.get("github_views"),
        referrers=payload.get("github_referrers"),
        repository=payload.get("github_repository"),
    )
    if not github["traffic_available"] and not _has_source_error(payload.get("source_errors"), "github_traffic"):
        warnings.append("github_traffic: owner traffic data is unavailable")

    return {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "privacy": {
            "runtime_telemetry": False,
            "reads_local_data": False,
            "scope": "aggregate package, repository, referrer, and release-asset counts only",
        },
        "pypi": {
            "metric": "downloads_without_mirrors",
            "last_7_days": current_total,
            "previous_7_days": previous_total,
            "week_over_week_percent": week_over_week_percent,
            "last_7_days_complete": current_complete,
            "previous_7_days_complete": previous_complete,
            "baseline_window_days": baseline_days,
            "release_exclusion_days_after_release": release_exclusion_days,
            "release_excluded_median_daily": float(median(baseline_values)),
            "baseline_sample_days": len(baseline_values),
            "excluded_release_dates": [day.isoformat() for day in excluded_in_baseline],
        },
        "github": github,
        "release_assets": _build_release_asset_summary(releases),
        "sources": {
            "pypistats_without_mirrors": "available",
            "github_releases": "available",
            "github_repository": "available" if payload.get("github_repository") is not None else "unavailable",
            "github_traffic": "available" if github["traffic_available"] else "unavailable",
        },
        "warnings": warnings,
    }


def render_growth_report_markdown(report: Mapping[str, Any]) -> str:
    """Render an aggregate growth report as operator-focused Markdown."""
    pypi = _required_mapping(report, "pypi")
    github = _required_mapping(report, "github")
    release_assets = _required_mapping(report, "release_assets")
    privacy = _required_mapping(report, "privacy")
    warnings = report.get("warnings", [])
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) if warnings else "- None"
    referrers = github.get("top_referrers")
    if isinstance(referrers, list) and referrers:
        referrer_lines = "\n".join(
            f"- `{item['name']}`: {item['visits']} visits, {item['uniques']} unique visitors" for item in referrers
        )
    else:
        referrer_lines = "- Unavailable"

    week_over_week = pypi["week_over_week_percent"]
    week_over_week_text = "n/a" if week_over_week is None else f"{week_over_week:.1f}%"
    runtime_telemetry = "enabled" if privacy["runtime_telemetry"] else "disabled"
    return (
        "# Aggregate Growth Report\n\n"
        f"As of: `{report['as_of']}`\n\n"
        f"Runtime telemetry: `{runtime_telemetry}`\n\n"
        "This report reads aggregate distribution metadata only. It does not inspect datasets, preview artifacts, "
        "host logs, or local paths.\n\n"
        "## Demand\n\n"
        "Metric: Downloads without mirrors\n\n"
        f"- Last 7 days: `{pypi['last_7_days']}`\n"
        f"- Previous 7 days: `{pypi['previous_7_days']}`\n"
        f"- Week over week: `{week_over_week_text}`\n"
        f"- Release-excluded median: `{pypi['release_excluded_median_daily']}` downloads/day "
        f"from `{pypi['baseline_sample_days']}` sampled days\n\n"
        "## Qualified Reach\n\n"
        f"- GitHub views: `{_optional_metric(github['views'])}`\n"
        f"- Unique visitors: `{_optional_metric(github['unique_visitors'])}`\n"
        f"- Stars: `{_optional_metric(github['stars'])}`\n"
        f"- Referrer visits: `{_optional_metric(github['referrer_visits'])}`\n\n"
        "### Top Referrers\n\n"
        f"{referrer_lines}\n\n"
        "## Installable Assets\n\n"
        f"- MCPB downloads across releases: `{release_assets['mcpb_downloads_total']}`\n"
        f"- Latest release: `{release_assets['latest_release'] or 'n/a'}`\n"
        f"- Latest-release MCPB downloads: `{release_assets['latest_release_mcpb_downloads']}`\n\n"
        "## Warnings\n\n"
        f"{warning_lines}\n\n"
        "## Interpretation\n\n"
        "PyPI downloads are a distribution proxy, not proof of a successful preview. Track a release-excluded "
        "baseline, "
        "qualified human reach, MCPB downloads, and voluntary real-host evidence together.\n"
    )


def _parse_downloads(payload: Mapping[str, Any]) -> dict[date, int]:
    rows = payload.get("data")
    if not isinstance(rows, list):
        msg = "pypistats data must be a list"
        raise TypeError(msg)
    downloads: dict[date, int] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            msg = f"pypistats row {index} must be an object"
            raise TypeError(msg)
        if row.get("category") != "without_mirrors":
            continue
        day = _parse_iso_date(row.get("date"), field=f"pypistats row {index} date")
        count = _parse_count(row.get("downloads"), field=f"pypistats row {index} downloads")
        downloads[day] = downloads.get(day, 0) + count
    if not downloads:
        msg = "pypistats data must contain without_mirrors rows"
        raise ValueError(msg)
    return downloads


def _parse_releases(value: Any) -> list[_ReleaseRecord]:
    if not isinstance(value, list):
        msg = "github_releases must be a list"
        raise TypeError(msg)
    releases: list[_ReleaseRecord] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            msg = f"github release {index} must be an object"
            raise TypeError(msg)
        published_at = item.get("published_at")
        if published_at is None:
            continue
        published_on = _parse_iso_datetime(published_at, field=f"github release {index} published_at").date()
        tag = item.get("tag_name")
        if not isinstance(tag, str) or not tag:
            msg = f"github release {index} tag_name must be a non-empty string"
            raise ValueError(msg)
        assets = item.get("assets", [])
        if not isinstance(assets, list):
            msg = f"github release {index} assets must be a list"
            raise TypeError(msg)
        mcpb_downloads = 0
        for asset_index, asset in enumerate(assets):
            if not isinstance(asset, Mapping):
                msg = f"github release {index} asset {asset_index} must be an object"
                raise TypeError(msg)
            name = asset.get("name")
            if isinstance(name, str) and name.endswith(".mcpb"):
                mcpb_downloads += _parse_count(
                    asset.get("download_count"),
                    field=f"github release {index} asset {asset_index} download_count",
                )
        releases.append(_ReleaseRecord(tag=tag, published_on=published_on, mcpb_downloads=mcpb_downloads))
    return sorted(releases, key=lambda release: (release.published_on, release.tag))


def _build_github_summary(*, views: Any, referrers: Any, repository: Any) -> dict[str, Any]:
    view_count: int | None = None
    unique_visitors: int | None = None
    if views is not None:
        if not isinstance(views, Mapping):
            msg = "github_views must be an object or null"
            raise TypeError(msg)
        view_count = _parse_count(views.get("count"), field="github_views count")
        unique_visitors = _parse_count(views.get("uniques"), field="github_views uniques")

    top_referrers: list[dict[str, Any]] | None = None
    referrer_visits: int | None = None
    referrer_uniques: int | None = None
    if referrers is not None:
        if not isinstance(referrers, list):
            msg = "github_referrers must be a list or null"
            raise TypeError(msg)
        top_referrers = []
        for index, item in enumerate(referrers):
            if not isinstance(item, Mapping):
                msg = f"github referrer {index} must be an object"
                raise TypeError(msg)
            name = item.get("referrer")
            if not isinstance(name, str) or not name:
                msg = f"github referrer {index} name must be a non-empty string"
                raise ValueError(msg)
            top_referrers.append(
                {
                    "name": name,
                    "visits": _parse_count(item.get("count"), field=f"github referrer {index} count"),
                    "uniques": _parse_count(item.get("uniques"), field=f"github referrer {index} uniques"),
                }
            )
        top_referrers.sort(key=lambda item: (-item["visits"], item["name"].lower()))
        referrer_visits = sum(item["visits"] for item in top_referrers)
        referrer_uniques = sum(item["uniques"] for item in top_referrers)

    stars: int | None = None
    if repository is not None:
        if not isinstance(repository, Mapping):
            msg = "github_repository must be an object or null"
            raise TypeError(msg)
        stars = _parse_count(repository.get("stargazers_count"), field="github_repository stargazers_count")

    return {
        "traffic_available": views is not None and referrers is not None,
        "views": view_count,
        "unique_visitors": unique_visitors,
        "stars": stars,
        "referrer_visits": referrer_visits,
        "referrer_uniques": referrer_uniques,
        "top_referrers": top_referrers,
    }


def _build_release_asset_summary(releases: list[_ReleaseRecord]) -> dict[str, Any]:
    latest = releases[-1] if releases else None
    return {
        "release_count": len(releases),
        "mcpb_downloads_total": sum(release.mcpb_downloads for release in releases),
        "latest_release": latest.tag if latest else None,
        "latest_release_mcpb_downloads": latest.mcpb_downloads if latest else 0,
    }


def _source_warnings(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Mapping):
        msg = "source_errors must be an object"
        raise TypeError(msg)
    warnings: list[str] = []
    for source, error in sorted(value.items(), key=lambda item: str(item[0])):
        if not isinstance(source, str) or not isinstance(error, str):
            msg = "source_errors keys and values must be strings"
            raise TypeError(msg)
        warnings.append(f"{source}: {error}")
    return warnings


def _has_source_error(value: Any, source: str) -> bool:
    return isinstance(value, Mapping) and source in value


def _required_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        msg = f"{key} must be an object"
        raise TypeError(msg)
    return value


def _parse_iso_date(value: Any, *, field: str) -> date:
    if not isinstance(value, str):
        msg = f"{field} must be a valid ISO date"
        raise TypeError(msg)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        msg = f"{field} must be a valid ISO date"
        raise ValueError(msg) from exc


def _parse_iso_datetime(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str):
        msg = f"{field} must be a valid ISO datetime"
        raise TypeError(msg)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        msg = f"{field} must be a valid ISO datetime"
        raise ValueError(msg) from exc


def _parse_count(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        msg = f"{field} must be a non-negative integer"
        raise ValueError(msg)
    return value


def _date_window(*, as_of: date, days: int) -> list[date]:
    return [as_of - timedelta(days=offset) for offset in range(days - 1, -1, -1)]


def _period_total(downloads: Mapping[date, int], dates: list[date]) -> tuple[int, bool]:
    return sum(downloads.get(day, 0) for day in dates), all(day in downloads for day in dates)


def _release_window_dates(releases: list[_ReleaseRecord], *, days_after_release: int) -> set[date]:
    return {
        release.published_on + timedelta(days=offset)
        for release in releases
        for offset in range(days_after_release + 1)
    }


def _optional_metric(value: Any) -> str:
    return "unavailable" if value is None else str(value)
