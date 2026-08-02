from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mcp import Client
from mcp.types import TextResourceContents
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION

from albumentationsx_mcp.adapters.mcp.registration import surface_for_profile
from albumentationsx_mcp.capabilities import CapabilityProfile
from albumentationsx_mcp.server import ServerSettings, create_mcp_server


@pytest.mark.parametrize(
    ("mode", "expected_version"),
    [
        pytest.param(LATEST_MODERN_VERSION, LATEST_MODERN_VERSION, id="modern"),
        pytest.param("legacy", LATEST_HANDSHAKE_VERSION, id="legacy"),
    ],
)
def test_full_profile_supports_modern_and_legacy_protocols(
    tmp_path: Path,
    mode: str,
    expected_version: str,
) -> None:
    async def exercise_protocol() -> None:
        server = create_mcp_server(
            ServerSettings(
                allowed_roots=[tmp_path],
                artifact_root=tmp_path / "artifacts",
            )
        )

        async with Client(server, mode=mode) as client:
            tools = await client.list_tools()
            result = await client.call_tool("search_transforms", {"query": "blur", "limit": 3})
            resource = await client.read_resource("albumentationsx://examples/client-smoke")

            assert client.protocol_version == expected_version
            assert {tool.name for tool in tools.tools} == set(surface_for_profile(CapabilityProfile.FULL).tools)
            assert tools.result_type == "complete"
            assert result.is_error is False
            assert result.result_type == "complete"
            assert result.structured_content is not None
            assert result.structured_content["results"]
            assert resource.result_type == "complete"
            assert isinstance(resource.contents[0], TextResourceContents)
            assert "run_host_smoke_check" in resource.contents[0].text

    asyncio.run(exercise_protocol())
