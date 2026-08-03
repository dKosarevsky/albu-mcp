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
        apps = [create_mcp_server(_settings(tmp_path)).streamable_http_app(json_response=True) for _ in range(2)]
        async with run_loopback_mcp_cluster(apps) as cluster:
            async with Client(cluster.url, mode="auto") as client:
                tools = await client.list_tools(cache_mode="refresh")
                smoke = await client.call_tool("run_host_smoke_check", {"include_write_probe": False})
                preview = await client.call_tool(
                    "render_preview_batch",
                    {"request": _preview_request(image_path)},
                )
                assert preview.structured_content is not None
                run_id = preview.structured_content["run_id"]
                contact_sheet_uri = next(
                    item["uri"] for item in preview.structured_content["artifacts"] if item["kind"] == "contact_sheet"
                )
                manifest = await client.call_tool("get_preview_manifest", {"run_id": run_id})
                contact_sheet = await client.read_resource(contact_sheet_uri)
                first_protocol = client.protocol_version

            async with Client(cluster.url, mode="auto") as reconnected:
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
    observed_names = {_header_map(item)["mcp-name"] for item in successful if "mcp-name" in _header_map(item)}
    assert {
        "run_host_smoke_check",
        "render_preview_batch",
        "get_preview_manifest",
    }.issubset(observed_names)


def test_legacy_streamable_http_keeps_initialize_and_resource_flow(tmp_path: Path) -> None:
    async def exercise() -> dict[str, Any]:
        app = create_mcp_server(_settings(tmp_path)).streamable_http_app(json_response=True)
        async with (
            run_loopback_mcp_cluster([app]) as cluster,
            Client(cluster.url, mode="legacy") as client,
        ):
            tools = await client.list_tools(cache_mode="refresh")
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


def test_streamable_http_negotiates_apps_and_preserves_fallback(tmp_path: Path) -> None:
    image_path = tmp_path / "apps.png"
    Image.new("RGB", (16, 16), (128, 96, 64)).save(image_path)

    async def exercise() -> dict[str, Any]:
        app = create_mcp_server(_settings(tmp_path)).streamable_http_app(json_response=True)
        extension = advertise(EXTENSION_ID, {"mimeTypes": [APP_MIME_TYPE]})
        async with run_loopback_mcp_cluster([app]) as cluster:
            async with Client(
                cluster.url,
                mode="auto",
                extensions=[extension],
            ) as app_client:
                app_capabilities = app_client.server_capabilities.model_dump(by_alias=True, exclude_none=True)
                app_result = await app_client.call_tool(
                    "render_preview_batch",
                    {"request": _preview_request(image_path)},
                )

            async with Client(cluster.url, mode="auto") as ordinary_client:
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
    assert result["ordinary_capabilities"]["extensions"][EXTENSION_ID] == {}
    assert result["app_result"].is_error is False
    assert result["ordinary_result"].is_error is False
    assert result["app_result"].structured_content["run_id"]
    assert result["ordinary_result"].structured_content["run_id"]
