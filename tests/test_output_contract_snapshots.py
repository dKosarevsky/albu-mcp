from __future__ import annotations

import json
from pathlib import Path

from scripts.export_output_contracts import build_output_contract_snapshot, dump_output_contract_snapshot

_SNAPSHOT_PATH = Path("tests/fixtures/snapshots/output_contracts.json")


def test_output_contract_snapshot_matches_representative_outputs(tmp_path: Path) -> None:
    current = build_output_contract_snapshot(tmp_path)
    expected = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert current == expected


def test_output_contract_snapshot_fixture_is_canonical() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert _SNAPSHOT_PATH.read_text(encoding="utf-8") == dump_output_contract_snapshot(snapshot)
