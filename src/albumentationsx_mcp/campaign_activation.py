"""Privacy-safe campaign activation analysis over aggregate public evidence."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlsplit

_CAMPAIGN_WINDOW_DAYS = 14
_ISSUE_BODY_LIMIT = 100_000
_FORM_FIELD_PATTERN = re.compile(r"^### (?P<label>[^\n]+)\n\n(?P<value>.*?)(?=^### |\Z)", re.MULTILINE | re.DOTALL)
_CAMPAIGN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
_CAMPAIGN_FIELD = "Campaign or use case"
_SOURCE_FIELD = "Discovery source"
_INSTALL_FIELD = "Install route"
_OUTCOME_FIELD = "Workflow outcome"
_COMPLETED_OUTCOME = "accepted-after-adjustment"
_UNREPORTED = "unreported-or-unrecognized"
_DISCOVERY_SOURCES = frozenset(
    {
        "official-albumentations-docs",
        "albumentations-discord",
        "x-twitter",
        "github",
        "mcp-registry",
        "pypi",
        "skills-sh",
        "other-or-not-sure",
    }
)
_INSTALL_ROUTES = frozenset(
    {
        "claude-desktop-mcpb",
        "uvx",
        "pip",
        "source-checkout",
        "other-or-not-sure",
    }
)
_OUTCOMES = frozenset(
    {
        _COMPLETED_OUTCOME,
        "accepted-first-render",
        "blocked-before-render",
        "unresolved-after-adjustment",
    }
)


@dataclass(frozen=True)
class _CampaignConfig:
    """Validated campaign configuration used by the pure report builder."""

    campaign_id: str
    starts_on: date
    ends_on: date
    destination_url: str
    baseline_unique_visitors: int
    baseline_mcpb_downloads: int
    baseline_completed_loops: int
    baseline_distinct_submitters: int
    target_unique_visitors: int
    target_mcpb_increment: int
    target_completed_loops: int
    target_distinct_submitters: int
    publications: tuple[_Publication, ...]


@dataclass(frozen=True)
class _Publication:
    """Public campaign publication metadata safe to include in reports."""

    channel: str
    url: str
    published_at: datetime


@dataclass(frozen=True)
class _FeedbackSummary:
    """Aggregate issue-form evidence with no issue-level values."""

    attributed_reports: int
    completed_loops: int
    distinct_submitters: int
    completed_without_submitter: int
    invalid_created_at: int
    outside_observed_window: int
    discovery_sources: Mapping[str, int]
    install_routes: Mapping[str, int]
    outcomes: Mapping[str, int]


def build_campaign_activation_report(
    *,
    config: Mapping[str, Any],
    growth_report: Mapping[str, Any],
    workflow_feedback_issues: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a bounded activation report without returning issue-level data."""
    campaign = _parse_config(config)
    as_of = _parse_date(growth_report.get("as_of"), field="growth_report as_of")
    phase = _campaign_phase(as_of=as_of, starts_on=campaign.starts_on, ends_on=campaign.ends_on)
    feedback = _summarize_feedback(
        workflow_feedback_issues,
        campaign_id=campaign.campaign_id,
        starts_on=campaign.starts_on,
        ends_on=campaign.ends_on,
        as_of=as_of,
    )
    observed_publications = tuple(
        publication for publication in campaign.publications if publication.published_at.date() <= as_of
    )
    warnings = _parse_warnings(growth_report.get("warnings", []))
    if not campaign.publications:
        warnings.append("no publication URL and timestamp are recorded")
    elif not observed_publications:
        warnings.append("no recorded publication had occurred by report as_of")
    elif len(observed_publications) != len(campaign.publications):
        future_count = len(campaign.publications) - len(observed_publications)
        warnings.append(f"{future_count} publication(s) occur after report as_of and were ignored")

    github = _required_mapping(growth_report, "github")
    traffic_available = _required_bool(github, "traffic_available")
    traffic_window_days = _count(github.get("traffic_window_days"), field="github traffic_window_days")
    current_unique_visitors = (
        _count(github.get("unique_visitors"), field="github unique_visitors") if traffic_available else None
    )
    reach_target_met = (
        current_unique_visitors is not None and current_unique_visitors >= campaign.target_unique_visitors
    )
    if current_unique_visitors is None:
        warnings.append("qualified reach is unavailable because GitHub Traffic data was not collected")

    release_assets = _required_mapping(growth_report, "release_assets")
    current_mcpb_downloads = _count(
        release_assets.get("mcpb_downloads_total"),
        field="release_assets mcpb_downloads_total",
    )
    mcpb_increment = current_mcpb_downloads - campaign.baseline_mcpb_downloads
    if mcpb_increment < 0:
        warnings.append("MCPB cumulative downloads are below baseline; a release or asset may have been removed")
    mcpb_target_met = mcpb_increment >= campaign.target_mcpb_increment

    completed_increment = feedback.completed_loops - campaign.baseline_completed_loops
    distinct_increment = feedback.distinct_submitters - campaign.baseline_distinct_submitters
    if completed_increment < 0 or distinct_increment < 0:
        warnings.append("voluntary feedback counts are below baseline; a public issue may have been removed")
    if feedback.completed_without_submitter:
        warnings.append(
            f"{feedback.completed_without_submitter} completed loop(s) had no public submitter and were not "
            "included in the distinct-submitter count"
        )
    if feedback.outside_observed_window:
        warnings.append(
            f"{feedback.outside_observed_window} workflow feedback issue(s) fell outside the observed campaign window"
        )
    if feedback.invalid_created_at:
        warnings.append(
            f"{feedback.invalid_created_at} workflow feedback issue(s) had no valid created_at and were ignored"
        )
    activation_target_met = (
        completed_increment >= campaign.target_completed_loops
        and distinct_increment >= campaign.target_distinct_submitters
    )
    targets_met = reach_target_met and mcpb_target_met and activation_target_met

    movement_observed = (
        (current_unique_visitors is not None and current_unique_visitors > campaign.baseline_unique_visitors)
        or current_mcpb_downloads > campaign.baseline_mcpb_downloads
        or feedback.completed_loops > campaign.baseline_completed_loops
        or feedback.distinct_submitters > campaign.baseline_distinct_submitters
    )
    reach_observed = current_unique_visitors is not None
    recommendation = _recommendation(
        phase=phase,
        targets_met=targets_met,
        movement_observed=movement_observed,
        reach_observed=reach_observed,
    )
    next_action = (
        "Wait until aggregate metrics cover the recorded publication before interpreting movement."
        if campaign.publications and not observed_publications
        else _next_action(
            phase=phase,
            recommendation=recommendation,
            reach_target_met=reach_target_met,
            mcpb_target_met=mcpb_target_met,
            activation_target_met=activation_target_met,
        )
    )

    return {
        "schema_version": 1,
        "campaign": {
            "id": campaign.campaign_id,
            "starts_on": campaign.starts_on.isoformat(),
            "ends_on": campaign.ends_on.isoformat(),
            "as_of": as_of.isoformat(),
            "phase": phase,
            "destination_url": campaign.destination_url,
            "publications": [
                {
                    "channel": publication.channel,
                    "url": publication.url,
                    "published_at": publication.published_at.isoformat(),
                }
                for publication in observed_publications
            ],
            "attribution_ready": bool(observed_publications),
        },
        "privacy": {
            "runtime_telemetry": False,
            "reads_local_data": False,
            "contains_issue_level_data": False,
            "issue_data_usage": "aggregate voluntary public issue fields and public timestamps in memory only",
        },
        "qualified_reach": {
            "metric": "github_unique_visitors_rolling_window",
            "traffic_window_days": traffic_window_days,
            "available": traffic_available,
            "baseline_unique_visitors": campaign.baseline_unique_visitors,
            "current_unique_visitors": current_unique_visitors,
            "target_unique_visitors": campaign.target_unique_visitors,
            "target_met": reach_target_met,
        },
        "mcpb_conversion_proxy": {
            "metric": "cumulative_mcpb_downloads_across_releases",
            "baseline_downloads_total": campaign.baseline_mcpb_downloads,
            "current_downloads_total": current_mcpb_downloads,
            "incremental_downloads": mcpb_increment,
            "target_increment": campaign.target_mcpb_increment,
            "target_downloads_total": campaign.baseline_mcpb_downloads + campaign.target_mcpb_increment,
            "target_met": mcpb_target_met,
        },
        "activation": {
            "attributed_reports": feedback.attributed_reports,
            "completed_loops": feedback.completed_loops,
            "completed_loops_since_baseline": completed_increment,
            "distinct_submitters": feedback.distinct_submitters,
            "distinct_submitters_since_baseline": distinct_increment,
            "target_completed_loops": campaign.target_completed_loops,
            "target_distinct_submitters": campaign.target_distinct_submitters,
            "target_met": activation_target_met,
            "discovery_sources": dict(feedback.discovery_sources),
            "install_routes": dict(feedback.install_routes),
            "outcomes": dict(feedback.outcomes),
        },
        "pypi_context": _build_pypi_context(_required_mapping(growth_report, "pypi")),
        "targets_met": targets_met,
        "recommendation": recommendation,
        "next_action": next_action,
        "warnings": _deduplicate(warnings),
    }


