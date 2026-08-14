"""Export a privacy-safe classification campaign activation report."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from albumentationsx_mcp.campaign_activation import (
    build_campaign_activation_report,
    render_campaign_activation_markdown,
)
from albumentationsx_mcp.growth import build_growth_report
from scripts.public_metrics_sources import (
    fetch_live_growth_payload,
    fetch_workflow_feedback_issues,
    safe_error_message,
)

_DEFAULT_CONFIG = Path("docs/campaigns/classification-robustness-2026-08.json")
_DEFAULT_PACKAGE = "albumentationsx-mcp"
_DEFAULT_REPOSITORY = "dKosarevsky/albu-mcp"


def main() -> None:
    """CLI entrypoint for live and reproducible offline activation reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", dest="input_path", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    parser.add_argument("--package", default=_DEFAULT_PACKAGE)
    parser.add_argument("--repository", default=_DEFAULT_REPOSITORY)
    parser.add_argument("--baseline-days", type=int, default=28)
    parser.add_argument("--release-exclusion-days", type=int, default=2)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    try:
        payload = (
            _load_mapping(args.input_path, description="campaign activation input")
            if args.input_path is not None
            else _fetch_live_input(
                config_path=args.config,
                package=args.package,
                repository=args.repository,
                baseline_days=args.baseline_days,
                release_exclusion_days=args.release_exclusion_days,
            )
        )
        report = build_campaign_activation_report(
            config=_required_mapping(payload, "config"),
            growth_report=_required_mapping(payload, "growth_report"),
            workflow_feedback_issues=_required_issue_list(payload, "workflow_feedback_issues"),
        )
        content = (
            render_campaign_activation_markdown(report)
            if args.format == "markdown"
            else json.dumps(report, indent=2, sort_keys=True) + "\n"
        )
    except (HTTPError, URLError, OSError, TimeoutError, TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"campaign activation report failed: {safe_error_message(exc)}\n")
        raise SystemExit(1) from exc

    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _fetch_live_input(
    *,
    config_path: Path,
    package: str,
    repository: str,
    baseline_days: int,
    release_exclusion_days: int,
) -> dict[str, Any]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    growth_payload = fetch_live_growth_payload(package=package, repository=repository, token=token)
    return {
        "config": _load_mapping(config_path, description="campaign config"),
        "growth_report": build_growth_report(
            growth_payload,
            baseline_days=baseline_days,
            release_exclusion_days=release_exclusion_days,
        ),
        "workflow_feedback_issues": fetch_workflow_feedback_issues(repository=repository, token=token),
    }


def _load_mapping(path: Path, *, description: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        msg = f"{description} must be a JSON object"
        raise TypeError(msg)
    return value


def _required_mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        msg = f"{key} must be an object"
        raise TypeError(msg)
    return item


def _required_issue_list(value: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    item = value.get(key)
    if not isinstance(item, list):
        msg = f"{key} must be a list"
        raise TypeError(msg)
    issues: list[Mapping[str, Any]] = []
    for index, issue in enumerate(item):
        if not isinstance(issue, Mapping):
            msg = f"{key} item {index} must be an object"
            raise TypeError(msg)
        issues.append(issue)
    return issues


if __name__ == "__main__":
    main()
