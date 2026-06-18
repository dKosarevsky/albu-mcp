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


def test_output_contract_snapshot_includes_preview_request_validation_examples() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert "validate_preview_request_ready" in snapshot
    assert "validate_preview_request_missing_input" in snapshot
    assert "validate_preview_request_outside_allowed_root" in snapshot
    ready = snapshot["validate_preview_request_ready"]
    missing = snapshot["validate_preview_request_missing_input"]
    outside = snapshot["validate_preview_request_outside_allowed_root"]
    assert ready["valid"] is True
    assert missing["valid"] is False
    assert outside["valid"] is False
    assert "input_path_missing" in {check["code"] for check in missing["checks"]}
    assert "input_path_outside_allowed_root" in {check["code"] for check in outside["checks"]}


def test_output_contract_snapshot_includes_interactive_tuning_session_export() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert "export_tuning_session" in snapshot
    export = snapshot["export_tuning_session"]
    content = json.loads(export["content"])

    assert export["format"] == "json"
    assert export["session_id"] == "<session-id>"
    assert export["status"] == "accepted"
    assert export["step_count"] == 1
    assert export["artifact"]["uri"] == "artifact://tuning-sessions/tuning-session-<session-id>.json"
    assert export["artifact"]["mime_type"] == "application/json"
    assert content["accepted_candidate_run_id"] == "candidate-a"
    assert content["steps"][0]["step_id"] == "<step-id>"


def test_output_contract_snapshot_includes_interactive_tuning_session_lifecycle() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert snapshot["close_tuning_session_rejected"]["status"] == "rejected"
    assert snapshot["archive_tuning_session"]["status"] == "archived"
    assert snapshot["cleanup_tuning_sessions"]["deleted_count"] == 1
    assert snapshot["cleanup_tuning_sessions"]["protected_active_count"] == 1


def test_output_contract_snapshot_links_preview_report_session_artifacts() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    report = snapshot["export_preview_report"]

    assert report["tuning_session_artifacts"] == [
        {
            "kind": "report",
            "mime_type": "text/markdown",
            "path": "<artifact-path>/tuning-session-<session-id>.md",
            "sha256": "<sha256>",
            "size_bytes": "<size-bytes>",
            "uri": "artifact://tuning-sessions/tuning-session-<session-id>.md",
        }
    ]
    assert (
        "[tuning-session-<session-id>.md](artifact://tuning-sessions/tuning-session-<session-id>.md)"
        in report["content"]
    )
