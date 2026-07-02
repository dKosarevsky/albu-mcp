"""Build or run a host setup probe before first-preview work."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import get_args

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.host_setup import (
    DEFAULT_ALLOWED_ROOT,
    DEFAULT_ARTIFACT_ROOT,
    build_host_setup_probe,
    render_host_setup_probe_markdown,
)


def main() -> None:
    """CLI entrypoint for host setup probes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Probe the current machine instead of rendering a template.",
    )
    parser.add_argument("--host", choices=get_args(HostName), default=None)
    parser.add_argument("--allowed-root", type=Path, default=DEFAULT_ALLOWED_ROOT)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    probe = build_host_setup_probe(
        live=args.live,
        allowed_root=args.allowed_root,
        artifact_root=args.artifact_root,
        host=args.host,
    )
    content = (
        json.dumps(probe, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_host_setup_probe_markdown(probe)
    )
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
