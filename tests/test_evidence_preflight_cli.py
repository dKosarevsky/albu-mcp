from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_empty_records(tmp_path: Path) -> tuple[Path, Path]:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")
    return host_records, beta_records


def _write_template_manifest(directory: Path, *, host: str) -> Path:
    path = directory / f"{host.lower().replace(' ', '-')}-evidence-session-manifest.json"
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


def _write_filled_manifest(directory: Path, *, host: str) -> Path:
    path = directory / f"{host.lower().replace(' ', '-')}-evidence-session-manifest.json"
    path.write_text(
        json.dumps(
            {
                "manifest_status": "filled",
                "host": host,
                "status": "passed",
                "date": "2026-07-05",
                "reviewer": "Release operator",
                "evidence": (
                    f"Reviewer observed real {host} MCP host UI, listed AlbumentationsX MCP tools, "
                    "ran run_host_smoke_check, and confirmed preview_ready=true."
                ),
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


def _write_template_beta_drafts(beta_dir: Path) -> Path:
    beta_dir.mkdir()
    drafts = [
        "dataset_health_before_training",
        "noisy_preview_tuning",
        "robustness_distortion_variants",
    ]
    buckets = {
        "dataset_health_before_training": "dataset_quality_gap",
        "noisy_preview_tuning": "review_agent_v3_gap",
        "robustness_distortion_variants": "workflow_fit_gap",
    }
    for workflow_id in drafts:
        slug = workflow_id.replace("_", "-")
        (beta_dir / f"{slug}-beta-response.json").write_text(
            json.dumps(
                {
                    "workflow_id": workflow_id,
                    "status": "needs_followup" if workflow_id == "noisy_preview_tuning" else "passed",
                    "attempt_date": "2026-07-05",
                    "participant_role": "ML practitioner",
                    "summary": f"redacted {workflow_id} outcome; replace with the participant's safe workflow summary",
                    "triage_bucket": buckets[workflow_id],
                    "artifact_refs": ["docs/assets/demo/demo_report.md"],
                    "private_data_included": False,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return beta_dir


def _write_filled_beta_drafts(beta_dir: Path) -> Path:
    beta_dir.mkdir()
    drafts = [
        (
            "dataset_health_before_training",
            "dataset_quality_gap",
            "Participant found a dataset class imbalance before training.",
        ),
        (
            "noisy_preview_tuning",
            "review_agent_v3_gap",
            "Participant accepted softened noise after reviewing the second contact sheet.",
        ),
        (
            "robustness_distortion_variants",
            "workflow_fit_gap",
            "Participant selected the distortion variant set that preserved object recognizability.",
        ),
    ]
    for workflow_id, triage_bucket, summary in drafts:
        slug = workflow_id.replace("_", "-")
        (beta_dir / f"{slug}-beta-response.json").write_text(
            json.dumps(
                {
                    "workflow_id": workflow_id,
                    "status": "needs_followup" if workflow_id == "noisy_preview_tuning" else "passed",
                    "attempt_date": "2026-07-05",
                    "participant_role": "ML practitioner",
                    "summary": summary,
                    "triage_bucket": triage_bucket,
                    "artifact_refs": ["docs/assets/demo/demo_report.md"],
                    "private_data_included": False,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return beta_dir


def test_evidence_preflight_reports_blocked_template_inputs_without_writing(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")
    template_dir = tmp_path / "operator-packets"
    template_dir.mkdir()
    codex_manifest = _write_template_manifest(template_dir, host="Codex")
    claude_manifest = _write_template_manifest(template_dir, host="Claude Code")
    beta_dir = _write_template_beta_drafts(tmp_path / "beta-response-templates")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "preflight",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--host-manifest",
            str(codex_manifest),
            "--host-manifest",
            str(claude_manifest),
            "--beta-dir",
            str(beta_dir),
            "--template-host-manifest",
            str(codex_manifest),
            "--template-host-manifest",
            str(claude_manifest),
            "--template-beta-dir",
            str(beta_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["preflight_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["template_guard_status"] == "passed"
    assert payload["import_wizard_status"] == "blocked"
    assert payload["proof_status"] == "blocked"
    assert payload["rc_preview_status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "import_wizard:host_manifest_not_ready",
        "import_wizard:beta_draft_not_ready",
    ]
    assert "rc_unblock:p0_host_evidence_missing_or_blocked" in payload["evidence_blockers"]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_evidence_preflight_reports_ready_to_import_when_session_inputs_are_filled(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    template_dir = tmp_path / "operator-packets"
    template_dir.mkdir()
    template_codex = _write_template_manifest(template_dir, host="Codex")
    template_claude = _write_template_manifest(template_dir, host="Claude Code")
    template_beta_dir = _write_template_beta_drafts(tmp_path / "beta-response-templates")
    session_dir = tmp_path / "evidence-session"
    session_dir.mkdir()
    session_codex = _write_filled_manifest(session_dir, host="Codex")
    session_claude = _write_filled_manifest(session_dir, host="Claude Code")
    session_beta_dir = _write_filled_beta_drafts(tmp_path / "beta-responses")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "preflight",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--host-manifest",
            str(session_codex),
            "--host-manifest",
            str(session_claude),
            "--beta-dir",
            str(session_beta_dir),
            "--template-host-manifest",
            str(template_codex),
            "--template-host-manifest",
            str(template_claude),
            "--template-beta-dir",
            str(template_beta_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["preflight_status"] == "ready_to_import"
    assert payload["writes_records"] is False
    assert payload["template_guard_status"] == "passed"
    assert payload["import_wizard_status"] == "ready_to_import"
    assert payload["blocking_reasons"] == []
    assert payload["next_commands"][0].startswith("albu-mcp evidence import-wizard")
    assert "--import-ready" in payload["next_commands"][0]
    assert str(session_codex) in payload["next_commands"][0]
    assert str(session_beta_dir) in payload["next_commands"][0]
    assert payload["evidence_blockers"] == [
        "proof_status:Codex:manual_host_ui",
        "proof_status:Codex:first_10_minutes_replay",
        "proof_status:Claude Code:manual_host_ui",
        "proof_status:Claude Code:first_10_minutes_replay",
        "rc_unblock:p0_host_evidence_missing_or_blocked",
        "rc_unblock:beta_validation_incomplete",
    ]


def test_evidence_preflight_writes_markdown_report(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    template_dir = tmp_path / "operator-packets"
    template_dir.mkdir()
    codex_manifest = _write_template_manifest(template_dir, host="Codex")
    beta_dir = _write_template_beta_drafts(tmp_path / "beta-response-templates")
    output = tmp_path / "preflight.md"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "preflight",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--host-manifest",
            str(codex_manifest),
            "--beta-dir",
            str(beta_dir),
            "--template-host-manifest",
            str(codex_manifest),
            "--template-beta-dir",
            str(beta_dir),
            "--format",
            "markdown",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = output.read_text(encoding="utf-8")

    assert result.stdout == f"wrote evidence preflight to {output}\n"
    assert "# Evidence Preflight" in report
    assert "Preflight status: `blocked`" in report
    assert "Template guard: `passed`" in report
    assert "Import wizard: `blocked`" in report
