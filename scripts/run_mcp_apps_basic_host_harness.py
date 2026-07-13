"""Run a loopback-only streamable HTTP server for the official MCP Apps basic host."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlsplit

import uvicorn
from starlette.middleware.cors import CORSMiddleware

from albumentationsx_mcp.server import ServerSettings, create_mcp_server

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
_MAX_PORT = 65535
_INVALID_ORIGIN_MESSAGE = "allowed origin must be one loopback HTTP origin"
_INVALID_PORT_MESSAGE = "--port must be between 1 and 65535"


def validate_loopback_origin(origin: str) -> str:
    """Validate one exact browser origin for the local test harness."""
    parsed = urlsplit(origin)
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(_INVALID_ORIGIN_MESSAGE) from exc
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in _LOOPBACK_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or not parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(_INVALID_ORIGIN_MESSAGE)
    return origin


def build_basic_host_app(
    *,
    allowed_roots: list[Path],
    artifact_root: Path,
    allowed_origin: str,
) -> CORSMiddleware:
    """Build the bounded server with CORS limited to the official local host."""
    origin = validate_loopback_origin(allowed_origin)
    server = create_mcp_server(
        ServerSettings(
            allowed_roots=[path.resolve() for path in allowed_roots],
            artifact_root=artifact_root.resolve(),
        ),
    )
    return CORSMiddleware(
        server.streamable_http_app(),
        allow_origins=[origin],
        allow_credentials=False,
        allow_methods=["DELETE", "GET", "POST"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the development-only host harness."""
    parser = argparse.ArgumentParser(
        description="Run AlbumentationsX MCP for the official MCP Apps basic host.",
    )
    parser.add_argument("--allowed-root", action="append", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--allowed-origin", default="http://localhost:8080")
    parser.add_argument("--host", choices=sorted(_LOOPBACK_HOSTS), default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3001)
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the loopback-only development harness."""
    args = build_parser().parse_args(argv)
    if not 1 <= args.port <= _MAX_PORT:
        raise SystemExit(_INVALID_PORT_MESSAGE)
    app = build_basic_host_app(
        allowed_roots=args.allowed_root,
        artifact_root=args.artifact_root,
        allowed_origin=args.allowed_origin,
    )
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
