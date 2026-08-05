from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.types import Message

from tests.support.mcp_http import (
    RoundRobinMcpDispatcher,
    _stop_loopback_server,
    run_loopback_mcp_cluster,
    sanitize_mcp_headers,
)


class _LifecycleError(RuntimeError):
    pass


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


def _state_backend(label: str) -> Starlette:
    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[dict[str, str]]:
        del app
        yield {"backend": label}

    async def endpoint(request: Request) -> PlainTextResponse:
        backend = request.state.backend
        request.state.backend = "request-local-mutation"
        return PlainTextResponse(backend)

    return Starlette(routes=[Route("/mcp", endpoint, methods=["POST"])], lifespan=lifespan)


def _lifecycle_backend(label: str, events: list[str], failure: str | None = None) -> Starlette:
    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[dict[str, str]]:
        del app
        events.append(f"{label}:start")
        if failure == "startup":
            raise _LifecycleError(f"{label}:startup")
        try:
            yield {"backend": label}
        finally:
            events.append(f"{label}:stop")
            if failure == "shutdown":
                raise _LifecycleError(f"{label}:shutdown")

    async def endpoint(request: Request) -> PlainTextResponse:
        return PlainTextResponse(request.state.backend)

    return Starlette(routes=[Route("/mcp", endpoint, methods=["POST"])], lifespan=lifespan)


def _hanging_startup_backend(events: list[str]) -> Starlette:
    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        del app
        events.append("hang:start")
        try:
            await asyncio.Event().wait()
            yield
        finally:
            events.append("hang:stop")
            message = "hang:cleanup"
            raise _LifecycleError(message)

    return Starlette(lifespan=lifespan)


def _background_tasks():
    tasks = asyncio.all_tasks()
    current = asyncio.current_task()
    if current is not None:
        tasks.remove(current)
    return tasks


async def _assert_listener_closed(url: str) -> None:
    port = int(url.rsplit(":", maxsplit=1)[1].split("/", maxsplit=1)[0])
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", port),
            timeout=0.2,
        )
    except (OSError, asyncio.TimeoutError):
        return
    writer.close()
    await writer.wait_closed()
    message = f"loopback listener on port {port} is still accepting connections"
    raise AssertionError(message)


async def _request(
    dispatcher: RoundRobinMcpDispatcher,
    *,
    method: str = "POST",
    path: str = "/mcp",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> bytes:
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
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": headers
            if headers is not None
            else [
                (b"mcp-protocol-version", b"2026-07-28"),
                (b"mcp-method", b"tools/list"),
            ],
            "client": ("127.0.0.1", 49152),
            "server": ("127.0.0.1", 8000),
        },
        receive,
        send,
    )
    return b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")


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
            (b"mcp-param-resource", b"file:///Users/example/private.json"),
            (b"mcp-resource-uri", b"file:///Users/example/private.json"),
            (b"mcp-unknown", b"private-value"),
        ]
    )

    assert headers == (
        ("mcp-protocol-version", "2026-07-28"),
        ("mcp-method", "tools/call"),
        ("mcp-name", "x" * 128),
        ("mcp-session-id", "<present>"),
    )
    assert sanitize_mcp_headers([(b"mcp-name", b"preview_augmentation")]) == (("mcp-name", "preview_augmentation"),)
    assert sanitize_mcp_headers([(b"mcp-name", b"file:///Users/example/private.json")]) == (("mcp-name", "<redacted>"),)


def test_trace_is_bounded_and_reports_overflow_and_truncation() -> None:
    async def exercise() -> RoundRobinMcpDispatcher:
        dispatcher = RoundRobinMcpDispatcher([_backend("zero", [])], max_trace_entries=2)
        headers = [
            (b"mcp-protocol-version", b"2026-07-28"),
            (b"mcp-method", b"tools/call"),
            (b"mcp-name", b"preview_augmentation"),
            (b"mcp-session-id", b"opaque-secret"),
            (b"mcp-method", b"tools/list"),
        ]
        for _ in range(3):
            await _request(
                dispatcher,
                method="M" * 32,
                path=f"/{'p' * 300}",
                headers=headers,
            )
        return dispatcher

    dispatcher = asyncio.run(exercise())

    assert len(dispatcher.trace) == 2
    assert dispatcher.trace_overflow_count == 1
    for item in dispatcher.trace:
        assert len(item.method) == 16
        assert len(item.path) == 256
        assert len(item.mcp_headers) == 4
        assert item.method_truncated is True
        assert item.path_truncated is True
        assert item.mcp_headers_truncated is True


