"""Root CLI dispatch and server fallback."""

from __future__ import annotations

import sys

from albumentationsx_mcp.adapters.cli.registration import GROUP_RUNNERS
from albumentationsx_mcp.adapters.cli.runtime import run_server


def main(argv: list[str] | None = None) -> None:
    """Run a grouped operator command or the default MCP server."""
    resolved_argv = sys.argv[1:] if argv is None else argv
    if resolved_argv and resolved_argv[0] in GROUP_RUNNERS:
        run_cli_subcommand(name=resolved_argv[0], argv=resolved_argv[1:])
        return
    run_server(resolved_argv)


def run_cli_subcommand(*, name: str, argv: list[str]) -> None:
    """Dispatch one recognized top-level command group."""
    GROUP_RUNNERS[name](argv)
