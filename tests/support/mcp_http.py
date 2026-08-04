from __future__ import annotations

import asyncio
import re
import socket
from collections import deque
from collections.abc import AsyncIterator, Iterable, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

import uvicorn

if TYPE_CHECKING:
    from starlette.applications import Starlette
    from starlette.types import Message, Receive, Scope, Send

_MAX_TRACE_ENTRIES = 256
_MAX_HTTP_METHOD_VALUE = 16
_MAX_HTTP_PATH_VALUE = 256
_MAX_MCP_HEADER_COUNT = 4
_MAX_MCP_HEADER_VALUE = 128
_MCP_HEADER_ALLOWLIST = frozenset({"mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id"})
_SENSITIVE_MCP_HEADERS = frozenset({"mcp-session-id"})
_SAFE_MCP_NAME = re.compile(r"[A-Za-z0-9_.-]+\Z")


@dataclass(frozen=True)
class HttpRequestTrace:
    """One privacy-safe observation from the test-only HTTP dispatcher."""

    backend_index: int
    method: str
    path: str
    mcp_headers: tuple[tuple[str, str], ...]
    status: int
    method_truncated: bool = False
    path_truncated: bool = False
    mcp_headers_truncated: bool = False


@dataclass(frozen=True)
class LoopbackMcpCluster:
    """Running loopback endpoint and its bounded trace."""

    url: str
    dispatcher: RoundRobinMcpDispatcher

    @property
    def trace(self) -> tuple[HttpRequestTrace, ...]:
        return self.dispatcher.trace

    @property
    def trace_overflow_count(self) -> int:
        return self.dispatcher.trace_overflow_count


def sanitize_mcp_headers(headers: Iterable[tuple[bytes, bytes]]) -> tuple[tuple[str, str], ...]:
    """Keep only bounded MCP metadata and redact opaque session identifiers."""
    safe, _ = _sanitize_mcp_headers(headers)
    return safe


def _sanitize_mcp_headers(
    headers: Iterable[tuple[bytes, bytes]],
) -> tuple[tuple[tuple[str, str], ...], bool]:
    safe: list[tuple[str, str]] = []
    seen: set[str] = set()
    truncated = False
    for raw_name, raw_value in headers:
        name = raw_name.decode("latin-1").lower()
        if name not in _MCP_HEADER_ALLOWLIST:
            continue
        if name in seen or len(safe) >= _MAX_MCP_HEADER_COUNT:
            truncated = True
            continue
        seen.add(name)
        value, value_truncated = _sanitize_mcp_header_value(name, raw_value)
        truncated = truncated or value_truncated
        safe.append((name, value))
    return tuple(safe), truncated


def _sanitize_mcp_header_value(name: str, raw_value: bytes) -> tuple[str, bool]:
    if name in _SENSITIVE_MCP_HEADERS:
        return "<present>", False
    value = raw_value.decode("latin-1")
    if name == "mcp-name" and _SAFE_MCP_NAME.fullmatch(value) is None:
        return "<redacted>", True
    return value[:_MAX_MCP_HEADER_VALUE], len(value) > _MAX_MCP_HEADER_VALUE