def render_campaign_activation_markdown(report: Mapping[str, Any]) -> str:
    """Render an aggregate campaign activation report as Markdown."""
    campaign = _required_mapping(report, "campaign")
    privacy = _required_mapping(report, "privacy")
    reach = _required_mapping(report, "qualified_reach")
    mcpb = _required_mapping(report, "mcpb_conversion_proxy")
    activation = _required_mapping(report, "activation")
    pypi = _required_mapping(report, "pypi_context")
    warning_values = report.get("warnings", [])
    warning_lines = "\n".join(f"- {warning}" for warning in warning_values) if warning_values else "- None"
    runtime_telemetry = "enabled" if privacy["runtime_telemetry"] else "disabled"
    targets_met = "yes" if report["targets_met"] else "no"
    publications = campaign.get("publications")
    publication_lines = _render_publications(publications)
    return (
        "# Campaign Activation Report\n\n"
        f"Campaign: `{campaign['id']}`\n\n"
        f"Window: `{campaign['starts_on']}` to `{campaign['ends_on']}`\n\n"
        f"As of: `{campaign['as_of']}` (`{campaign['phase']}`)\n\n"
        f"Destination: {campaign['destination_url']}\n\n"
        "## Recorded Publications\n\n"
        f"{publication_lines}\n\n"
        f"Runtime telemetry: `{runtime_telemetry}`\n\n"
        "This report is computed from aggregate public distribution metrics, deliberately submitted issue fields, "
        "and public issue timestamps. It does not include issue bodies, titles, URLs, usernames, individual issue "
        "timestamps, datasets, preview artifacts, host logs, or local paths.\n\n"
        "## Qualified Reach\n\n"
        f"- GitHub unique visitors (rolling {reach['traffic_window_days']} days): "
        f"`{_optional_metric(reach['current_unique_visitors'])}`\n"
        f"- Baseline: `{reach['baseline_unique_visitors']}`\n"
        f"- Target: `{reach['target_unique_visitors']}`\n"
        f"- Target met: `{_yes_no(reach['target_met'])}`\n\n"
        "## MCPB Conversion Proxy\n\n"
        f"- Cumulative downloads: `{mcpb['current_downloads_total']}`\n"
        f"- Baseline: `{mcpb['baseline_downloads_total']}`\n"
        f"- Increment: `{mcpb['incremental_downloads']}`\n"
        f"- Target increment: `{mcpb['target_increment']}`\n"
        f"- Target met: `{_yes_no(mcpb['target_met'])}`\n\n"
        "This is a distribution proxy, not proof that an MCP host completed a preview.\n\n"
        "## Product Activation\n\n"
        f"- Attributed reports: `{activation['attributed_reports']}`\n"
        f"- Completed adjustment loops: `{activation['completed_loops']}`\n"
        f"- Distinct submitters: `{activation['distinct_submitters']}`\n"
        f"- Loop target: `{activation['target_completed_loops']}`\n"
        f"- Distinct-submitter target: `{activation['target_distinct_submitters']}`\n"
        f"- Target met: `{_yes_no(activation['target_met'])}`\n\n"
        "### Discovery Sources\n\n"
        f"{_render_counts(activation['discovery_sources'])}\n\n"
        "### Install Routes\n\n"
        f"{_render_counts(activation['install_routes'])}\n\n"
        "### Outcomes\n\n"
        f"{_render_counts(activation['outcomes'])}\n\n"
        "## PyPI Context\n\n"
        f"- Last 7 days: `{pypi['last_7_days']}`\n"
        f"- Previous 7 days: `{pypi['previous_7_days']}`\n"
        f"- Current period complete: `{_yes_no(pypi['last_7_days_complete'])}`\n"
        f"- Previous period complete: `{_yes_no(pypi['previous_7_days_complete'])}`\n"
        f"- Release-excluded median: `{_optional_metric(pypi['release_excluded_median_daily'])}`\n\n"
        "## Decision\n\n"
        f"- All targets met: `{targets_met}`\n"
        f"- Recommendation: `{report['recommendation']}`\n"
        f"- Next action: {report['next_action']}\n\n"
        "## Warnings\n\n"
        f"{warning_lines}\n"
    )


