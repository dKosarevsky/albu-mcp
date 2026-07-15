from __future__ import annotations

import json
from pathlib import Path

from scripts.export_cli_contract import build_cli_contract_snapshot, dump_cli_contract_snapshot

_SNAPSHOT_PATH = Path("tests/fixtures/snapshots/cli_contract.json")


def test_cli_contract_snapshot_matches_public_surface() -> None:
    expected = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert build_cli_contract_snapshot() == expected


def test_cli_contract_has_complete_inventory() -> None:
    snapshot = build_cli_contract_snapshot()

    assert snapshot["dispatch"]["groups"] == [
        "activation",
        "beta",
        "distribution",
        "evidence",
        "host",
        "intake",
        "preview",
        "rc",
        "trust",
    ]
    assert sum(len(group["commands"]) for group in snapshot["groups"].values()) == 84


def test_cli_contract_snapshot_fixture_is_canonical() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert _SNAPSHOT_PATH.read_text(encoding="utf-8") == dump_cli_contract_snapshot(snapshot)
