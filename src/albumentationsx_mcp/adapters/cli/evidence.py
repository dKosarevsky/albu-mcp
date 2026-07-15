"""Composition of capture and guidance evidence CLI adapters."""

from __future__ import annotations

import argparse
import sys

from pydantic import ValidationError

from albumentationsx_mcp.adapters.cli.contracts import CliGroupSurface
from albumentationsx_mcp.adapters.cli.evidence_capture import (
    CAPTURE_COMMANDS,
    CAPTURE_HANDLERS,
    register_capture_parsers,
)
from albumentationsx_mcp.adapters.cli.evidence_guidance import (
    GUIDANCE_COMMANDS,
    GUIDANCE_HANDLERS,
    register_guidance_parsers,
)

SURFACE = CliGroupSurface(group="evidence", commands=CAPTURE_COMMANDS + GUIDANCE_COMMANDS)


def build_evidence_parser() -> argparse.ArgumentParser:
    """Build the complete evidence command parser."""
    parser = argparse.ArgumentParser(description="Record and validate real MCP host evidence.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_capture_parsers(subparsers)
    register_guidance_parsers(subparsers)
    return parser


def run_evidence(argv: list[str]) -> None:
    """Run an evidence command."""
    args = build_evidence_parser().parse_args(argv)
    try:
        sys.stdout.write(handle_evidence_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def handle_evidence_command(args: argparse.Namespace) -> str:
    """Execute one parsed evidence command."""
    return {**CAPTURE_HANDLERS, **GUIDANCE_HANDLERS}[args.command](args)
