# Streamable HTTP Conformance and Published Upgrade Proof Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove AlbumentationsX MCP works across stateless modern Streamable HTTP backends, preserves legacy HTTP
clients, and supports a published `1.20.0 -> 1.21.0` restart without losing public contracts or preview artifacts.

**Architecture:** Keep HTTP routing machinery under test support, keep compatibility comparison pure in the package
domain, and isolate network, subprocess, and MCP client concerns in operator scripts. Use the public MCP 2.x client API
for every protocol observation and emit only bounded, privacy-safe evidence.

**Tech Stack:** Python 3.10+, MCP Python SDK 2.x, Starlette, Uvicorn, Pillow, pytest, Ruff, ty, uv/uvx, GitHub Actions.

---

## File Map

- `tests/support/mcp_http.py`: loopback Uvicorn lifecycle, multi-backend ASGI dispatch, and redacted request traces.
- `tests/test_mcp_http_harness.py`: focused routing, lifecycle, and trace-redaction tests for test support.
- `tests/test_mcp_http_conformance.py`: modern, legacy, reconnect, artifact, and MCP Apps HTTP contract tests.
- `src/albumentationsx_mcp/upgrade_proof.py`: pure observations, subset comparison, digests, failures, and report model.
- `tests/test_upgrade_proof.py`: parameterized report-model tests with no network or subprocesses.
- `scripts/published_upgrade_runtime.py`: published `uvx` server adapter and three-row MCP client orchestration.
- `tests/test_published_upgrade_runtime.py`: in-process replacement for the `uvx` adapter that proves orchestration.
- `scripts/check_published_upgrade.py`: argument parsing, PyPI visibility checks, timeout, and atomic report output.
- `scripts/check_published_package_smoke.py`: expose the existing PyPI version check for reuse.
- `tests/test_published_upgrade_cli.py`: CLI validation, dry-run, failure, and atomic-output tests.
- `.github/workflows/published-upgrade-proof.yml`: explicit, manually dispatched external-package probe.
- `tests/test_published_upgrade_workflow.py`: static workflow and evidence-link guards.
- `docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-03.json`: generated successful evidence.
- `docs/STATUS.md`: compatibility evidence status and link; no host UI claim.

### Task 1: Build The Loopback HTTP Test Boundary

**Files:**
- Create: `tests/support/__init__.py`
- Create: `tests/support/mcp_http.py`
- Create: `tests/test_mcp_http_harness.py`

- [ ] **Step 1: Write failing routing and redaction tests**

Create `tests/support/__init__.py`:

```python
"""Reusable support code for integration tests."""
```

Create `tests/test_mcp_http_harness.py`:

```python
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
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
```

- [ ] **Step 2: Run the tests and verify the support module is missing**

Run: `uv run pytest tests/test_mcp_http_harness.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'tests.support.mcp_http'`.

- [ ] **Step 3: Implement the bounded dispatcher and Uvicorn context manager**

Create `tests/support/mcp_http.py`:

```python
from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator, Iterable, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass

import uvicorn
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
        value = "<present>" if name in _SENSITIVE_MCP_HEADERS else raw_value.decode("latin-1")[:_MAX_MCP_HEADER_VALUE]
        safe.append((name, value))
    return tuple(safe)


class RoundRobinMcpDispatcher:
    """Fan out lifespan and route each HTTP request to one independent backend."""

    def __init__(self, apps: Sequence[Starlette]) -> None:
        if not apps:
            raise ValueError("at least one backend app is required")
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
        if startup["type"] != "lifespan.startup":
            raise RuntimeError("expected lifespan.startup")
        started = False
        try:
            async with AsyncExitStack() as stack:
                for app in self._apps:
                    await stack.enter_async_context(app.router.lifespan_context(app))
                started = True
                await send({"type": "lifespan.startup.complete"})
                shutdown = await receive()
                if shutdown["type"] != "lifespan.shutdown":
                    raise RuntimeError("expected lifespan.shutdown")
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
    listener.setblocking(False)
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
            raise RuntimeError("loopback MCP cluster did not stop within the timeout") from None
        finally:
            listener.close()


async def _wait_until_started(server: uvicorn.Server, serve_task: asyncio.Task[None]) -> None:
    while not server.started:
        if serve_task.done():
            await serve_task
        await asyncio.sleep(0.01)
```

- [ ] **Step 4: Run the focused harness tests**

Run: `uv run pytest tests/test_mcp_http_harness.py -q`

Expected: `3 passed`.

- [ ] **Step 5: Lint and commit the test boundary**

Run: `uv run ruff check tests/support tests/test_mcp_http_harness.py`

Expected: no diagnostics.

```bash
git add tests/support tests/test_mcp_http_harness.py
git commit -m "test: add loopback MCP HTTP cluster"
```

### Task 2: Prove Modern, Legacy, And MCP Apps HTTP Contracts

**Files:**
- Create: `tests/test_mcp_http_conformance.py`

- [ ] **Step 1: Add the modern cross-backend preview and reconnect scenario**

Create `tests/test_mcp_http_conformance.py` with the imports and first test below:

