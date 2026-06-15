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


def test_output_contract_snapshot_includes_diagnostics_examples() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert "diagnose_environment_ok" in snapshot
    assert "diagnose_environment_missing_allowed_root" in snapshot
    missing_root = snapshot["diagnose_environment_missing_allowed_root"]
    assert missing_root["status"] == "warning"
    assert "remediation_actions" in missing_root
    assert [action["code"] for action in missing_root["remediation_actions"]] == ["fix_allowed_root"]


def test_output_contract_snapshot_includes_host_smoke_examples() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert "run_host_smoke_check_ready" in snapshot
    assert "run_host_smoke_check_missing_allowed_root" in snapshot
    ready = snapshot["run_host_smoke_check_ready"]
    blocked = snapshot["run_host_smoke_check_missing_allowed_root"]
    assert ready["preview_ready"] is True
    assert ready["preview_request_template"]["tool"] == "render_preview_batch"
    assert ready["preview_request_template"]["request"]["variants_per_image"] == 1
    assert blocked["preview_ready"] is False
    assert blocked["preview_request_template"] is None