class RoundRobinMcpDispatcher:
    """Fan out lifespan and route each HTTP request to one independent backend."""

    def __init__(
        self,
        apps: Sequence[Starlette],
        *,
        max_trace_entries: int = _MAX_TRACE_ENTRIES,
    ) -> None:
        if not apps:
            message = "at least one backend app is required"
            raise ValueError(message)
        if not 1 <= max_trace_entries <= _MAX_TRACE_ENTRIES:
            message = f"max_trace_entries must be between 1 and {_MAX_TRACE_ENTRIES}"
            raise ValueError(message)
        self._apps = tuple(apps)
        self._next_backend = 0
        self._routing_lock = asyncio.Lock()
        self._max_trace_entries = max_trace_entries
        self._trace: deque[HttpRequestTrace] = deque(maxlen=max_trace_entries)
        self._trace_overflow_count = 0
        self._backend_states: tuple[dict[str, object], ...] = tuple({} for _ in self._apps)
        self._startup_error: Exception | None = None
        self._shutdown_error: Exception | None = None
        self._lifespan_task: asyncio.Task[None] | None = None

    @property
    def trace(self) -> tuple[HttpRequestTrace, ...]:
        return tuple(self._trace)

    @property
    def trace_overflow_count(self) -> int:
        return self._trace_overflow_count

    @property
    def startup_error(self) -> Exception | None:
        return self._startup_error

    @property
    def shutdown_error(self) -> Exception | None:
        return self._shutdown_error

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
            backend_scope: Scope = dict(scope)
            backend_scope["state"] = self._backend_states[backend_index].copy()
            await self._apps[backend_index](backend_scope, receive, traced_send)
        finally:
            method, method_truncated = _bounded_text(scope.get("method", ""), _MAX_HTTP_METHOD_VALUE)
            path, path_truncated = _bounded_text(scope.get("path", ""), _MAX_HTTP_PATH_VALUE)
            mcp_headers, mcp_headers_truncated = _sanitize_mcp_headers(scope.get("headers", []))
            if len(self._trace) == self._max_trace_entries:
                self._trace_overflow_count += 1
            self._trace.append(
                HttpRequestTrace(
                    backend_index=backend_index,
                    method=method,
                    path=path,
                    mcp_headers=mcp_headers,
                    status=status if status is not None else 500,
                    method_truncated=method_truncated,
                    path_truncated=path_truncated,
                    mcp_headers_truncated=mcp_headers_truncated,
                )
            )

    async def _choose_backend(self) -> int:
        async with self._routing_lock:
            selected = self._next_backend
            self._next_backend = (selected + 1) % len(self._apps)
            return selected

    async def _serve_lifespan(self, receive: Receive, send: Send) -> None:
        self._startup_error = None
        self._shutdown_error = None
        self._lifespan_task = asyncio.current_task()
        startup = await receive()
        _require_message_type(startup, "lifespan.startup")
        started = False
        startup_error: Exception | None = None
        try:
            async with AsyncExitStack() as stack:
                backend_states: list[dict[str, object]] = []
                for app in self._apps:
                    try:
                        state = await stack.enter_async_context(app.router.lifespan_context(app))
                    except Exception as exc:
                        startup_error = exc
                        raise
                    backend_states.append(dict(state) if state is not None else {})
                self._backend_states = tuple(backend_states)
                await send({"type": "lifespan.startup.complete"})
                started = True
                shutdown = await receive()
                _require_message_type(shutdown, "lifespan.shutdown")
            await send({"type": "lifespan.shutdown.complete"})
        except Exception as exc:
            phase = "shutdown" if started else "startup"
            failure = startup_error if startup_error is not None else exc
            if started:
                self._shutdown_error = failure
            else:
                self._startup_error = failure
                if startup_error is not None and exc is not startup_error:
                    self._shutdown_error = exc
            await send({"type": f"lifespan.{phase}.failed", "message": type(failure).__name__})
            if failure is not exc:
                raise failure from exc
            raise
        finally:
            self._backend_states = tuple({} for _ in self._apps)
            self._lifespan_task = None

    async def _cancel_lifespan(self) -> None:
        task = self._lifespan_task
        if task is None or task.done() or task is asyncio.current_task():
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@asynccontextmanager
async def run_loopback_mcp_cluster(
    apps: Sequence[Starlette],
    *,
    startup_timeout: float = 5.0,
    shutdown_timeout: float = 5.0,
) -> AsyncIterator[LoopbackMcpCluster]:
    """Serve the supplied apps on a pre-bound loopback socket."""
    dispatcher = RoundRobinMcpDispatcher(apps)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serve_task: asyncio.Task[None] | None = None
    completed_without_error = False
    try:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.setblocking(False)  # noqa: FBT003
        port = int(listener.getsockname()[1])
        server = uvicorn.Server(uvicorn.Config(dispatcher, log_level="error", access_log=False, lifespan="on"))
        serve_task = asyncio.create_task(server.serve(sockets=[listener]))
        await asyncio.wait_for(
            _wait_until_started(server, serve_task, dispatcher),
            timeout=startup_timeout,
        )
        yield LoopbackMcpCluster(url=f"http://127.0.0.1:{port}/mcp", dispatcher=dispatcher)
        completed_without_error = True
    finally:
        cleanup_error = None
        if serve_task is not None:
            cleanup_error = await _stop_loopback_server(
                server,
                serve_task,
                dispatcher,
                timeout=shutdown_timeout,
            )
        listener.close()
        if completed_without_error and cleanup_error is not None:
            raise cleanup_error


async def _wait_until_started(
    server: uvicorn.Server,
    serve_task: asyncio.Task[None],
    dispatcher: RoundRobinMcpDispatcher,
) -> None:
    while True:
        if dispatcher.startup_error is not None:
            raise dispatcher.startup_error
        if server.started:
            return
        if serve_task.done():
            await serve_task
            if dispatcher.startup_error is not None:
                raise dispatcher.startup_error
            message = "loopback MCP cluster stopped before startup completed"
            raise RuntimeError(message)
        await asyncio.sleep(0.01)


async def _stop_loopback_server(
    server: uvicorn.Server,
    serve_task: asyncio.Task[None],
    dispatcher: RoundRobinMcpDispatcher,
    *,
    timeout: float,
) -> BaseException | None:
    server.should_exit = True
    if not server.started:
        await dispatcher._cancel_lifespan()

    task_error: BaseException | None = None
    completion = asyncio.gather(serve_task, return_exceptions=True)
    try:
        results = await asyncio.wait_for(asyncio.shield(completion), timeout=timeout)
    except asyncio.TimeoutError:
        await dispatcher._cancel_lifespan()
        serve_task.cancel()
        await completion
        await dispatcher._cancel_lifespan()
        message = "loopback MCP cluster did not stop within the timeout"
        task_error = RuntimeError(message)
    except asyncio.CancelledError as exc:
        await dispatcher._cancel_lifespan()
        serve_task.cancel()
        await completion
        task_error = exc
    else:
        result = results[0]
        if isinstance(result, BaseException):
            task_error = result

    return dispatcher.shutdown_error if dispatcher.shutdown_error is not None else task_error


def _require_message_type(message: Message, expected: str) -> None:
    if message["type"] != expected:
        error = f"expected {expected}"
        raise RuntimeError(error)


def _bounded_text(value: object, maximum: int) -> tuple[str, bool]:
    text = str(value)
    return text[:maximum], len(text) > maximum