```python
from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.client import advertise
from mcp.server.apps import APP_MIME_TYPE, EXTENSION_ID
from mcp.types import BlobResourceContents, TextResourceContents
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION
from PIL import Image

from albumentationsx_mcp.adapters.mcp.registration import surface_for_profile
from albumentationsx_mcp.capabilities import CapabilityProfile
from albumentationsx_mcp.server import ServerSettings, create_mcp_server
from tests.support.mcp_http import HttpRequestTrace, run_loopback_mcp_cluster


def _settings(root: Path) -> ServerSettings:
    return ServerSettings(allowed_roots=[root], artifact_root=root / "artifacts")


def _preview_request(image_path: Path) -> dict[str, Any]:
    return {
        "input_paths": [str(image_path)],
        "pipeline": {"transforms": [{"name": "HorizontalFlip", "params": {}, "p": 1.0}]},
        "variants_per_image": 1,
        "seed": 17,
    }


def _header_map(trace: HttpRequestTrace) -> dict[str, str]:
    return dict(trace.mcp_headers)


def test_modern_streamable_http_is_stateless_across_backends_and_reconnect(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.new("RGB", (24, 24), (96, 128, 160)).save(image_path)

    async def exercise() -> dict[str, Any]:
        apps = [
            create_mcp_server(_settings(tmp_path)).streamable_http_app(json_response=True)
            for _ in range(2)
        ]
        async with run_loopback_mcp_cluster(apps) as cluster:
            async with Client(cluster.url, mode=LATEST_MODERN_VERSION) as client:
                tools = await client.list_tools(cache_mode="reload")
                smoke = await client.call_tool("run_host_smoke_check", {"include_write_probe": False})
                preview = await client.call_tool(
                    "render_preview_batch",
                    {"request": _preview_request(image_path)},
                )
                assert preview.structured_content is not None
                run_id = preview.structured_content["run_id"]
                contact_sheet_uri = next(
                    item["uri"]
                    for item in preview.structured_content["artifacts"]
                    if item["kind"] == "contact_sheet"
                )
                manifest = await client.call_tool("get_preview_manifest", {"run_id": run_id})
                contact_sheet = await client.read_resource(contact_sheet_uri)
                first_protocol = client.protocol_version

            async with Client(cluster.url, mode=LATEST_MODERN_VERSION) as reconnected:
                restored = await reconnected.call_tool("get_preview_manifest", {"run_id": run_id})
                second_protocol = reconnected.protocol_version

            return {
                "tools": {tool.name for tool in tools.tools},
                "smoke": smoke.structured_content,
                "run_id": run_id,
                "manifest": manifest.structured_content,
                "restored": restored.structured_content,
                "contact_sheet": contact_sheet.contents[0],
                "protocols": (first_protocol, second_protocol),
                "trace": cluster.trace,
            }

    result = asyncio.run(exercise())

    assert result["tools"] == set(surface_for_profile(CapabilityProfile.FULL).tools)
    assert result["smoke"]["preview_ready"] is True
    assert result["manifest"]["run_id"] == result["run_id"]
    assert result["restored"]["run_id"] == result["run_id"]
    assert result["protocols"] == (LATEST_MODERN_VERSION, LATEST_MODERN_VERSION)
    contact_sheet = result["contact_sheet"]
    assert isinstance(contact_sheet, BlobResourceContents)
    assert base64.b64decode(contact_sheet.blob).startswith(b"\x89PNG\r\n\x1a\n")
    successful = [item for item in result["trace"] if 200 <= item.status < 300]
    assert {item.backend_index for item in successful} == {0, 1}
    assert all("mcp-session-id" not in _header_map(item) for item in successful)
    assert all(_header_map(item)["mcp-protocol-version"] == LATEST_MODERN_VERSION for item in successful)
    assert {
        "server/discover",
        "tools/list",
        "tools/call",
        "resources/read",
    }.issubset({_header_map(item)["mcp-method"] for item in successful})
    observed_names = {
        _header_map(item)["mcp-name"]
        for item in successful
        if "mcp-name" in _header_map(item)
    }
    assert {
        "run_host_smoke_check",
        "render_preview_batch",
        "get_preview_manifest",
    }.issubset(observed_names)
```

- [ ] **Step 2: Run the modern scenario as a characterization check**

Run: `uv run pytest tests/test_mcp_http_conformance.py::test_modern_streamable_http_is_stateless_across_backends_and_reconnect -q`

Expected: PASS. A failure is a concrete SDK/runtime defect and must be fixed with a smaller regression test before
continuing; do not weaken round-robin or session assertions.

- [ ] **Step 3: Add the legacy one-backend scenario**

Append:

```python
def test_legacy_streamable_http_keeps_initialize_and_resource_flow(tmp_path: Path) -> None:
    async def exercise() -> dict[str, Any]:
        app = create_mcp_server(_settings(tmp_path)).streamable_http_app(json_response=True)
        async with run_loopback_mcp_cluster([app]) as cluster:
            async with Client(cluster.url, mode="legacy") as client:
                tools = await client.list_tools(cache_mode="reload")
                search = await client.call_tool("search_transforms", {"query": "blur", "limit": 3})
                example = await client.read_resource("albumentationsx://examples/client-smoke")
                return {
                    "protocol": client.protocol_version,
                    "tools": {tool.name for tool in tools.tools},
                    "search": search,
                    "example": example.contents[0],
                    "trace": cluster.trace,
                }

    result = asyncio.run(exercise())

    assert result["protocol"] == LATEST_HANDSHAKE_VERSION
    assert result["tools"] == set(surface_for_profile(CapabilityProfile.FULL).tools)
    assert result["search"].is_error is False
    assert result["search"].structured_content["results"]
    assert isinstance(result["example"], TextResourceContents)
    assert "run_host_smoke_check" in result["example"].text
    assert {item.backend_index for item in result["trace"]} == {0}
    assert any("mcp-session-id" in _header_map(item) for item in result["trace"])
```

- [ ] **Step 4: Add extension-aware and ordinary-client Apps coverage**

Append:

```python
def test_streamable_http_negotiates_apps_and_preserves_fallback(tmp_path: Path) -> None:
    image_path = tmp_path / "apps.png"
    Image.new("RGB", (16, 16), (128, 96, 64)).save(image_path)

    async def exercise() -> dict[str, Any]:
        app = create_mcp_server(_settings(tmp_path)).streamable_http_app(json_response=True)
        extension = advertise(EXTENSION_ID, {"mimeTypes": [APP_MIME_TYPE]})
        async with run_loopback_mcp_cluster([app]) as cluster:
            async with Client(
                cluster.url,
                mode=LATEST_MODERN_VERSION,
                extensions=[extension],
            ) as app_client:
                app_capabilities = app_client.server_capabilities.model_dump(by_alias=True, exclude_none=True)
                app_result = await app_client.call_tool(
                    "render_preview_batch",
                    {"request": _preview_request(image_path)},
                )

            async with Client(cluster.url, mode=LATEST_MODERN_VERSION) as ordinary_client:
                ordinary_capabilities = ordinary_client.server_capabilities.model_dump(
                    by_alias=True,
                    exclude_none=True,
                )
                ordinary_result = await ordinary_client.call_tool(
                    "render_preview_batch",
                    {"request": _preview_request(image_path)},
                )

            return {
                "app_capabilities": app_capabilities,
                "ordinary_capabilities": ordinary_capabilities,
                "app_result": app_result,
                "ordinary_result": ordinary_result,
            }

    result = asyncio.run(exercise())

    assert result["app_capabilities"]["extensions"][EXTENSION_ID] == {}
    assert EXTENSION_ID not in result["ordinary_capabilities"].get("extensions", {})
    assert result["app_result"].is_error is False
    assert result["ordinary_result"].is_error is False
    assert result["app_result"].structured_content["run_id"]
    assert result["ordinary_result"].structured_content["run_id"]
```

- [ ] **Step 5: Run all HTTP tests on the supported local interpreter**

Run: `uv run pytest tests/test_mcp_http_harness.py tests/test_mcp_http_conformance.py -q`

Expected: `6 passed` with no leaked Uvicorn task or socket warnings.

