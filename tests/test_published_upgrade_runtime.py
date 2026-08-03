from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    import pytest


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
        ("1.21.0", "auto"),
    ]
    assert report["matrix"][0]["negotiated_protocol"] == LATEST_HANDSHAKE_VERSION
    assert report["matrix"][2]["client_mode"] == LATEST_MODERN_VERSION
    assert report["matrix"][2]["negotiated_protocol"] == LATEST_MODERN_VERSION
    assert report["artifact_continuity"]["content_unchanged"] is True
    assert str(tmp_path) not in encoded
