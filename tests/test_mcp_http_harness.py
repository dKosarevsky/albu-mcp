from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.types import Message

from tests.support.mcp_http import (
    RoundRobinMcpDispatcher,
    run_loopback_mcp_cluster,
    sanitize_mcp_headers,
)


def _backend(label: str, events: list[str]) -> Starlette:
    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        del app
        events.append(f"{label}:start")
        yield
        events.append(f"{label}:stop")

    async def endpoint(request: Request) -> PlainTextResponse:
        del request
        return PlainTextResponse(label)

    return Starlette(routes=[Route("/mcp", endpoint, methods=["POST"])], lifespan=lifespan)


async def _request(dispatcher: RoundRobinMcpDispatcher) -> bytes:
    incoming: list[Message] = [{"type": "http.request", "body": b"{}", "more_body": False}]
    messages = iter(incoming)
    sent: list[Message] = []

    async def receive() -> Message:
        return next(messages)

    async def send(message: Message) -> None:
        sent.append(message)

    await dispatcher(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/mcp",
            "raw_path": b"/mcp",
            "query_string": b"",
            "headers": [
                (b"mcp-protocol-version", b"2026-07-28"),
                (b"mcp-method", b"tools/list"),
            ],
            "client": ("127.0.0.1", 49152),
            "server": ("127.0.0.1", 8000),
        },
        receive,
        send,
    )
    return b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )


def test_dispatcher_routes_consecutive_requests_round_robin() -> None:
    async def exercise() -> tuple[list[bytes], RoundRobinMcpDispatcher]:
        dispatcher = RoundRobinMcpDispatcher([_backend("zero", []), _backend("one", [])])
        bodies = [await _request(dispatcher) for _ in range(3)]
        return bodies, dispatcher

    bodies, dispatcher = asyncio.run(exercise())

    assert bodies == [b"zero", b"one", b"zero"]
    assert [item.backend_index for item in dispatcher.trace] == [0, 1, 0]
    assert [item.status for item in dispatcher.trace] == [200, 200, 200]


def test_trace_keeps_only_bounded_mcp_headers() -> None:
    headers = sanitize_mcp_headers(
        [
            (b"authorization", b"Bearer secret"),
            (b"cookie", b"session=secret"),
            (b"mcp-protocol-version", b"2026-07-28"),
            (b"mcp-method", b"tools/call"),
            (b"mcp-name", b"x" * 200),
            (b"mcp-session-id", b"opaque-secret"),
        ]
    )

    assert headers == (
        ("mcp-protocol-version", "2026-07-28"),
        ("mcp-method", "tools/call"),
        ("mcp-name", "x" * 128),
        ("mcp-session-id", "<present>"),
    )


def test_loopback_cluster_fans_out_backend_lifespans() -> None:
    async def exercise() -> list[str]:
        events: list[str] = []
        async with run_loopback_mcp_cluster([_backend("zero", events), _backend("one", events)]):
            assert events == ["zero:start", "one:start"]
        return events

    assert asyncio.run(exercise()) == ["zero:start", "one:start", "one:stop", "zero:stop"]