- [ ] **Step 6: Commit protocol conformance coverage**

```bash
git add tests/test_mcp_http_conformance.py
git commit -m "test: prove Streamable HTTP compatibility"
```

### Task 3: Implement The Pure Upgrade Evidence Model

**Files:**
- Create: `src/albumentationsx_mcp/upgrade_proof.py`
- Create: `tests/test_upgrade_proof.py`

- [ ] **Step 1: Write parameterized subset, protocol, artifact, and determinism tests**

Create `tests/test_upgrade_proof.py`:

```python
from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

import pytest

from albumentationsx_mcp.upgrade_proof import (
    ArtifactContinuity,
    ProtocolObservation,
    PublicSurface,
    build_upgrade_proof_report,
)


def _surface(*, extra_tool: str | None = None) -> PublicSurface:
    tools = ["render_preview_batch", "search_transforms"]
    if extra_tool is not None:
        tools.append(extra_tool)
    return PublicSurface.build(
        tools=tools,
        resources=["albumentationsx://examples/client-smoke"],
        resource_templates=["albumentationsx://preview-artifacts/{run_id}/{filename}"],
        prompts=["augment_dataset"],
    )


def _observation(version: str, mode: str, protocol: str, surface: PublicSurface) -> ProtocolObservation:
    return ProtocolObservation(
        server_version=version,
        observed_server_version=version,
        client_mode=mode,
        expected_protocol=protocol,
        negotiated_protocol=protocol,
        surface=surface,
    )


def _artifact() -> ArtifactContinuity:
    return ArtifactContinuity(
        manifest_readable=True,
        manifest_run_id_matches=True,
        contact_sheet_readable=True,
        content_unchanged=True,
        contact_sheet_sha256="a" * 64,
    )


def _report(
    *,
    old_surface: PublicSurface | None = None,
    new_surface: PublicSurface | None = None,
    artifact: ArtifactContinuity | None = None,
) -> dict[str, Any]:
    old = old_surface or _surface()
    new = new_surface or _surface(extra_tool="trace_preview_variant")
    return build_upgrade_proof_report(
        package="albumentationsx-mcp",
        from_version="1.20.0",
        to_version="1.21.0",
        observed_on="2026-08-03",
        from_legacy=_observation("1.20.0", "legacy", "2025-11-25", old),
        to_legacy=_observation("1.21.0", "legacy", "2025-11-25", new),
        to_modern=_observation("1.21.0", "2026-07-28", "2026-07-28", new),
        artifact=artifact or _artifact(),
    )


def test_additive_upgrade_passes_without_emitting_public_identifier_lists() -> None:
    report = _report()
    encoded = json.dumps(report, sort_keys=True)

    assert report["status"] == "pass"
    assert report["failures"] == []
    assert report["compatibility"]["old_surface_is_subset"] is True
    assert "trace_preview_variant" not in encoded
    assert "/Users/" not in encoded
    assert "/home/" not in encoded


@pytest.mark.parametrize("category", ["tools", "resources", "resource_templates", "prompts"])
def test_removed_public_identifier_fails_closed(category: str) -> None:
    old = _surface()
    values = {name: list(items) for name, items in old.categories().items()}
    removed = values[category].pop()
    new = PublicSurface.build(
        tools=values["tools"],
        resources=values["resources"],
        resource_templates=values["resource_templates"],
        prompts=values["prompts"],
    )

    report = _report(old_surface=old, new_surface=new)

    assert report["status"] == "fail"
    assert report["compatibility"]["categories"][category]["missing"] == [removed]
    assert "surface_removed" in {failure["code"] for failure in report["failures"]}


def test_version_protocol_or_artifact_failure_is_reported_with_remediation() -> None:
    report = _report()
    old_row = _observation("1.20.0", "legacy", "2025-11-25", _surface())
    bad_protocol = replace(
        old_row,
        observed_server_version="9.9.9",
        negotiated_protocol="2026-07-28",
    )
    bad_artifact = replace(_artifact(), content_unchanged=False)

    failed = build_upgrade_proof_report(
        package="albumentationsx-mcp",
        from_version="1.20.0",
        to_version="1.21.0",
        observed_on="2026-08-03",
        from_legacy=bad_protocol,
        to_legacy=_observation("1.21.0", "legacy", "2025-11-25", _surface()),
        to_modern=_observation("1.21.0", "2026-07-28", "2026-07-28", _surface()),
        artifact=bad_artifact,
    )

    assert report["status"] == "pass"
    assert failed["status"] == "fail"
    assert {item["code"] for item in failed["failures"]} == {
        "artifact_continuity_failed",
        "protocol_negotiation_failed",
        "server_version_mismatch",
    }
    assert all(item["remediation"] for item in failed["failures"])


def test_report_is_deterministic_for_reordered_identifiers() -> None:
    first = _report()
    reordered = PublicSurface.build(
        tools=["search_transforms", "render_preview_batch"],
        resources=["albumentationsx://examples/client-smoke"],
        resource_templates=["albumentationsx://preview-artifacts/{run_id}/{filename}"],
        prompts=["augment_dataset"],
    )
    second = _report(old_surface=reordered)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
```

- [ ] **Step 2: Run the tests and verify the model is missing**

Run: `uv run pytest tests/test_upgrade_proof.py -q`

Expected: collection fails on `albumentationsx_mcp.upgrade_proof`.

- [ ] **Step 3: Implement deterministic report construction**

Create `src/albumentationsx_mcp/upgrade_proof.py`:

