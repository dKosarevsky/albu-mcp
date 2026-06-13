"""Command-line entry point for the AlbumentationsX MCP server."""

from __future__ import annotations

import argparse
from pathlib import Path

from albumentationsx_mcp.server import ServerSettings, create_mcp_server, settings_from_environment


def main() -> None:
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="Run the AlbumentationsX MCP server.")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--artifact-root", type=Path, default=None)
    parser.add_argument("--allowed-root", action="append", type=Path, default=None)
    args = parser.parse_args()

    settings = settings_from_environment()
    if args.artifact_root is not None or args.allowed_root is not None:
        settings = ServerSettings(
            allowed_roots=args.allowed_root or settings.allowed_roots,
            artifact_root=args.artifact_root or settings.artifact_root,
        )

    server = create_mcp_server(settings)
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
