"""Server launch and host-readiness CLI adapters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

from albumentationsx_mcp.adapters.cli.contracts import CliGroupSurface
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.host_setup import (
    DEFAULT_ALLOWED_ROOT,
    DEFAULT_ARTIFACT_ROOT,
    build_host_setup_probe,
    render_host_setup_probe_markdown,
)
from albumentationsx_mcp.host_trust import build_host_trust_dashboard, render_host_trust_dashboard_markdown
from albumentationsx_mcp.server import ServerSettings, create_mcp_server, settings_from_environment

HOST_SURFACE = CliGroupSurface(group="host", commands=("setup-probe", "next-action"))


def build_server_parser() -> argparse.ArgumentParser:
    """Build the default MCP server parser."""
    parser = argparse.ArgumentParser(description="Run the AlbumentationsX MCP server.")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--artifact-root", type=Path, default=None)
    parser.add_argument("--allowed-root", action="append", type=Path, default=None)
    return parser


def run_server(argv: list[str]) -> None:
    """Run the MCP server."""
    args = build_server_parser().parse_args(argv)
    settings = settings_from_environment()
    if args.artifact_root is not None or args.allowed_root is not None:
        settings = ServerSettings(
            allowed_roots=args.allowed_root or settings.allowed_roots,
            artifact_root=args.artifact_root or settings.artifact_root,
        )

    server = create_mcp_server(settings)
    server.run(transport=args.transport)


def build_host_parser() -> argparse.ArgumentParser:
    """Build the host-readiness command parser."""
    parser = argparse.ArgumentParser(description="Inspect host setup readiness before real MCP evidence runs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_probe = subparsers.add_parser("setup-probe", help="Build or run a host setup readiness probe.")
    setup_probe.add_argument("--host", choices=get_args(HostName), default=None)
    setup_probe.add_argument("--live", action="store_true")
    setup_probe.add_argument("--allowed-root", type=Path, default=DEFAULT_ALLOWED_ROOT)
    setup_probe.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    setup_probe.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    setup_probe.add_argument("--output", type=Path, default=None)

    next_action = subparsers.add_parser("next-action", help="Show the next real evidence action per MCP host.")
    next_action.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    next_action.add_argument("--host", choices=get_args(HostName), default=None)
    next_action.add_argument("--include-session", action="store_true")
    next_action.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    next_action.add_argument("--output", type=Path, default=None)
    return parser


def run_host(argv: list[str]) -> None:
    """Run a host-readiness command."""
    args = build_host_parser().parse_args(argv)
    try:
        sys.stdout.write(handle_host_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def handle_host_command(args: argparse.Namespace) -> str:
    """Execute one parsed host-readiness command."""
    if args.command == "next-action":
        return handle_host_next_action(args)
    if args.command != "setup-probe":
        message = f"unsupported host command: {args.command}"
        raise ValueError(message)
    probe = build_host_setup_probe(
        host=args.host,
        live=args.live,
        allowed_root=args.allowed_root,
        artifact_root=args.artifact_root,
    )
    if args.format == "json":
        content = json.dumps(probe, indent=2, sort_keys=True) + "\n"
    elif args.format == "markdown":
        content = render_host_setup_probe_markdown(probe)
    else:
        content = (
            f"host setup-probe {probe['probe_status']} "
            f"(hosts={probe['summary']['host_count']}, next_action={probe['next_action']})\n"
        )
    if args.output is None:
        return content
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    return f"wrote host setup-probe to {args.output}\n"


def handle_host_next_action(args: argparse.Namespace) -> str:
    """Execute the host trust-dashboard shortcut."""
    report = build_host_trust_dashboard(path=args.path, host=args.host, include_session=args.include_session)
    if args.format == "json":
        content = json.dumps(report, indent=2, sort_keys=True) + "\n"
    elif args.format == "markdown":
        content = render_host_trust_dashboard_markdown(report)
    else:
        content = (
            f"host next-action {report['dashboard_status']} "
            f"(next_host={report['next_host'] or 'none'}, next='{report['next_command']}')\n"
        )
    if args.output is None:
        return content
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    return f"wrote host trust dashboard to {args.output}\n"