def _parse_config(value: Mapping[str, Any]) -> _CampaignConfig:
    schema_version = _count(value.get("schema_version"), field="campaign schema_version")
    if schema_version != 1:
        msg = "campaign schema_version must be 1"
        raise ValueError(msg)
    campaign_id = value.get("id")
    if not isinstance(campaign_id, str) or _CAMPAIGN_ID_PATTERN.fullmatch(campaign_id) is None:
        msg = "campaign id must be a non-empty lowercase slug"
        raise ValueError(msg)
    starts_on = _parse_date(value.get("starts_on"), field="campaign starts_on")
    ends_on = _parse_date(value.get("ends_on"), field="campaign ends_on")
    if (ends_on - starts_on).days != _CAMPAIGN_WINDOW_DAYS:
        msg = "campaign window must be exactly 14 days"
        raise ValueError(msg)
    destination_url = _https_url(value.get("destination_url"), field="campaign destination_url")
    baseline = _required_mapping(value, "baseline")
    targets = _required_mapping(value, "targets")
    return _CampaignConfig(
        campaign_id=campaign_id,
        starts_on=starts_on,
        ends_on=ends_on,
        destination_url=destination_url,
        baseline_unique_visitors=_count(
            baseline.get("github_unique_visitors"),
            field="baseline github_unique_visitors",
        ),
        baseline_mcpb_downloads=_count(
            baseline.get("mcpb_downloads_total"),
            field="baseline mcpb_downloads_total",
        ),
        baseline_completed_loops=_count(
            baseline.get("completed_loops"),
            field="baseline completed_loops",
        ),
        baseline_distinct_submitters=_count(
            baseline.get("distinct_submitters"),
            field="baseline distinct_submitters",
        ),
        target_unique_visitors=_count(
            targets.get("github_unique_visitors"),
            field="target github_unique_visitors",
        ),
        target_mcpb_increment=_count(
            targets.get("mcpb_downloads_increment"),
            field="target mcpb_downloads_increment",
        ),
        target_completed_loops=_count(
            targets.get("completed_loops"),
            field="target completed_loops",
        ),
        target_distinct_submitters=_count(
            targets.get("distinct_submitters"),
            field="target distinct_submitters",
        ),
        publications=_parse_publications(
            value.get("publications", []),
            starts_on=starts_on,
            ends_on=ends_on,
        ),
    )


