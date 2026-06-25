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


def test_output_contract_snapshot_includes_review_packet_handoff() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert "build_review_packet_ready" in snapshot
    packet = snapshot["build_review_packet_ready"]
    assert packet["status"] == "ok"
    assert packet["preview_ready"] is True
    assert packet["recommended_next_tool"] == "validate_preview_request"
    assert packet["preview_request_template"]["tool"] == "render_preview_batch"
    assert "export_preview_report" in packet["tool_sequence"]
    assert packet["report_handoff"]["resource"] == "albumentationsx://examples/report-handoff"


def test_output_contract_snapshot_includes_dataset_quality_report() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert "inspect_dataset_quality_ready" in snapshot
    report = snapshot["inspect_dataset_quality_ready"]
    assert report["status"] == "warning"
    assert report["image_count"] == 4
    assert report["sampled_image_count"] == 4
    assert report["aggregate"]["image_count"] == 4
    assert report["split_distribution"] == {"train": 3, "val": 1}
    assert report["class_distribution"] == {"cat": 3, "dog": 1}
    assert report["image_size_summary"]["aspect_ratio_min"] == 0.5
    assert report["image_size_summary"]["aspect_ratio_max"] == 1.5
    assert report["duplicate_image_count"] == 2
    assert report["annotation_summary"]["source_format"] == "coco"
    assert report["annotation_summary"]["annotated_image_count"] == 3
    assert report["annotation_summary"]["missing_annotation_count"] == 1
    assert report["annotation_summary"]["out_of_bounds_annotation_count"] == 1
    assert "build_review_packet" in report["recommended_next_tools"]
    assert "dataset_high_clipping" in {finding["code"] for finding in report["findings"]}
    assert "dataset_exact_duplicate_images" in {finding["code"] for finding in report["findings"]}
    assert "dataset_missing_annotations" in {finding["code"] for finding in report["findings"]}
    assert "dataset_out_of_bounds_annotations" in {finding["code"] for finding in report["findings"]}


def test_output_contract_snapshot_includes_review_agent_plan() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    plan = snapshot["plan_preview_review"]

    assert plan["decision"] == "revise_candidate"
    assert plan["recommended_next_tool"] == "adjust_pipeline"
    assert plan["feedback_tags"] == ["too_noisy:high"]
    assert plan["tuning_summary"]["quality_risk"] == "medium"
    assert any("render_preview_batch" in action for action in plan["next_actions"])


def test_output_contract_snapshot_includes_feedback_interpretation() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    interpretation = snapshot["interpret_preview_feedback"]

    assert interpretation["decision_hint"] == "revise"
    assert interpretation["recommended_next_tool"] == "adjust_pipeline"
    assert interpretation["feedback_tags"] == ["too_noisy:high", "object_unrecognizable:high"]


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
