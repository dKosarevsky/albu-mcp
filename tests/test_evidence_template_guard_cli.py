from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_template_manifest(tmp_path: Path, *, host: str) -> Path:
    path = tmp_path / f"{host.lower().replace(' ', '-')}-evidence-session-manifest.json"
    path.write_text(
        json.dumps(
            {
                "manifest_status": "template",
                "host": host,
                "status": "pending",
                "date": "2026-07-05",
                "reviewer": "Release operator",
                "evidence": "TODO: replace with reviewer-observed real MCP host UI evidence.",
                "artifacts": ["docs/assets/demo/demo_report.md"],
                "commands_used": ["run_host_smoke_check"],
                "confirm_real_host_observed": False,
                "private_data_included": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_ready_manifest(tmp_path: Path, *, host: str) -> Path:
    path = tmp_path / f"{host.lower().replace(' ', '-')}-evidence-session-manifest.json"
    path.write_text(
        json.dumps(
            {
                "manifest_status": "filled",
                "host": host,
                "status": "passed",
                "date": "2026-07-05",
                "reviewer": "Release operator",
                "evidence": f"Reviewer observed real {host} MCP host UI and first preview workflow.",
                "artifacts": [f"docs/operator-evidence/{host.lower().replace(' ', '-')}-run-notes.md"],
                "commands_used": ["run_host_smoke_check", "render_preview_batch"],
                "confirm_real_host_observed": True,
                "private_data_included": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_template_beta_draft(beta_dir: Path) -> Path:
    beta_dir.mkdir()
    path = beta_dir / "noisy-preview-tuning-beta-response.json"
    path.write_text(
        json.dumps(
            {
                "workflow_id": "noisy_preview_tuning",
                "status": "needs_followup",
                "attempt_date": "2026-07-05",
                "participant_role": "ML practitioner",
                "summary": (
                    "redacted noisy_preview_tuning outcome; replace with the participant's safe workflow summary"
                ),
                "triage_bucket": "review_agent_v3_gap",
                "artifact_refs": ["docs/assets/demo/demo_report.md"],
                "private_data_included": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_ready_beta_draft(beta_dir: Path) -> Path:
    beta_dir.mkdir(exist_ok=True)
    path = beta_dir / "dataset-health-before-training-beta-response.json"
    path.write_text(
        json.dumps(
            {
                "workflow_id": "dataset_health_before_training",
                "status": "passed",
                "attempt_date": "2026-07-05",
                "participant_role": "ML practitioner",
                "summary": "Participant found a dataset class imbalance before starting model training.",
                "triage_bucket": "dataset_quality_gap",
                "artifact_refs": ["docs/assets/demo/demo_report.md"],
                "private_data_included": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_evidence_template_guard_passes_when_templates_remain_blocked(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    manifest = _write_template_manifest(tmp_path, host="Codex")
    beta_dir = tmp_path / "beta-response-templates"
    beta_draft = _write_template_beta_draft(beta_dir)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "template-guard",
            "--host-records",
            str(host_records),
            "--host-manifest",
            str(manifest),
            "--beta-dir",
            str(beta_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["guard_status"] == "passed"
    assert payload["writes_records"] is False
    assert payload["violation_count"] == 0
    assert payload["host_manifests"][0]["guard_status"] == "blocked_as_template"
    assert payload["host_manifests"][0]["validation_status"] == "template_requires_real_evidence"
    assert payload["beta_drafts"][0]["guard_status"] == "blocked_as_template"
    assert payload["beta_drafts"][0]["validation_status"] == "template_requires_participant_evidence"
    assert payload["guarded_paths"] == [str(manifest), str(beta_draft)]


def test_evidence_template_guard_reports_ready_drafts_without_writing(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    host_before = host_records.read_text(encoding="utf-8")
    manifest = _write_template_manifest(tmp_path, host="Codex")
    beta_dir = tmp_path / "beta-response-templates"
    _write_template_beta_draft(beta_dir)
    ready_draft = _write_ready_beta_draft(beta_dir)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "template-guard",
            "--host-records",
            str(host_records),
            "--host-manifest",
            str(manifest),
            "--beta-dir",
            str(beta_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    unsafe = next(item for item in payload["beta_drafts"] if item["path"] == str(ready_draft))

    assert payload["guard_status"] == "failed"
    assert payload["writes_records"] is False
    assert payload["violation_count"] == 1
    assert payload["violations"] == [str(ready_draft)]
    assert unsafe["guard_status"] == "unsafe_ready_to_import"
    assert unsafe["validation_status"] == "ready_to_import"
    assert host_records.read_text(encoding="utf-8") == host_before


def test_evidence_template_guard_fails_when_beta_template_directory_is_empty(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    manifest = _write_template_manifest(tmp_path, host="Codex")
    beta_dir = tmp_path / "beta-response-templates"
    beta_dir.mkdir()

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "template-guard",
            "--host-records",
            str(host_records),
            "--host-manifest",
            str(manifest),
            "--beta-dir",
            str(beta_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["guard_status"] == "failed"
    assert payload["violation_count"] == 1
    assert payload["beta_drafts"] == [
        {
            "path": str(beta_dir),
            "guard_status": "missing",
            "violation_reason": "beta_drafts_missing",
        }
    ]


def test_evidence_template_guard_strict_exits_nonzero_for_ready_template_paths(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    manifest = _write_ready_manifest(tmp_path, host="Codex")
    beta_dir = tmp_path / "beta-response-templates"
    _write_template_beta_draft(beta_dir)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "template-guard",
            "--host-records",
            str(host_records),
            "--host-manifest",
            str(manifest),
            "--beta-dir",
            str(beta_dir),
            "--strict",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "evidence template-guard failed: 1 importable template path" in result.stderr
