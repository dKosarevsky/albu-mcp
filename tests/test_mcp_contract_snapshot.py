from __future__ import annotations

import json
from pathlib import Path

from albumentationsx_mcp.server import create_mcp_server
from scripts.export_mcp_contract import build_contract_snapshot, dump_contract_snapshot

_SNAPSHOT_PATH = Path("tests/fixtures/snapshots/mcp_contract.json")


def test_mcp_contract_snapshot_matches_public_surface() -> None:
    current = build_contract_snapshot(create_mcp_server())
    expected = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert current == expected


def test_mcp_contract_snapshot_fixture_is_canonical() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert _SNAPSHOT_PATH.read_text(encoding="utf-8") == dump_contract_snapshot(snapshot)


def test_guided_preview_tool_inputs_publish_runtime_bounds() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    tools = {tool["name"]: tool for tool in snapshot["tools"]}
    guided_properties = tools["run_first_preview"]["parameters"]["properties"]
    trace_properties = tools["trace_preview_variant"]["parameters"]["properties"]

    assert {
        key: guided_properties["max_images"][key]
        for key in ("minimum", "maximum", "default")
    } == {"minimum": 1, "maximum": 8, "default": 8}
    assert trace_properties["image_index"]["minimum"] == 0
    assert trace_properties["variant_index"]["minimum"] == 0