def _parse_publications(
    value: Any,
    *,
    starts_on: date,
    ends_on: date,
) -> tuple[_Publication, ...]:
    if not isinstance(value, list):
        msg = "campaign publications must be a list"
        raise TypeError(msg)
    publications: list[_Publication] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            msg = f"campaign publication {index} must be an object"
            raise TypeError(msg)
        channel = item.get("channel")
        if not isinstance(channel, str) or _CAMPAIGN_ID_PATTERN.fullmatch(channel) is None:
            msg = f"campaign publication {index} channel must be a lowercase slug"
            raise ValueError(msg)
        url = _https_url(item.get("url"), field=f"campaign publication {index} url")
        published_at = _iso_datetime(
            item.get("published_at"),
            field=f"campaign publication {index} published_at",
        )
        if not starts_on <= published_at.date() < ends_on:
            msg = f"campaign publication {index} timestamp must fall inside the campaign window"
            raise ValueError(msg)
        identity = (channel, url)
        if identity in seen:
            msg = f"campaign publication {index} duplicates an earlier channel URL"
            raise ValueError(msg)
        seen.add(identity)
        publications.append(_Publication(channel=channel, url=url, published_at=published_at))
    return tuple(publications)


def _summarize_feedback(
    issues: Sequence[Mapping[str, Any]],
    *,
    campaign_id: str,
    starts_on: date,
    ends_on: date,
    as_of: date,
) -> _FeedbackSummary:
    sources: Counter[str] = Counter()
    install_routes: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    completed_submitters: set[str] = set()
    attributed_reports = 0
    completed_loops = 0
    completed_without_submitter = 0
    invalid_created_at = 0
    outside_observed_window = 0
    for index, issue in enumerate(issues):
        if not isinstance(issue, Mapping):
            msg = f"workflow feedback issue {index} must be an object"
            raise TypeError(msg)
        if "workflow-feedback" not in _issue_labels(issue.get("labels", [])):
            continue
        body = issue.get("body")
        if not isinstance(body, str) or len(body) > _ISSUE_BODY_LIMIT:
            continue
        fields = _parse_issue_form(body)
        if fields.get(_CAMPAIGN_FIELD) != campaign_id:
            continue
        created_on = _issue_created_on(issue.get("created_at"))
        if created_on is None:
            invalid_created_at += 1
            continue
        if not starts_on <= created_on < ends_on or created_on > as_of:
            outside_observed_window += 1
            continue
        attributed_reports += 1
        source = _bounded_value(fields.get(_SOURCE_FIELD), allowed=_DISCOVERY_SOURCES)
        install_route = _bounded_value(fields.get(_INSTALL_FIELD), allowed=_INSTALL_ROUTES)
        outcome = _bounded_value(fields.get(_OUTCOME_FIELD), allowed=_OUTCOMES)
        sources[source] += 1
        install_routes[install_route] += 1
        outcomes[outcome] += 1
        if outcome != _COMPLETED_OUTCOME:
            continue
        completed_loops += 1
        submitter = _issue_submitter(issue.get("user"))
        if submitter is None:
            completed_without_submitter += 1
        else:
            completed_submitters.add(submitter)
    return _FeedbackSummary(
        attributed_reports=attributed_reports,
        completed_loops=completed_loops,
        distinct_submitters=len(completed_submitters),
        completed_without_submitter=completed_without_submitter,
        invalid_created_at=invalid_created_at,
        outside_observed_window=outside_observed_window,
        discovery_sources=dict(sorted(sources.items())),
        install_routes=dict(sorted(install_routes.items())),
        outcomes=dict(sorted(outcomes.items())),
    )


