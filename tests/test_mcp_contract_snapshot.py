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