def test_trace_capacity_cannot_exceed_hard_limit() -> None:
    with pytest.raises(ValueError, match="max_trace_entries"):
        RoundRobinMcpDispatcher([_backend("zero", [])], max_trace_entries=257)


def test_dispatcher_keeps_backend_lifespan_states_distinct() -> None:
    async def exercise() -> list[bytes]:
        async with run_loopback_mcp_cluster([_state_backend("zero"), _state_backend("one")]) as cluster:
            return [await _request(cluster.dispatcher) for _ in range(3)]

    assert asyncio.run(exercise()) == [b"zero", b"one", b"zero"]


def test_cluster_propagates_startup_failure_and_preserves_it_during_rollback() -> None:
    async def exercise() -> list[str]:
        events: list[str] = []
        baseline_tasks = _background_tasks()

        async def start_cluster() -> None:
            async with run_loopback_mcp_cluster(
                [
                    _lifecycle_backend("zero", events, "shutdown"),
                    _lifecycle_backend("one", events, "startup"),
                ],
                startup_timeout=0.25,
                shutdown_timeout=0.25,
            ):
                raise AssertionError

        with pytest.raises(_LifecycleError, match="one:startup"):
            await start_cluster()
        await asyncio.sleep(0)
        assert _background_tasks() <= baseline_tasks
        return events

    assert asyncio.run(exercise()) == ["zero:start", "one:start", "zero:stop"]


def test_cluster_propagates_shutdown_failure_and_closes_listener() -> None:
    async def exercise() -> list[str]:
        events: list[str] = []
        baseline_tasks = _background_tasks()
        url = ""

        async def run_cluster() -> None:
            nonlocal url
            async with run_loopback_mcp_cluster(
                [
                    _lifecycle_backend("zero", events),
                    _lifecycle_backend("one", events, "shutdown"),
                ]
            ) as cluster:
                url = cluster.url
                assert events == ["zero:start", "one:start"]

        with pytest.raises(_LifecycleError, match="one:shutdown"):
            await run_cluster()
        await asyncio.sleep(0)
        assert _background_tasks() <= baseline_tasks
        await _assert_listener_closed(url)
        return events

    assert asyncio.run(exercise()) == ["zero:start", "one:start", "one:stop", "zero:stop"]


def test_cluster_preserves_startup_timeout_during_failing_cleanup() -> None:
    async def exercise() -> list[str]:
        events: list[str] = []
        baseline_tasks = _background_tasks()

        async def start_cluster() -> None:
            async with run_loopback_mcp_cluster(
                [_hanging_startup_backend(events)],
                startup_timeout=0.05,
                shutdown_timeout=0.05,
            ):
                raise AssertionError

        with pytest.raises(asyncio.TimeoutError):
            await start_cluster()
        await asyncio.sleep(0)
        assert _background_tasks() <= baseline_tasks
        return events

    assert asyncio.run(exercise()) == ["hang:start", "hang:stop"]


def test_stop_loopback_server_bounds_cancellation_resistant_task() -> None:
    async def exercise() -> tuple[BaseException | None, float, int]:
        release = asyncio.Event()
        cancellations = 0

        async def resist_first_cancellation() -> None:
            nonlocal cancellations
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancellations += 1
                await release.wait()

        async def safety_release() -> None:
            await asyncio.sleep(0.2)
            release.set()

        serve_task = asyncio.create_task(resist_first_cancellation())
        safety_task = asyncio.create_task(safety_release())
        await asyncio.sleep(0)
        server = type("ServerState", (), {"started": True, "should_exit": False})()
        dispatcher = RoundRobinMcpDispatcher([_backend("zero", [])])
        started = asyncio.get_running_loop().time()
        error = await _stop_loopback_server(
            server,  # ty: ignore[invalid-argument-type] - focused task-lifecycle boundary.
            serve_task,
            dispatcher,
            timeout=0.01,
        )
        elapsed = asyncio.get_running_loop().time() - started
        release.set()
        await serve_task
        safety_task.cancel()
        await asyncio.gather(safety_task, return_exceptions=True)
        return error, elapsed, cancellations

    error, elapsed, cancellations = asyncio.run(exercise())

    assert isinstance(error, RuntimeError)
    assert str(error) == "loopback MCP cluster did not stop within the timeout"
    assert elapsed < 0.1
    assert cancellations == 1


def test_loopback_cluster_fans_out_backend_lifespans() -> None:
    async def exercise() -> list[str]:
        events: list[str] = []
        async with run_loopback_mcp_cluster([_backend("zero", events), _backend("one", events)]):
            assert events == ["zero:start", "one:start"]
        return events

    assert asyncio.run(exercise()) == ["zero:start", "one:start", "one:stop", "zero:stop"]