def _parse_issue_form(body: str) -> dict[str, str]:
    normalized = body.replace("\r\n", "\n").replace("\r", "\n")
    fields: dict[str, str] = {}
    for match in _FORM_FIELD_PATTERN.finditer(normalized):
        label = match.group("label").strip()
        value = match.group("value").strip()
        first_line = next((line.strip() for line in value.splitlines() if line.strip()), "")
        if first_line not in {"", "_No response_", "No response"}:
            fields[label] = first_line
    return fields


def _issue_labels(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    labels: set[str] = set()
    for item in value:
        if isinstance(item, str) and item:
            labels.add(item)
        elif isinstance(item, Mapping):
            name = item.get("name")
            if isinstance(name, str) and name:
                labels.add(name)
    return labels


def _issue_submitter(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None
    login = value.get("login")
    return login if isinstance(login, str) and login else None


def _issue_created_on(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).date()


def _bounded_value(value: str | None, *, allowed: frozenset[str]) -> str:
    return value if value in allowed else _UNREPORTED


def _campaign_phase(*, as_of: date, starts_on: date, ends_on: date) -> str:
    if as_of < starts_on:
        return "not_started"
    if as_of < ends_on:
        return "active"
    return "ended"


def _recommendation(
    *,
    phase: str,
    targets_met: bool,
    movement_observed: bool,
    reach_observed: bool,
) -> str:
    if targets_met or phase != "ended":
        return "continue"
    if not movement_observed and reach_observed:
        return "stop"
    return "adjust"


def _next_action(
    *,
    phase: str,
    recommendation: str,
    reach_target_met: bool,
    mcpb_target_met: bool,
    activation_target_met: bool,
) -> str:
    if recommendation == "stop":
        return "Stop this campaign and revisit its audience, destination, and value proposition before republishing."
    if reach_target_met and mcpb_target_met and activation_target_met:
        return "Preserve the proven workflow and broaden distribution without changing the activation path."
    if phase == "not_started":
        return "Publish the canonical use case through one recorded channel before interpreting movement."
    if not reach_target_met:
        return "Increase qualified distribution to the canonical use-case page and record real publication URLs."
    if not mcpb_target_met:
        return "Clarify the MCPB and uvx install choices while keeping the same campaign destination."
    return "Reduce first-preview or feedback friction before expanding the campaign to another use case."


def _build_pypi_context(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "metric": str(value.get("metric", "downloads_without_mirrors")),
        "last_7_days": _count(value.get("last_7_days"), field="pypi last_7_days"),
        "previous_7_days": _count(value.get("previous_7_days"), field="pypi previous_7_days"),
        "last_7_days_complete": _required_bool(value, "last_7_days_complete"),
        "previous_7_days_complete": _required_bool(value, "previous_7_days_complete"),
        "release_excluded_median_daily": _optional_number(
            value.get("release_excluded_median_daily"),
            field="pypi release_excluded_median_daily",
        ),
    }


def _required_mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        msg = f"{key} must be an object"
        raise TypeError(msg)
    return item


def _required_bool(value: Mapping[str, Any], key: str) -> bool:
    item = value.get(key)
    if not isinstance(item, bool):
        msg = f"{key} must be a boolean"
        raise TypeError(msg)
    return item


def _count(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field} must be an integer"
        raise TypeError(msg)
    if value < 0:
        msg = f"{field} must be non-negative"
        raise ValueError(msg)
    return value


def _optional_number(value: Any, *, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = f"{field} must be a number or null"
        raise TypeError(msg)
    if value < 0:
        msg = f"{field} must be non-negative"
        raise ValueError(msg)
    return float(value)


def _parse_date(value: Any, *, field: str) -> date:
    if not isinstance(value, str):
        msg = f"{field} must be an ISO date"
        raise TypeError(msg)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        msg = f"{field} must be an ISO date"
        raise ValueError(msg) from exc


def _iso_datetime(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str):
        msg = f"{field} must be an ISO timestamp with a timezone"
        raise TypeError(msg)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        msg = f"{field} must be an ISO timestamp with a timezone"
        raise ValueError(msg) from exc
    if parsed.tzinfo is None:
        msg = f"{field} must be an ISO timestamp with a timezone"
        raise ValueError(msg)
    return parsed.astimezone(timezone.utc)


def _https_url(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        msg = f"{field} must be an HTTPS URL"
        raise TypeError(msg)
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username is not None or parsed.password is not None:
        msg = f"{field} must be an HTTPS URL without credentials"
        raise ValueError(msg)
    return value


def _parse_warnings(value: Any) -> list[str]:
    if not isinstance(value, list):
        msg = "growth report warnings must be a list of strings"
        raise TypeError(msg)
    warnings: list[str] = []
    for item in value:
        if not isinstance(item, str):
            msg = "growth report warnings must be a list of strings"
            raise TypeError(msg)
        warnings.append(item)
    return warnings


def _deduplicate(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _render_counts(value: Any) -> str:
    if not isinstance(value, Mapping):
        msg = "aggregate counts must be an object"
        raise TypeError(msg)
    return "\n".join(f"- `{name}`: `{count}`" for name, count in value.items()) if value else "- None reported"


def _render_publications(value: Any) -> str:
    if not isinstance(value, list):
        msg = "campaign publications must be a list"
        raise TypeError(msg)
    if not value:
        return "- None recorded; do not attribute aggregate movement to this campaign."
    lines: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            msg = "campaign publication must be an object"
            raise TypeError(msg)
        lines.append(f"- `{item['channel']}` at `{item['published_at']}`: {item['url']}")
    return "\n".join(lines)


def _optional_metric(value: Any) -> str:
    return "unavailable" if value is None else str(value)


def _yes_no(value: Any) -> str:
    return "yes" if value else "no"
