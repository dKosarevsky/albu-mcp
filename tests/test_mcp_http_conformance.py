from __future__ import annotations

import asyncio
import base64
from io import BytesIO
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.client import advertise
from mcp.server.apps import APP_MIME_TYPE, EXTENSION_ID, client_supports_apps
from mcp.server.mcpserver import Context  # noqa: TC002 - resolved at runtime by the tool registrar
from mcp.types import BlobResourceContents, TextResourceContents
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION
from PIL import Image

from albumentationsx_mcp.adapters.mcp.registration import surface_for_profile
from albumentationsx_mcp.capabilities import CapabilityProfile
from albumentationsx_mcp.mcp_app import PREVIEW_REVIEW_APP_URI
from albumentationsx_mcp.server import ServerSettings, create_mcp_server
from tests.support.mcp_http import HttpRequestTrace, run_loopback_mcp_cluster

_READ_TIMEOUT_SECONDS = 15.0


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


def _operation_posts(
    trace: tuple[HttpRequestTrace, ...],
    *,
    mcp_method: str,
    mcp_name: str | None = None,
) -> tuple[HttpRequestTrace, ...]:
    matching = [
        item
        for item in trace
        if item.method == "POST"
        and _header_map(item).get("mcp-method") == mcp_method
        and (mcp_name is None or _header_map(item).get("mcp-name") == mcp_name)
    ]
    assert len(matching) == 1, [(item.method, item.backend_index, _header_map(item)) for item in trace]
    return tuple(matching)


def _operation_backend(
    trace: tuple[HttpRequestTrace, ...],
    *,
    mcp_method: str,
    mcp_name: str | None = None,
) -> int:
    return _operation_posts(trace, mcp_method=mcp_method, mcp_name=mcp_name)[0].backend_index


def _assert_modern_result(result: dict[str, Any]) -> None:
    assert result["tools"] == set(surface_for_profile(CapabilityProfile.FULL).tools)
    assert result["smoke"]["preview_ready"] is True
    assert result["manifest"]["run_id"] == result["run_id"]
    assert result["restored"]["run_id"] == result["run_id"]
    assert result["restored"] == result["manifest"]
    assert result["protocols"] == (LATEST_MODERN_VERSION, LATEST_MODERN_VERSION)
    contact_sheet = result["contact_sheet"]
    assert isinstance(contact_sheet, BlobResourceContents)
    assert contact_sheet.mime_type == "image/png"
    png = base64.b64decode(contact_sheet.blob, validate=True)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(png)) as decoded:
        assert decoded.format == "PNG"
        decoded.verify()

    phases = result["phases"]
    phase_backends = {
        "discover": _operation_backend(phases["discover"], mcp_method="server/discover"),
        "list_tools": _operation_backend(phases["list_tools"], mcp_method="tools/list"),
        "smoke": _operation_backend(
            phases["smoke"],
            mcp_method="tools/call",
            mcp_name="run_host_smoke_check",
        ),
        "render_preview_batch": _operation_backend(
            phases["render_preview_batch"],
            mcp_method="tools/call",
            mcp_name="render_preview_batch",
        ),
        "get_preview_manifest": _operation_backend(
            phases["get_preview_manifest"],
            mcp_method="tools/call",
            mcp_name="get_preview_manifest",
        ),
        "read_contact_sheet": _operation_backend(
            phases["read_contact_sheet"],
            mcp_method="resources/read",
            mcp_name="<redacted>",
        ),
        "reconnect_discover": _operation_backend(
            phases["reconnect_discover"],
            mcp_method="server/discover",
        ),
        "reconnect_manifest": _operation_backend(
            phases["reconnect_manifest"],
            mcp_method="tools/call",
            mcp_name="get_preview_manifest",
        ),
    }
    render_backend = phase_backends["render_preview_batch"]
    assert {
        phase_backends["get_preview_manifest"],
        phase_backends["read_contact_sheet"],
    } - {render_backend}
    assert sum(len(trace) for trace in phases.values()) == len(result["trace"])
    assert result["trace"]
    assert all(200 <= item.status < 300 for item in result["trace"])
    assert all("mcp-session-id" not in _header_map(item) for item in result["trace"])
    assert all(_header_map(item)["mcp-protocol-version"] == LATEST_MODERN_VERSION for item in result["trace"])
    assert result["trace_overflow_count"] == 0