```python
"""Pure compatibility evidence for published AlbumentationsX MCP upgrades."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

_SCHEMA_VERSION = "albumentationsx-mcp/published-upgrade-proof/v1"


@dataclass(frozen=True)
class PublicSurface:
    """Canonical public MCP identifiers observed from one server process."""

    tools: tuple[str, ...]
    resources: tuple[str, ...]
    resource_templates: tuple[str, ...]
    prompts: tuple[str, ...]

    @classmethod
    def build(
        cls,
        *,
        tools: Iterable[str],
        resources: Iterable[str],
        resource_templates: Iterable[str],
        prompts: Iterable[str],
    ) -> PublicSurface:
        return cls(
            tools=_canonical(tools),
            resources=_canonical(resources),
            resource_templates=_canonical(resource_templates),
            prompts=_canonical(prompts),
        )

    def categories(self) -> dict[str, tuple[str, ...]]:
        return {
            "tools": self.tools,
            "resources": self.resources,
            "resource_templates": self.resource_templates,
            "prompts": self.prompts,
        }


@dataclass(frozen=True)
class ProtocolObservation:
    """One published server and current-client protocol observation."""

    server_version: str
    observed_server_version: str
    client_mode: str
    expected_protocol: str
    negotiated_protocol: str
    surface: PublicSurface


@dataclass(frozen=True)
class ArtifactContinuity:
    """Bounded result of reading an old preview through the new server."""

    manifest_readable: bool
    manifest_run_id_matches: bool
    contact_sheet_readable: bool
    content_unchanged: bool
    contact_sheet_sha256: str


def build_upgrade_proof_report(
    *,
    package: str,
    from_version: str,
    to_version: str,
    observed_on: str,
    from_legacy: ProtocolObservation,
    to_legacy: ProtocolObservation,
    to_modern: ProtocolObservation,
    artifact: ArtifactContinuity,
) -> dict[str, Any]:
    """Build a deterministic privacy-safe upgrade report."""
    rows = (from_legacy, to_legacy, to_modern)
    failures: list[dict[str, object]] = []
    for row in rows:
        if row.observed_server_version != row.server_version:
            failures.append(
                {
                    "code": "server_version_mismatch",
                    "scope": f"{row.server_version}:{row.client_mode}",
                    "remediation": "Verify the uvx package pin and the published distribution metadata.",
                }
            )
        if row.negotiated_protocol != row.expected_protocol:
            failures.append(
                {
                    "code": "protocol_negotiation_failed",
                    "scope": f"{row.server_version}:{row.client_mode}",
                    "remediation": "Verify the selected client mode and published server SDK compatibility.",
                }
            )

    categories: dict[str, Any] = {}
    old_surface_is_subset = True
    for name, old_identifiers in from_legacy.surface.categories().items():
        new_identifiers = to_legacy.surface.categories()[name]
        missing = sorted(set(old_identifiers) - set(new_identifiers))
        categories[name] = {
            "ok": not missing,
            "old": _surface_summary(old_identifiers),
            "new": _surface_summary(new_identifiers),
            "missing": missing,
        }
        if missing:
            old_surface_is_subset = False
            failures.append(
                {
                    "code": "surface_removed",
                    "scope": name,
                    "missing": missing,
                    "remediation": "Restore the published identifier or document and version a breaking change.",
                }
            )

    new_modes_equal = to_legacy.surface == to_modern.surface
    if not new_modes_equal:
        failures.append(
            {
                "code": "new_mode_surface_mismatch",
                "scope": to_version,
                "remediation": "Register the same capability profile for legacy and modern protocol modes.",
            }
        )

    artifact_ok = all(
        (
            artifact.manifest_readable,
            artifact.manifest_run_id_matches,
            artifact.contact_sheet_readable,
            artifact.content_unchanged,
        )
    )
    if not artifact_ok:
        failures.append(
            {
                "code": "artifact_continuity_failed",
                "scope": f"{from_version}->{to_version}",
                "remediation": "Inspect manifest and artifact resource compatibility before releasing an upgrade.",
            }
        )

    return {
        "schema_version": _SCHEMA_VERSION,
        "package": package,
        "from_version": from_version,
        "to_version": to_version,
        "observed_on": observed_on,
        "status": "pass" if not failures else "fail",
        "matrix": [_protocol_summary(row) for row in rows],
        "compatibility": {
            "old_surface_is_subset": old_surface_is_subset,
            "new_modes_equal": new_modes_equal,
            "categories": categories,
        },
        "artifact_continuity": {
            "ok": artifact_ok,
            "manifest_readable": artifact.manifest_readable,
            "manifest_run_id_matches": artifact.manifest_run_id_matches,
            "contact_sheet_readable": artifact.contact_sheet_readable,
            "content_unchanged": artifact.content_unchanged,
            "contact_sheet_sha256": artifact.contact_sheet_sha256,
        },
        "failures": failures,
    }


def _protocol_summary(row: ProtocolObservation) -> dict[str, object]:
    return {
        "server_version": row.server_version,
        "observed_server_version": row.observed_server_version,
        "client_mode": row.client_mode,
        "expected_protocol": row.expected_protocol,
        "negotiated_protocol": row.negotiated_protocol,
        "ok": row.expected_protocol == row.negotiated_protocol,
        "surface": {name: _surface_summary(values) for name, values in row.surface.categories().items()},
    }


def _surface_summary(identifiers: Iterable[str]) -> dict[str, object]:
    canonical = _canonical(identifiers)
    return {"count": len(canonical), "sha256": _digest(canonical)}


def _canonical(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _digest(values: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Run model tests, Ruff, and ty**

Run: `uv run pytest tests/test_upgrade_proof.py -q`

Expected: `7 passed`.

Run: `uv run ruff check src/albumentationsx_mcp/upgrade_proof.py tests/test_upgrade_proof.py`

Expected: no diagnostics.

Run: `uv run ty check src/albumentationsx_mcp/upgrade_proof.py tests/test_upgrade_proof.py`

Expected: no diagnostics.

- [ ] **Step 5: Commit the pure evidence model**

```bash
git add src/albumentationsx_mcp/upgrade_proof.py tests/test_upgrade_proof.py
git commit -m "feat: model published upgrade evidence"
```

### Task 4: Add The Isolated Published-Server Runtime Adapter

**Files:**
- Create: `scripts/published_upgrade_runtime.py`
- Create: `tests/test_published_upgrade_runtime.py`

- [ ] **Step 1: Write an in-process orchestration test**

Create `tests/test_published_upgrade_runtime.py`:

```python
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from mcp import Client
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION

from albumentationsx_mcp import server as server_module
from albumentationsx_mcp.server import ServerSettings
from scripts.published_upgrade_runtime import (
    PublishedUpgradeConfig,
    ServerClientRequest,
    build_uvx_server_command,
    clean_subprocess_environment,
    run_published_upgrade,
)


def test_build_uvx_server_command_pins_exact_package_version() -> None:
    assert build_uvx_server_command("1.20.0") == [
        "uvx",
        "--from",
        "albumentationsx-mcp==1.20.0",
        "--refresh-package",
        "albumentationsx-mcp",
        "albumentationsx-mcp",
    ]


def test_clean_environment_removes_albumentationsx_runtime_overrides() -> None:
    cleaned = clean_subprocess_environment(
        {
            "PATH": "/bin",
            "HTTPS_PROXY": "http://proxy.invalid",
            "ALBU_MCP_ALLOWED_ROOTS": "/private/input",
            "ALBU_MCP_CAPABILITY_PROFILE": "core",
        }
    )

    assert cleaned == {"PATH": "/bin", "HTTPS_PROXY": "http://proxy.invalid"}


