"""Network sources for privacy-safe public package and repository metrics."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

_REQUEST_TIMEOUT_SECONDS = 30
_REPOSITORY_PART_COUNT = 2
_GITHUB_PAGE_SIZE = 100
_USER_AGENT = "albumentationsx-mcp-public-metrics/1"


def fetch_live_growth_payload(*, package: str, repository: str, token: str | None) -> dict[str, Any]:
    """Fetch aggregate PyPI, GitHub repository, release, and Traffic data."""
    owner, name = _repository_parts(repository)
    package_segment = quote(package, safe="")
    repository_segment = f"{quote(owner, safe='')}/{quote(name, safe='')}"
    github_headers = _github_headers(token)

    payload: dict[str, Any] = {
        "pypistats": _fetch_json(
            f"https://pypistats.org/api/packages/{package_segment}/overall?mirrors=false",
            headers={"Accept": "application/json"},
        ),
        "github_repository": _fetch_json(
            f"https://api.github.com/repos/{repository_segment}",
            headers=github_headers,
        ),
        "github_releases": _fetch_github_releases(repository_segment, headers=github_headers),
        "source_errors": {},
        "collected_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    if token is None:
        payload["github_views"] = None
        payload["github_referrers"] = None
        payload["source_errors"] = {"github_traffic": "GH_TOKEN or GITHUB_TOKEN is not set"}
        return payload

    views, views_error = _optional_fetch_json(
        f"https://api.github.com/repos/{repository_segment}/traffic/views",
        headers=github_headers,
    )
    referrers, referrers_error = _optional_fetch_json(
        f"https://api.github.com/repos/{repository_segment}/traffic/popular/referrers",
        headers=github_headers,
    )
    payload["github_views"] = views
    payload["github_referrers"] = referrers
    errors = [error for error in (views_error, referrers_error) if error]
    if errors:
        payload["source_errors"] = {"github_traffic": "; ".join(errors)}
    return payload


def fetch_workflow_feedback_issues(*, repository: str, token: str | None) -> list[dict[str, Any]]:
    """Fetch every public workflow-feedback issue while excluding pull requests."""
    owner, name = _repository_parts(repository)
    repository_segment = f"{quote(owner, safe='')}/{quote(name, safe='')}"
    headers = _github_headers(token)
    issues: list[dict[str, Any]] = []
    page = 1
    while True:
        value = _fetch_json(
            f"https://api.github.com/repos/{repository_segment}/issues"
            f"?state=all&labels=workflow-feedback&per_page={_GITHUB_PAGE_SIZE}&page={page}",
            headers=headers,
        )
        if not isinstance(value, list):
            msg = "GitHub issues response must be a list"
            raise TypeError(msg)
        for index, item in enumerate(value):
            if not isinstance(item, Mapping):
                msg = f"GitHub issue {index} on page {page} must be an object"
                raise TypeError(msg)
            if "pull_request" not in item:
                issues.append(dict(item))
        if len(value) < _GITHUB_PAGE_SIZE:
            return issues
        page += 1


def safe_error_message(exc: BaseException) -> str:
    """Return a bounded network error without response bodies or credentials."""
    if isinstance(exc, HTTPError):
        return f"GitHub or PyPI API returned HTTP {exc.code}"
    if isinstance(exc, URLError):
        return f"network request failed: {exc.reason}"
    return str(exc)


def _fetch_json(url: str, *, headers: Mapping[str, str]) -> Any:
    request_headers = {"User-Agent": _USER_AGENT, **headers}
    request = Request(url, headers=request_headers)  # noqa: S310
    with urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _fetch_github_releases(repository_segment: str, *, headers: Mapping[str, str]) -> list[Any]:
    releases: list[Any] = []
    page = 1
    while True:
        value = _fetch_json(
            f"https://api.github.com/repos/{repository_segment}/releases?per_page={_GITHUB_PAGE_SIZE}&page={page}",
            headers=headers,
        )
        if not isinstance(value, list):
            msg = "GitHub releases response must be a list"
            raise TypeError(msg)
        releases.extend(value)
        if len(value) < _GITHUB_PAGE_SIZE:
            return releases
        page += 1


def _optional_fetch_json(url: str, *, headers: Mapping[str, str]) -> tuple[Any | None, str | None]:
    try:
        return _fetch_json(url, headers=headers), None
    except (HTTPError, URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        return None, safe_error_message(exc)


def _repository_parts(value: str) -> tuple[str, str]:
    parts = value.split("/")
    if len(parts) != _REPOSITORY_PART_COUNT or not all(part and part not in {".", ".."} for part in parts):
        msg = "repository must use the owner/name form"
        raise ValueError(msg)
    return parts[0], parts[1]


def _github_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