def test_modern_streamable_http_is_stateless_across_backends_and_reconnect(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.new("RGB", (24, 24), (96, 128, 160)).save(image_path)

    async def exercise() -> dict[str, Any]:
        apps = [create_mcp_server(_settings(tmp_path)).streamable_http_app(json_response=True) for _ in range(2)]
        async with run_loopback_mcp_cluster(apps) as cluster:
            phases: dict[str, tuple[HttpRequestTrace, ...]] = {}
            phase_start = len(cluster.trace)
            async with Client(
                cluster.url,
                mode="auto",
                read_timeout_seconds=_READ_TIMEOUT_SECONDS,
            ) as client:
                phases["discover"] = cluster.trace[phase_start:]
                phase_start = len(cluster.trace)
                tools = await client.list_tools(cache_mode="refresh")
                phases["list_tools"] = cluster.trace[phase_start:]
                phase_start = len(cluster.trace)
                smoke = await client.call_tool("run_host_smoke_check", {"include_write_probe": False})
                phases["smoke"] = cluster.trace[phase_start:]
                phase_start = len(cluster.trace)
                preview = await client.call_tool(
                    "render_preview_batch",
                    {"request": _preview_request(image_path)},
                )
                phases["render_preview_batch"] = cluster.trace[phase_start:]
                assert preview.structured_content is not None
                run_id = preview.structured_content["run_id"]
                contact_sheet_uri = next(
                    item["uri"] for item in preview.structured_content["artifacts"] if item["kind"] == "contact_sheet"
                )
                phase_start = len(cluster.trace)
                manifest = await client.call_tool("get_preview_manifest", {"run_id": run_id})
                phases["get_preview_manifest"] = cluster.trace[phase_start:]
                phase_start = len(cluster.trace)
                contact_sheet = await client.read_resource(contact_sheet_uri)
                phases["read_contact_sheet"] = cluster.trace[phase_start:]
                first_protocol = client.protocol_version

            phase_start = len(cluster.trace)
            async with Client(
                cluster.url,
                mode="auto",
                read_timeout_seconds=_READ_TIMEOUT_SECONDS,
            ) as reconnected:
                phases["reconnect_discover"] = cluster.trace[phase_start:]
                phase_start = len(cluster.trace)
                restored = await reconnected.call_tool("get_preview_manifest", {"run_id": run_id})
                phases["reconnect_manifest"] = cluster.trace[phase_start:]
                second_protocol = reconnected.protocol_version

            return {
                "tools": {tool.name for tool in tools.tools},
                "smoke": smoke.structured_content,
                "run_id": run_id,
                "manifest": manifest.structured_content,
                "restored": restored.structured_content,
                "contact_sheet": contact_sheet.contents[0],
                "protocols": (first_protocol, second_protocol),
                "phases": phases,
                "trace": cluster.trace,
                "trace_overflow_count": cluster.trace_overflow_count,
            }

    _assert_modern_result(asyncio.run(exercise()))


def test_legacy_streamable_http_keeps_initialize_and_resource_flow(tmp_path: Path) -> None:
    async def exercise() -> dict[str, Any]:
        app = create_mcp_server(_settings(tmp_path)).streamable_http_app(json_response=True)
        async with (
            run_loopback_mcp_cluster([app]) as cluster,
            Client(
                cluster.url,
                mode="legacy",
                read_timeout_seconds=_READ_TIMEOUT_SECONDS,
            ) as client,
        ):
            phases: dict[str, tuple[HttpRequestTrace, ...]] = {}
            phase_start = len(cluster.trace)
            tools = await client.list_tools(cache_mode="refresh")
            phases["list_tools"] = cluster.trace[phase_start:]
            phase_start = len(cluster.trace)
            search = await client.call_tool("search_transforms", {"query": "blur", "limit": 3})
            phases["search_transforms"] = cluster.trace[phase_start:]
            phase_start = len(cluster.trace)
            example = await client.read_resource("albumentationsx://examples/client-smoke")
            phases["read_example"] = cluster.trace[phase_start:]
            return {
                "protocol": client.protocol_version,
                "tools": {tool.name for tool in tools.tools},
                "search": search,
                "example": example.contents[0],
                "phases": phases,
                "trace": cluster.trace,
            }

    result = asyncio.run(exercise())

    assert result["protocol"] == LATEST_HANDSHAKE_VERSION
    assert result["tools"] == set(surface_for_profile(CapabilityProfile.FULL).tools)
    assert result["search"].is_error is False
    assert result["search"].structured_content["results"]
    assert isinstance(result["example"], TextResourceContents)
    assert "run_host_smoke_check" in result["example"].text
    phases = result["phases"]
    for phase in ("list_tools", "search_transforms", "read_example"):
        posts = [item for item in phases[phase] if item.method == "POST"]
        assert posts
        assert all(200 <= item.status < 300 for item in posts)
        assert {item.backend_index for item in posts} == {0}
        assert all(_header_map(item).get("mcp-session-id") == "<present>" for item in posts)


def test_streamable_http_negotiates_apps_and_preserves_fallback(tmp_path: Path) -> None:
    image_path = tmp_path / "apps.png"
    Image.new("RGB", (16, 16), (128, 96, 64)).save(image_path)

    async def exercise() -> dict[str, Any]:
        server = create_mcp_server(_settings(tmp_path))

        @server.tool(name="probe_apps_support")
        def probe_apps_support(ctx: Context[Any, Any]) -> dict[str, bool]:
            return {"supports_apps": client_supports_apps(ctx)}

        app = server.streamable_http_app(json_response=True)
        extension = advertise(EXTENSION_ID, {"mimeTypes": [APP_MIME_TYPE]})
        async with run_loopback_mcp_cluster([app]) as cluster:
            async with Client(
                cluster.url,
                mode="auto",
                extensions=[extension],
                read_timeout_seconds=_READ_TIMEOUT_SECONDS,
            ) as app_client:
                app_capabilities = app_client.server_capabilities.model_dump(by_alias=True, exclude_none=True)
                tools = await app_client.list_tools(cache_mode="refresh")
                app_support = await app_client.call_tool("probe_apps_support")
                app_resource_result = await app_client.read_resource(PREVIEW_REVIEW_APP_URI)
                app_result = await app_client.call_tool(
                    "render_preview_batch",
                    {"request": _preview_request(image_path)},
                )

            async with Client(
                cluster.url,
                mode="auto",
                read_timeout_seconds=_READ_TIMEOUT_SECONDS,
            ) as ordinary_client:
                ordinary_capabilities = ordinary_client.server_capabilities.model_dump(
                    by_alias=True,
                    exclude_none=True,
                )
                ordinary_support = await ordinary_client.call_tool("probe_apps_support")
                ordinary_result = await ordinary_client.call_tool(
                    "render_preview_batch",
                    {"request": _preview_request(image_path)},
                )

            return {
                "app_capabilities": app_capabilities,
                "ordinary_capabilities": ordinary_capabilities,
                "app_support": app_support,
                "ordinary_support": ordinary_support,
                "render_meta": next(tool.meta for tool in tools.tools if tool.name == "render_preview_batch"),
                "app_resource": app_resource_result.contents[0],
                "app_result": app_result,
                "ordinary_result": ordinary_result,
            }

    result = asyncio.run(exercise())

    assert result["app_capabilities"]["extensions"][EXTENSION_ID] == {}
    assert result["ordinary_capabilities"]["extensions"][EXTENSION_ID] == {}
    assert result["app_support"].is_error is False
    assert result["app_support"].structured_content == {"supports_apps": True}
    assert result["ordinary_support"].is_error is False
    assert result["ordinary_support"].structured_content == {"supports_apps": False}
    assert result["render_meta"] == {
        "ui": {
            "resourceUri": PREVIEW_REVIEW_APP_URI,
            "visibility": ["model", "app"],
        }
    }
    app_resource = result["app_resource"]
    assert isinstance(app_resource, TextResourceContents)
    assert app_resource.mime_type == APP_MIME_TYPE
    assert 'data-albumentationsx-mcp-app="preview-review"' in app_resource.text
    assert result["app_result"].is_error is False
    assert result["ordinary_result"].is_error is False
    assert result["app_result"].structured_content["run_id"]
    assert result["ordinary_result"].structured_content["run_id"]