def test_upgrade_runtime_restarts_three_clients_and_reads_old_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[ServerClientRequest] = []

    @asynccontextmanager
    async def client_factory(request: ServerClientRequest) -> AsyncIterator[Client]:
        requests.append(request)
        monkeypatch.setattr(server_module, "_package_version", lambda: request.version)
        server = server_module.create_mcp_server(
            ServerSettings(
                allowed_roots=[request.allowed_root],
                artifact_root=request.artifact_root,
            )
        )
        async with Client(server, mode=request.mode) as client:
            yield client

    report = asyncio.run(
        run_published_upgrade(
            PublishedUpgradeConfig(
                from_version="1.20.0",
                to_version="1.21.0",
                observed_on="2026-08-03",
                allowed_root=tmp_path,
                artifact_root=tmp_path / "artifacts",
                read_timeout_seconds=20.0,
            ),
            client_factory=client_factory,
        )
    )
    encoded = json.dumps(report, sort_keys=True)

    assert report["status"] == "pass"
    assert [(item.version, item.mode) for item in requests] == [
        ("1.20.0", "legacy"),
        ("1.21.0", "legacy"),
        ("1.21.0", LATEST_MODERN_VERSION),
    ]
    assert report["matrix"][0]["negotiated_protocol"] == LATEST_HANDSHAKE_VERSION
    assert report["matrix"][2]["negotiated_protocol"] == LATEST_MODERN_VERSION
    assert report["artifact_continuity"]["content_unchanged"] is True
    assert str(tmp_path) not in encoded
```

- [ ] **Step 2: Run the tests and verify the runtime module is missing**

Run: `uv run pytest tests/test_published_upgrade_runtime.py -q`

Expected: collection fails on `scripts.published_upgrade_runtime`.

- [ ] **Step 3: Implement the MCP client factory and three-process matrix**

Create `scripts/published_upgrade_runtime.py` with these interfaces and behavior:

```python
"""Runtime adapter for published AlbumentationsX MCP upgrade probes."""

from __future__ import annotations

import base64
import hashlib
import os
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import BlobResourceContents
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION
from PIL import Image

from albumentationsx_mcp.upgrade_proof import (
    ArtifactContinuity,
    ProtocolObservation,
    PublicSurface,
    build_upgrade_proof_report,
)

PACKAGE = "albumentationsx-mcp"


@dataclass(frozen=True)
class PublishedUpgradeConfig:
    from_version: str
    to_version: str
    observed_on: str
    allowed_root: Path
    artifact_root: Path
    read_timeout_seconds: float


@dataclass(frozen=True)
class ServerClientRequest:
    version: str
    mode: str
    allowed_root: Path
    artifact_root: Path
    read_timeout_seconds: float


class ClientFactory(Protocol):
    def __call__(self, request: ServerClientRequest) -> AbstractAsyncContextManager[Client]:
        """Return an async context manager yielding a connected MCP client."""
        raise NotImplementedError


@dataclass(frozen=True)
class _ArtifactSeed:
    run_id: str
    contact_sheet_uri: str
    contact_sheet_sha256: str


def build_uvx_server_command(version: str) -> list[str]:
    return [
        "uvx",
        "--from",
        f"{PACKAGE}=={version}",
        "--refresh-package",
        PACKAGE,
        PACKAGE,
    ]


