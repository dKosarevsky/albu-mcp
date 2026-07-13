from __future__ import annotations

import asyncio
import base64
import sys
from pathlib import Path
from typing import Any

import numpy as np
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import BlobResourceContents, TextResourceContents
from PIL import Image
from pydantic import AnyUrl

from albumentationsx_mcp.mcp_app import (
    PREVIEW_ARTIFACT_URI_TEMPLATE,
    PREVIEW_REVIEW_APP_MIME_TYPE,
    PREVIEW_REVIEW_APP_URI,
)
from albumentationsx_mcp.server import create_mcp_server
from scripts.export_mcp_contract import build_contract_snapshot

_EXPECTED_TOOL_META = {
    "ui": {
        "resourceUri": PREVIEW_REVIEW_APP_URI,
        "visibility": ["model", "app"],
    }
}


def test_render_tools_publish_modern_preview_review_metadata() -> None:
    server = create_mcp_server()

    for tool_name in ["render_preview", "render_preview_batch"]:
        tool = server._tool_manager._tools[tool_name]
        assert tool.meta == _EXPECTED_TOOL_META
        assert tool.meta is not None
        assert "ui/resourceUri" not in tool.meta


def test_preview_review_resources_are_local_and_deny_network_access() -> None:
    server = create_mcp_server()
    app_resource = server._resource_manager._resources[PREVIEW_REVIEW_APP_URI]
    artifact_template = server._resource_manager._templates[PREVIEW_ARTIFACT_URI_TEMPLATE]
    html = asyncio.run(app_resource.read())

    assert app_resource.mime_type == PREVIEW_REVIEW_APP_MIME_TYPE
    assert app_resource.meta == {
        "ui": {
            "csp": {
                "connectDomains": [],
                "resourceDomains": [],
                "frameDomains": [],
                "baseUriDomains": [],
            },
            "prefersBorder": True,
        }
    }
    assert artifact_template.mime_type == "image/png"
    assert isinstance(html, str)
    assert 'data-albumentationsx-mcp-app="preview-review"' in html
    assert "https://" not in html
    assert "http://" not in html


def test_mcp_contract_snapshot_includes_app_metadata() -> None:
    snapshot = build_contract_snapshot(create_mcp_server())
    render_tool = next(tool for tool in snapshot["tools"] if tool["name"] == "render_preview_batch")
    app_resource = next(resource for resource in snapshot["resources"] if resource["uri"] == PREVIEW_REVIEW_APP_URI)

    assert render_tool["meta"] == _EXPECTED_TOOL_META
    assert app_resource["mime_type"] == PREVIEW_REVIEW_APP_MIME_TYPE
    assert app_resource["meta"]["ui"]["csp"]["connectDomains"] == []


def test_mcp_stdio_reads_preview_review_app_and_verified_image(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.fromarray(np.full((24, 24, 3), 128, dtype=np.uint8)).save(image_path)

    async def run_client() -> dict[str, Any]:
        params = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "albumentationsx_mcp",
                "--allowed-root",
                str(tmp_path),
                "--artifact-root",
                str(tmp_path / "artifacts"),
            ],
            cwd=str(Path.cwd()),
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            resources = await session.list_resources()
            templates = await session.list_resource_templates()
            app_result = await session.read_resource(AnyUrl(PREVIEW_REVIEW_APP_URI))
            preview_result = await session.call_tool(
                "render_preview_batch",
                {
                    "request": {
                        "input_paths": [str(image_path)],
                        "pipeline": {
                            "transforms": [{"name": "HorizontalFlip", "params": {}, "p": 1.0}],
                        },
                        "variants_per_image": 1,
                        "seed": 7,
                    }
                },
            )
            assert preview_result.isError is False
            assert preview_result.structuredContent is not None
            artifact_uri = next(
                item["uri"] for item in preview_result.structuredContent["artifacts"] if item["kind"] == "image"
            )
            image_result = await session.read_resource(AnyUrl(artifact_uri))
            app_content = app_result.contents[0]
            image_content = image_result.contents[0]
            assert isinstance(app_content, TextResourceContents)
            assert isinstance(image_content, BlobResourceContents)
            return {
                "render_meta": next(tool.meta for tool in tools.tools if tool.name == "render_preview_batch"),
                "resource_uris": {str(resource.uri) for resource in resources.resources},
                "template_uris": {str(template.uriTemplate) for template in templates.resourceTemplates},
                "app_mime_type": app_content.mimeType,
                "app_html": app_content.text,
                "image_mime_type": image_content.mimeType,
                "image_bytes": base64.b64decode(image_content.blob),
            }

    result = asyncio.run(run_client())

    assert result["render_meta"] == _EXPECTED_TOOL_META
    assert PREVIEW_REVIEW_APP_URI in result["resource_uris"]
    assert PREVIEW_ARTIFACT_URI_TEMPLATE in result["template_uris"]
    assert result["app_mime_type"] == PREVIEW_REVIEW_APP_MIME_TYPE
    assert 'data-albumentationsx-mcp-app="preview-review"' in result["app_html"]
    assert result["image_mime_type"] == "image/png"
    assert result["image_bytes"].startswith(b"\x89PNG\r\n\x1a\n")
