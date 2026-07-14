"""Export a privacy-safe aggregate package and repository growth report."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from albumentationsx_mcp.growth import build_growth_report, render_growth_report_markdown

_DEFAULT_PACKAGE = "albumentationsx-mcp"
_DEFAULT_REPOSITORY = "dKosarevsky/albu-mcp"
_REQUEST_TIMEOUT_SECONDS = 30
_REPOSITORY_PART_COUNT = 2
_USER_AGENT = "albumentationsx-mcp-growth-report/1"


def main() -> None:
    """CLI entrypoint for live and reproducible offline reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", dest="input_path", type=Path, default=None)
    parser.add_argument("--package", default=_DEFAULT_PACKAGE)
    parser.add_argument("--repository", default=_DEFAULT_REPOSITORY)
    parser.add_argument("--baseline-days", type=int, default=28)
    parser.add_argument("--release-exclusion-days", type=int, default=2)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    try:
        payload = (
            _load_payload(args.input_path)
            if args.input_path
            else _fetch_live_payload(
                package=args.package,
                repository=args.repository,
            )
        )
        report = build_growth_report(
            payload,
            baseline_days=args.baseline_days,
            release_exclusion_days=args.release_exclusion_days,
        )
        content = (
            render_growth_report_markdown(report)
            if args.format == "markdown"
            else json.dumps(report, indent=2, sort_keys=True) + "\n"
        )
    except (HTTPError, URLError, OSError, TimeoutError, TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"growth report failed: {_safe_error_message(exc)}\n")
        raise SystemExit(1) from exc

    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _load_payload(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        msg = "growth report input must be a JSON object"
        raise TypeError(msg)
    return value


def _fetch_live_payload(*, package: str, repository: str) -> dict[str, Any]:
    owner, name = _repository_parts(repository)
    package_segment = quote(package, safe="")
    repository_segment = f"{quote(owner, safe='')}/{quote(name, safe='')}"
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
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
        "github_releases": _fetch_json(
            f"https://api.github.com/repos/{repository_segment}/releases?per_page=100",
            headers=github_headers,
        ),
        "source_errors": {},
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


def _fetch_json(url: str, *, headers: Mapping[str, str]) -> Any:
    request_headers = {"User-Agent": _USER_AGENT, **headers}
    request = Request(url, headers=request_headers)  # noqa: S310
    with urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _optional_fetch_json(url: str, *, headers: Mapping[str, str]) -> tuple[Any | None, str | None]:
    try:
        return _fetch_json(url, headers=headers), None
    except (HTTPError, URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        return None, _safe_error_message(exc)


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


def _safe_error_message(exc: BaseException) -> str:
    if isinstance(exc, HTTPError):
        return f"GitHub or PyPI API returned HTTP {exc.code}"
    if isinstance(exc, URLError):
        return f"network request failed: {exc.reason}"
    return str(exc)


if __name__ == "__main__":
    main()