def clean_subprocess_environment(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    source = os.environ if environment is None else environment
    return {name: value for name, value in source.items() if not name.startswith("ALBU_MCP_")}


@asynccontextmanager
async def open_published_client(request: ServerClientRequest) -> AsyncIterator[Client]:
    command = build_uvx_server_command(request.version)
    params = StdioServerParameters(
        command=command[0],
        args=[
            *command[1:],
            "--allowed-root",
            str(request.allowed_root),
            "--artifact-root",
            str(request.artifact_root),
            "--capability-profile",
            "full",
        ],
        cwd=str(request.allowed_root),
        env=clean_subprocess_environment(),
    )
    with Path(os.devnull).open("w", encoding="utf-8") as errlog:
        async with Client(
            stdio_client(params, errlog=errlog),
            mode=request.mode,
            read_timeout_seconds=request.read_timeout_seconds,
        ) as client:
            yield client


async def run_published_upgrade(
    config: PublishedUpgradeConfig,
    *,
    client_factory: ClientFactory = open_published_client,
) -> dict[str, Any]:
    fixture_path = config.allowed_root / "generated-upgrade-fixture.png"
    Image.new("RGB", (24, 24), (96, 128, 160)).save(fixture_path)

    from_request = _client_request(config, version=config.from_version, mode="legacy")
    async with client_factory(from_request) as client:
        from_surface = await _snapshot_surface(client)
        from_legacy = _observation(client, from_request, LATEST_HANDSHAKE_VERSION, from_surface)
        seed = await _render_seed(client, fixture_path)

    to_legacy_request = _client_request(config, version=config.to_version, mode="legacy")
    async with client_factory(to_legacy_request) as client:
        to_legacy_surface = await _snapshot_surface(client)
        to_legacy = _observation(client, to_legacy_request, LATEST_HANDSHAKE_VERSION, to_legacy_surface)

    to_modern_request = _client_request(config, version=config.to_version, mode=LATEST_MODERN_VERSION)
    async with client_factory(to_modern_request) as client:
        to_modern_surface = await _snapshot_surface(client)
        to_modern = _observation(client, to_modern_request, LATEST_MODERN_VERSION, to_modern_surface)
        artifact = await _read_old_artifact(client, seed)

    return build_upgrade_proof_report(
        package=PACKAGE,
        from_version=config.from_version,
        to_version=config.to_version,
        observed_on=config.observed_on,
        from_legacy=from_legacy,
        to_legacy=to_legacy,
        to_modern=to_modern,
        artifact=artifact,
    )


def _client_request(config: PublishedUpgradeConfig, *, version: str, mode: str) -> ServerClientRequest:
    return ServerClientRequest(
        version=version,
        mode=mode,
        allowed_root=config.allowed_root,
        artifact_root=config.artifact_root,
        read_timeout_seconds=config.read_timeout_seconds,
    )


def _observation(
    client: Client,
    request: ServerClientRequest,
    expected_protocol: str,
    surface: PublicSurface,
) -> ProtocolObservation:
    server_info = client.server_info
    return ProtocolObservation(
        server_version=request.version,
        observed_server_version=server_info.version if server_info is not None else "<missing>",
        client_mode=request.mode,
        expected_protocol=expected_protocol,
        negotiated_protocol=str(client.protocol_version),
        surface=surface,
    )


async def _snapshot_surface(client: Client) -> PublicSurface:
    return PublicSurface.build(
        tools=await _collect_identifiers(client.list_tools, "tools", "name"),
        resources=await _collect_identifiers(client.list_resources, "resources", "uri"),
        resource_templates=await _collect_identifiers(
            client.list_resource_templates,
            "resource_templates",
            "uri_template",
        ),
        prompts=await _collect_identifiers(client.list_prompts, "prompts", "name"),
    )


async def _collect_identifiers(
    fetch: Callable[..., Awaitable[Any]],
    collection_name: str,
    identifier_name: str,
) -> list[str]:
    identifiers: list[str] = []
    cursor: str | None = None
    while True:
        page = await fetch(cursor=cursor, cache_mode="reload")
        identifiers.extend(str(getattr(item, identifier_name)) for item in getattr(page, collection_name))
        cursor = page.next_cursor
        if cursor is None:
            return identifiers


async def _render_seed(client: Client, fixture_path: Path) -> _ArtifactSeed:
    result = await client.call_tool(
        "render_preview_batch",
        {
            "request": {
                "input_paths": [str(fixture_path)],
                "pipeline": {"transforms": [{"name": "HorizontalFlip", "params": {}, "p": 1.0}]},
                "variants_per_image": 1,
                "seed": 17,
            }
        },
    )
    if result.is_error or result.structured_content is None:
        raise RuntimeError("published old server could not render the generated fixture")
    run_id = str(result.structured_content["run_id"])
    contact_sheet_uri = str(
        next(item["uri"] for item in result.structured_content["artifacts"] if item["kind"] == "contact_sheet")
    )
    payload = await _read_png_resource(client, contact_sheet_uri)
    return _ArtifactSeed(
        run_id=run_id,
        contact_sheet_uri=contact_sheet_uri,
        contact_sheet_sha256=hashlib.sha256(payload).hexdigest(),
    )


async def _read_old_artifact(client: Client, seed: _ArtifactSeed) -> ArtifactContinuity:
    manifest = await client.call_tool("get_preview_manifest", {"run_id": seed.run_id})
    manifest_content = manifest.structured_content
    manifest_readable = not manifest.is_error and manifest_content is not None
    manifest_run_id_matches = bool(
        manifest_readable and manifest_content is not None and manifest_content["run_id"] == seed.run_id
    )
    payload = await _read_png_resource(client, seed.contact_sheet_uri)
    digest = hashlib.sha256(payload).hexdigest()
    return ArtifactContinuity(
        manifest_readable=manifest_readable,
        manifest_run_id_matches=manifest_run_id_matches,
        contact_sheet_readable=True,
        content_unchanged=digest == seed.contact_sheet_sha256,
        contact_sheet_sha256=digest,
    )


async def _read_png_resource(client: Client, uri: str) -> bytes:
    result = await client.read_resource(uri)
    content = result.contents[0]
    if not isinstance(content, BlobResourceContents):
        raise RuntimeError("preview artifact resource did not return binary content")
    payload = base64.b64decode(content.blob)
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("preview artifact resource did not return a valid PNG")
    return payload
```

- [ ] **Step 4: Run runtime tests and static checks**

Run: `uv run pytest tests/test_published_upgrade_runtime.py -q`

Expected: `3 passed`.

Run: `uv run ruff check scripts/published_upgrade_runtime.py tests/test_published_upgrade_runtime.py`

Expected: no diagnostics.

Run: `uv run ty check scripts/published_upgrade_runtime.py tests/test_published_upgrade_runtime.py`

Expected: no diagnostics; do not add casts around product results.

- [ ] **Step 5: Commit the runtime adapter**

```bash
git add scripts/published_upgrade_runtime.py tests/test_published_upgrade_runtime.py
git commit -m "feat: probe published MCP upgrades"
```

### Task 5: Add The Thin, Fail-Closed Operator CLI

**Files:**
- Modify: `scripts/check_published_package_smoke.py`
- Create: `scripts/check_published_upgrade.py`
- Create: `tests/test_published_upgrade_cli.py`

- [ ] **Step 1: Expose the existing PyPI version check for reuse**

Rename `_check_pypi_version` to `check_pypi_version` and update its call in `run_smoke`:

```python
def check_pypi_version(*, package: str, version: str, timeout_seconds: float) -> str | None:
    """Return a safe error when an exact PyPI version endpoint is unavailable."""
    url = build_pypi_version_url(package=package, version=version)
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310 - fixed HTTPS PyPI URL.
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return f"PyPI version endpoint is not visible yet: {url} ({exc})"
    published_version = payload.get("info", {}).get("version")
    if published_version != version:
        return f"PyPI version endpoint returned {published_version!r}, expected {version!r}: {url}"
    return None
```

- [ ] **Step 2: Write CLI validation and atomic-output tests**

Create `tests/test_published_upgrade_cli.py`:

```python
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from scripts import check_published_upgrade


@pytest.mark.parametrize("version", ["", "latest", "1.21", "1.21.0;echo", "../1.21.0"])
def test_validate_exact_version_rejects_non_release_values(version: str) -> None:
    with pytest.raises(ValueError, match="exact release version"):
        check_published_upgrade.validate_exact_version(version)


def test_dry_run_prints_three_pinned_commands_without_network(capsys: pytest.CaptureFixture[str]) -> None:
    result = check_published_upgrade.main(
        ["--from-version", "1.20.0", "--to-version", "1.21.0", "--dry-run"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert [(item["server_version"], item["client_mode"]) for item in payload["commands"]] == [
        ("1.20.0", "legacy"),
        ("1.21.0", "legacy"),
        ("1.21.0", "2026-07-28"),
    ]
    assert all(command["command"][0] == "uvx" for command in payload["commands"])


def test_success_writes_report_atomically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = {"schema_version": "test", "status": "pass", "failures": []}

    async def fake_probe(config: object) -> dict[str, object]:
        del config
        return report

    monkeypatch.setattr(check_published_upgrade, "run_published_upgrade", fake_probe)
    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", lambda **kwargs: None)
    output = tmp_path / "evidence" / "upgrade.json"

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
            "--observed-on",
            "2026-08-03",
            "--output",
            str(output),
        ]
    )

    assert result == 0
    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert list(output.parent.iterdir()) == [output]


def test_failed_report_is_printed_but_not_recorded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = {
        "schema_version": "test",
        "status": "fail",
        "failures": [{"code": "surface_removed", "remediation": "restore it"}],
    }

    async def fake_probe(config: object) -> dict[str, object]:
        del config
        return report

    monkeypatch.setattr(check_published_upgrade, "run_published_upgrade", fake_probe)
    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", lambda **kwargs: None)
    output = tmp_path / "upgrade.json"

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
            "--output",
            str(output),
        ]
    )

    assert result == 1
    assert not output.exists()
    assert json.loads(capsys.readouterr().err)["status"] == "fail"


