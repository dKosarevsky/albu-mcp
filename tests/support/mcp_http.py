from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator, Iterable, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

import uvicorn

if TYPE_CHECKING:
    from starlette.applications import Starlette
    from starlette.types import Message, Receive, Scope, Send

_MAX_MCP_HEADER_VALUE = 128
_SENSITIVE_MCP_HEADERS = frozenset({"mcp-session-id"})


@dataclass(frozen=True)
class HttpRequestTrace:
    """One privacy-safe observation from the test-only HTTP dispatcher."""

    backend_index: int
    method: str
    path: str
    mcp_headers: tuple[tuple[str, str], ...]
    status: int


@dataclass(frozen=True)
class LoopbackMcpCluster:
    """Running loopback endpoint and its bounded trace."""

    url: str
    dispatcher: RoundRobinMcpDispatcher

    @property
    def trace(self) -> tuple[HttpRequestTrace, ...]:
        return tuple(self.dispatcher.trace)


def sanitize_mcp_headers(headers: Iterable[tuple[bytes, bytes]]) -> tuple[tuple[str, str], ...]:
    """Keep only bounded MCP metadata and redact opaque session identifiers."""
    safe: list[tuple[str, str]] = []
    for raw_name, raw_value in headers:
        name = raw_name.decode("latin-1").lower()
        if not name.startswith("mcp-"):
            continue
        value = (
            "<present>"
            if name in _SENSITIVE_MCP_HEADERS
            else raw_value.decode("latin-1")[:_MAX_MCP_HEADER_VALUE]
        )
        safe.append((name, value))
    return tuple(safe)


class RoundRobinMcpDispatcher:
    """Fan out lifespan and route each HTTP request to one independent backend."""

    def __init__(self, apps: Sequence[Starlette]) -> None:
        if not apps:
            message = "at least one backend app is required"
            raise ValueError(message)
        self._apps = tuple(apps)
        self._next_backend = 0
        self._routing_lock = asyncio.Lock()
        self.trace: list[HttpRequestTrace] = []

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self._serve_lifespan(receive, send)
            return
        if scope["type"] != "http":
            raise RuntimeError(f"unsupported ASGI scope: {scope['type']}")

        backend_index = await self._choose_backend()
        status: int | None = None

        async def traced_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
            await send(message)

        try:
            await self._apps[backend_index](scope, receive, traced_send)
        finally:
            self.trace.append(
                HttpRequestTrace(
                    backend_index=backend_index,
                    method=str(scope.get("method", "")),
                    path=str(scope.get("path", "")),
                    mcp_headers=sanitize_mcp_headers(scope.get("headers", [])),
                    status=status if status is not None else 500,
                )
            )

    async def _choose_backend(self) -> int:
        async with self._routing_lock:
            selected = self._next_backend
            self._next_backend = (selected + 1) % len(self._apps)
            return selected

    async def _serve_lifespan(self, receive: Receive, send: Send) -> None:
        startup = await receive()
        _require_message_type(startup, "lifespan.startup")
        started = False
        try:
            async with AsyncExitStack() as stack:
                for app in self._apps:
                    await stack.enter_async_context(app.router.lifespan_context(app))
                started = True
                await send({"type": "lifespan.startup.complete"})
                shutdown = await receive()
                _require_message_type(shutdown, "lifespan.shutdown")
            await send({"type": "lifespan.shutdown.complete"})
        except Exception as exc:
            phase = "shutdown" if started else "startup"
            await send({"type": f"lifespan.{phase}.failed", "message": type(exc).__name__})
            raise


@asynccontextmanager
async def run_loopback_mcp_cluster(
    apps: Sequence[Starlette],
    *,
    startup_timeout: float = 5.0,
    shutdown_timeout: float = 5.0,
) -> AsyncIterator[LoopbackMcpCluster]:
    """Serve the supplied apps on a pre-bound loopback socket."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    listener.setblocking(False)  # noqa: FBT003
    port = int(listener.getsockname()[1])
    dispatcher = RoundRobinMcpDispatcher(apps)
    server = uvicorn.Server(
        uvicorn.Config(dispatcher, log_level="error", access_log=False, lifespan="on")
    )
    serve_task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        await asyncio.wait_for(_wait_until_started(server, serve_task), timeout=startup_timeout)
        yield LoopbackMcpCluster(url=f"http://127.0.0.1:{port}/mcp", dispatcher=dispatcher)
    finally:
        server.should_exit = True
        try:
            await asyncio.wait_for(serve_task, timeout=shutdown_timeout)
        except TimeoutError:
            serve_task.cancel()
            await asyncio.gather(serve_task, return_exceptions=True)
            message = "loopback MCP cluster did not stop within the timeout"
            raise RuntimeError(message) from None
        finally:
            listener.close()


async def _wait_until_started(server: uvicorn.Server, serve_task: asyncio.Task[None]) -> None:
    while not server.started:
        if serve_task.done():
            await serve_task
        await asyncio.sleep(0.01)


def _require_message_type(message: Message, expected: str) -> None:
    if message["type"] != expected:
        error = f"expected {expected}"
        raise RuntimeError(error)
