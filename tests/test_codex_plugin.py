from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST_PATH = ROOT / ".codex-plugin" / "plugin.json"
MCP_MANIFEST_PATH = ROOT / ".mcp.json"


def test_codex_plugin_bundle_exposes_canonical_skill_and_pinned_server() -> None:
    assert PLUGIN_MANIFEST_PATH.is_file()
    assert MCP_MANIFEST_PATH.is_file()

    plugin = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
    mcp = json.loads(MCP_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert plugin["name"] == "albumentationsx-mcp"
    assert plugin["version"] == "1.15.0"
    assert plugin["skills"] == "./skills/"
    assert plugin["mcpServers"] == "./.mcp.json"
    assert plugin["interface"]["displayName"] == "AlbumentationsX MCP"
    assert plugin["interface"]["category"] == "Developer Tools"
    assert len(plugin["interface"]["defaultPrompt"]) <= 3
    assert all(len(prompt) <= 128 for prompt in plugin["interface"]["defaultPrompt"])

    assert list(mcp) == ["mcpServers"]
    assert list(mcp["mcpServers"]) == ["albumentationsx"]
    server = mcp["mcpServers"]["albumentationsx"]
    assert server["command"] == "uvx"
    assert server["args"] == [
        "--from",
        "albumentationsx-mcp==1.15.0",
        "albumentationsx-mcp",
    ]
    assert server["env_vars"] == [
        "ALBU_MCP_ALLOWED_ROOTS",
        "ALBU_MCP_ARTIFACT_ROOT",
        "ALBU_MCP_MAX_PREVIEW_RUNS",
    ]
    assert "--allowed-root" not in server["args"]
    assert "--artifact-root" not in server["args"]
    assert "env" not in server