def test_probe_timeout_fails_closed_without_recording_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def slow_probe(config: object) -> dict[str, object]:
        del config
        await asyncio.sleep(1.0)
        return {"status": "pass"}

    monkeypatch.setattr(check_published_upgrade, "run_published_upgrade", slow_probe)
    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", lambda **kwargs: None)
    output = tmp_path / "upgrade.json"

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
            "--probe-timeout",
            "0.001",
            "--output",
            str(output),
        ]
    )

    assert result == 1
    assert not output.exists()
    assert json.loads(capsys.readouterr().err)["failures"][0]["code"] == "probe_execution_failed"
```

- [ ] **Step 3: Run the CLI tests and verify the module is missing**

Run: `uv run pytest tests/test_published_upgrade_cli.py -q`

Expected: collection fails on `scripts.check_published_upgrade`.

- [ ] **Step 4: Implement argument parsing, retries, timeout, and atomic writes**

Create `scripts/check_published_upgrade.py`:

```python
"""Prove compatibility between two exact published AlbumentationsX MCP versions."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.types.version import LATEST_MODERN_VERSION

from scripts.check_published_package_smoke import check_pypi_version
from scripts.published_upgrade_runtime import (
    PACKAGE,
    PublishedUpgradeConfig,
    build_uvx_server_command,
    run_published_upgrade,
)

_EXACT_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[a-z]+[0-9]+)?$")


def validate_exact_version(value: str) -> str:
    if _EXACT_VERSION.fullmatch(value) is None:
        raise ValueError("version must be an exact release version such as 1.21.0")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-version", required=True, type=validate_exact_version)
    parser.add_argument("--to-version", required=True, type=validate_exact_version)
    parser.add_argument("--observed-on", type=date.fromisoformat, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=5.0)
    parser.add_argument("--pypi-timeout", type=float, default=20.0)
    parser.add_argument("--read-timeout", type=float, default=120.0)
    parser.add_argument("--probe-timeout", type=float, default=600.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    observed_on = args.observed_on or datetime.now(tz=timezone.utc).date()
    if args.dry_run:
        sys.stdout.write(
            json.dumps(
                {
                    "commands": [
                        {
                            "server_version": args.from_version,
                            "client_mode": "legacy",
                            "command": build_uvx_server_command(args.from_version),
                        },
                        {
                            "server_version": args.to_version,
                            "client_mode": "legacy",
                            "command": build_uvx_server_command(args.to_version),
                        },
                        {
                            "server_version": args.to_version,
                            "client_mode": LATEST_MODERN_VERSION,
                            "command": build_uvx_server_command(args.to_version),
                        },
                    ]
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        return 0

    for version in (args.from_version, args.to_version):
        if not _wait_for_pypi_version(
            version=version,
            retries=args.retries,
            delay_seconds=args.retry_delay,
            timeout_seconds=args.pypi_timeout,
        ):
            return 1

    try:
        with tempfile.TemporaryDirectory(prefix="albumentationsx-mcp-upgrade-") as temporary:
            root = Path(temporary)
            report = asyncio.run(
                asyncio.wait_for(
                    run_published_upgrade(
                        PublishedUpgradeConfig(
                            from_version=args.from_version,
                            to_version=args.to_version,
                            observed_on=observed_on.isoformat(),
                            allowed_root=root,
                            artifact_root=root / "artifacts",
                            read_timeout_seconds=args.read_timeout,
                        )
                    ),
                    timeout=args.probe_timeout,
                )
            )
    except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
        failure = {
            "schema_version": "albumentationsx-mcp/published-upgrade-proof/v1",
            "package": PACKAGE,
            "from_version": args.from_version,
            "to_version": args.to_version,
            "observed_on": observed_on.isoformat(),
            "status": "fail",
            "failures": [
                {
                    "code": "probe_execution_failed",
                    "error_type": type(exc).__name__,
                    "remediation": "Retry after checking PyPI visibility and the published server stderr locally.",
                }
            ],
        }
        sys.stderr.write(json.dumps(failure, indent=2, sort_keys=True) + "\n")
        return 1

    content = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if report["status"] != "pass":
        sys.stderr.write(content)
        return 1
    if args.output is None:
        sys.stdout.write(content)
    else:
        _write_atomic(args.output, content)
    return 0


def _wait_for_pypi_version(
    *,
    version: str,
    retries: int,
    delay_seconds: float,
    timeout_seconds: float,
) -> bool:
    attempts = max(1, retries)
    for attempt in range(1, attempts + 1):
        error = check_pypi_version(package=PACKAGE, version=version, timeout_seconds=timeout_seconds)
        if error is None:
            return True
        if attempt == attempts:
            sys.stderr.write(error + "\n")
            return False
        time.sleep(max(0.0, delay_seconds))
    return False


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            handle.write(content)
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run CLI and existing smoke tests**

Run: `uv run pytest tests/test_published_upgrade_cli.py tests/test_published_package_smoke.py -q`

Expected: all tests pass.

Run: `uv run python scripts/check_published_upgrade.py --from-version 1.20.0 --to-version 1.21.0 --dry-run`

Expected: valid JSON containing three exact `uvx` commands and no network access.

- [ ] **Step 6: Commit the operator CLI**

```bash
git add scripts/check_published_package_smoke.py scripts/check_published_upgrade.py tests/test_published_upgrade_cli.py
git commit -m "feat: add published upgrade proof CLI"
```

### Task 6: Add Manual External Automation

**Files:**
- Create: `.github/workflows/published-upgrade-proof.yml`
- Create: `tests/test_published_upgrade_workflow.py`

- [ ] **Step 1: Write a failing workflow contract test**

Create `tests/test_published_upgrade_workflow.py`:

```python
from pathlib import Path

_WORKFLOW = Path(".github/workflows/published-upgrade-proof.yml")


def test_published_upgrade_workflow_is_manual_and_uploads_only_successful_evidence() -> None:
    workflow = _WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert "from_version:" in workflow
    assert "to_version:" in workflow
    assert "scripts/check_published_upgrade.py" in workflow
    assert "actions/upload-artifact@v7" in workflow
    assert "if-no-files-found: error" in workflow
```

- [ ] **Step 2: Run the test and verify the workflow is missing**

Run: `uv run pytest tests/test_published_upgrade_workflow.py -q`

Expected: FAIL with `FileNotFoundError`.

- [ ] **Step 3: Create the manually dispatched workflow**

Create `.github/workflows/published-upgrade-proof.yml`:

```yaml
name: Published upgrade proof

on:
  workflow_dispatch:
    inputs:
      from_version:
        description: Published version to upgrade from
        required: true
        default: "1.20.0"
        type: string
      to_version:
        description: Published version to upgrade to
        required: true
        default: "1.21.0"
        type: string

permissions:
  contents: read

jobs:
  prove-upgrade:
    runs-on: ubuntu-latest
    timeout-minutes: 20

    steps:
      - name: Check out repository
        uses: actions/checkout@v5

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: false

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.13"

      - name: Install current client and probe dependencies
        run: uv sync --frozen --dev

      - name: Prove published upgrade
        run: >
          uv run python scripts/check_published_upgrade.py
          --from-version "${{ inputs.from_version }}"
          --to-version "${{ inputs.to_version }}"
          --observed-on "$(date -u +%F)"
          --output artifacts/published-upgrade-proof.json

      - name: Upload privacy-safe evidence
        uses: actions/upload-artifact@v7
        with:
          name: published-upgrade-proof
          path: artifacts/published-upgrade-proof.json
          if-no-files-found: error
          retention-days: 30
```

- [ ] **Step 4: Run the workflow contract and project scaffold tests**

Run: `uv run pytest tests/test_published_upgrade_workflow.py tests/test_project_scaffolding.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit external automation**

```bash
git add .github/workflows/published-upgrade-proof.yml tests/test_published_upgrade_workflow.py
git commit -m "ci: add published upgrade proof workflow"
```

### Task 7: Generate And Record The First Published Upgrade Evidence

**Files:**
- Create: `docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-03.json`
- Modify: `docs/STATUS.md`
- Modify: `tests/test_published_upgrade_workflow.py`

- [ ] **Step 1: Run the real network-dependent probe**

Run:

```bash
uv run python scripts/check_published_upgrade.py \
  --from-version 1.20.0 \
  --to-version 1.21.0 \
  --observed-on 2026-08-03 \
  --output docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-03.json
```

Expected: exit `0`; report status `pass`; three matrix rows; old-surface subset `true`; mode parity `true`; artifact
continuity `true`. If it fails, keep the failed JSON out of `docs/host-evidence`, retain the sanitized stderr report,
and treat the failure as a product defect rather than changing expected values.

- [ ] **Step 2: Add a committed-evidence privacy and status guard**

Append to `tests/test_published_upgrade_workflow.py`:

```python
import json

_EVIDENCE = Path("docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-03.json")


def test_committed_upgrade_evidence_is_passing_and_privacy_safe() -> None:
    content = _EVIDENCE.read_text(encoding="utf-8")
    report = json.loads(content)

    assert report["status"] == "pass"
    assert report["from_version"] == "1.20.0"
    assert report["to_version"] == "1.21.0"
    assert report["compatibility"]["old_surface_is_subset"] is True
    assert report["artifact_continuity"]["ok"] is True
    assert "/Users/" not in content
    assert "/home/" not in content
    assert "ALBU_MCP_" not in content
    assert "GH_TOKEN" not in content
    assert "GITHUB_TOKEN" not in content
```

- [ ] **Step 3: Record the machine-evidence boundary in project status**

Append this section to `docs/STATUS.md` before `## Host Evidence`:

```markdown
## Protocol Compatibility Evidence

Status: `passed`

Published upgrade: `1.20.0 -> 1.21.0`

Evidence: [privacy-safe machine report](host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-03.json)

Scope: Published-package stdio protocol negotiation and artifact continuity. This is not Streamable HTTP or real-host UI evidence.
```

- [ ] **Step 4: Verify committed evidence and status**

Run: `uv run pytest tests/test_published_upgrade_workflow.py -q`

Expected: `2 passed`.

Run: `git diff --check`

Expected: no output.

- [ ] **Step 5: Commit the observed evidence separately**

```bash
git add docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-03.json docs/STATUS.md tests/test_published_upgrade_workflow.py
git commit -m "docs: record published upgrade proof"
```

### Task 8: Run The Full Quality And Contract Gates

**Files:**
- Verify only; do not bump versions, create a tag, or change public snapshots.

- [ ] **Step 1: Run all focused compatibility tests**

Run:

```bash
uv run pytest \
  tests/test_mcp_http_harness.py \
  tests/test_mcp_http_conformance.py \
  tests/test_upgrade_proof.py \
  tests/test_published_upgrade_runtime.py \
  tests/test_published_upgrade_cli.py \
  tests/test_published_upgrade_workflow.py \
  tests/test_published_package_smoke.py -q
```

Expected: all focused tests pass with no leaked tasks, subprocesses, or sockets.

- [ ] **Step 2: Run the complete Python quality gates**

Run: `uv run pytest`

Expected: all tests pass.

Run: `uv run ruff check .`

Expected: no diagnostics.

Run: `uv run ruff format --check .`

Expected: all files already formatted.

Run: `uv run ty check`

Expected: no diagnostics.

- [ ] **Step 3: Re-prove stable public contracts and release readiness**

Run: `uv run python scripts/check_contract_snapshots.py`

Expected: MCP, CLI, and output snapshots are current with no public identifier removal.

Run: `uv run python scripts/check_release_readiness.py`

Expected: release readiness passes without a version bump.

Run: `uv run python scripts/run_golden_evals.py --work-dir /tmp/albu-mcp-http-proof-golden`

Expected: all golden MCP flows pass.

Run: `uv build`

Expected: wheel and source distribution build successfully.

- [ ] **Step 4: Review branch scope and release policy**

Run: `git diff --stat main...HEAD`

Expected: only test support, conformance tests, upgrade-proof code, operator automation, and evidence files appear.

Run: `git status --short`

Expected: empty output.

If every probe passes, do not create a release: this package changes assurance, not the public product. If a probe
exposes a runtime defect, preserve the failing regression test, implement the smallest compatible fix in a separate
patch-release commit, and release `1.21.1` only after repeating this entire matrix.

- [ ] **Step 5: Push, open a ready pull request, wait for CI, and merge**

```bash
git push
gh pr create \
  --base main \
  --head codex/http-conformance-upgrade-proof \
  --title "test: prove Streamable HTTP and published upgrades" \
  --body "Adds real loopback Streamable HTTP conformance, a privacy-safe published 1.20.0 to 1.21.0 upgrade probe, manual automation, and observed artifact-continuity evidence. No public MCP contract or package version changes."
gh pr checks --watch
gh pr merge --squash --delete-branch
```

Expected: required checks pass and the PR merges into `main`; no tag or GitHub release is created.
