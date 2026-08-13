"""Export a privacy-safe aggregate package and repository growth report."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from albumentationsx_mcp.growth import build_growth_report, render_growth_report_markdown
from scripts.public_metrics_sources import fetch_live_growth_payload, safe_error_message

_DEFAULT_PACKAGE = "albumentationsx-mcp"
_DEFAULT_REPOSITORY = "dKosarevsky/albu-mcp"


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
            else fetch_live_growth_payload(
                package=args.package,
                repository=args.repository,
                token=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"),
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
        sys.stderr.write(f"growth report failed: {safe_error_message(exc)}\n")
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


if __name__ == "__main__":
    main()
