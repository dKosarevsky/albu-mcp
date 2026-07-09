from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def _write_empty_records(tmp_path: Path) -> tuple[Path, Path]:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")
    return host_records, beta_records


def _write_filled_manifest(tmp_path: Path, *, host: str) -> Path:
    path = tmp_path / f"{host.lower().replace(' ', '-')}-evidence-session-manifest.json"
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
            }
        ),
        encoding="utf-8",
    )
    return path


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
                "evidence": (
                    "TODO: replace with redacted reviewer-observed MCP host UI evidence before importing records."
                ),
                "artifacts": ["docs/assets/demo/demo_report.md"],
                "commands_used": ["run_host_smoke_check", "render_preview_batch"],
                "confirm_real_host_observed": False,
                "private_data_included": False,
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_beta_drafts(tmp_path: Path) -> Path:
    beta_dir = tmp_path / "beta-response-templates"
    beta_dir.mkdir()
    drafts = [
        (
            "dataset-health-before-training",
            {
                "workflow_id": "dataset_health_before_training",
                "status": "passed",
                "triage_bucket": "dataset_quality_gap",
                "summary": "Dataset health attempt found class imbalance before preview rendering.",
            },
        ),
        (
            "noisy-preview-tuning",
            {
                "workflow_id": "noisy_preview_tuning",
                "status": "needs_followup",
                "triage_bucket": "review_agent_v3_gap",
                "summary": "Noisy preview feedback identified one candidate that should be softened.",
            },
        ),
        (
            "robustness-distortion-variants",
            {
                "workflow_id": "robustness_distortion_variants",
                "status": "passed",
                "triage_bucket": "workflow_fit_gap",
                "summary": "Robustness variants matched the participant goal after reviewing the contact sheet.",
            },
        ),
    ]
    for slug, payload in drafts:
        (beta_dir / f"{slug}-beta-response.json").write_text(
            json.dumps(
                {
                    **payload,
                    "attempt_date": "2026-07-05",
                    "participant_role": "ML practitioner",
                    "artifact_refs": ["docs/assets/demo/demo_report.md"],
                    "private_data_included": False,
                }
            ),
            encoding="utf-8",
        )
    return beta_dir


def test_evidence_import_wizard_no_write_reports_missing_inputs(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "import-wizard",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--host-manifest",
            str(tmp_path / "missing-manifest.json"),
            "--beta-dir",
            str(tmp_path / "missing-beta-dir"),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["wizard_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["host_manifest_count"] == 1
    assert payload["beta_draft_count"] == 0
    assert payload["blocked_reasons"] == ["host_manifest_missing", "beta_dir_missing"]
    assert payload["host_manifests"] == [
        {
            "path": str(tmp_path / "missing-manifest.json"),
            "status": "blocked",
            "blocked_reason": "host_manifest_missing",
        }
    ]
    assert payload["beta_drafts"] == []
    assert payload["next_commands"] == [
        "Fill reviewer-observed host manifests before import.",
        "Fill privacy-safe beta response drafts before import.",
    ]
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_evidence_import_wizard_imports_ready_inputs(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    codex_manifest = _write_filled_manifest(tmp_path, host="Codex")
    claude_manifest = _write_filled_manifest(tmp_path, host="Claude Code")
    beta_dir = _write_beta_drafts(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "import-wizard",
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
            "--import-ready",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    host_payload = json.loads(host_records.read_text(encoding="utf-8"))
    beta_payload = json.loads(beta_records.read_text(encoding="utf-8"))

    assert payload["wizard_status"] == "imported"
    assert payload["writes_records"] is True
    assert payload["host_manifest_count"] == 2
    assert payload["beta_draft_count"] == 3
    assert payload["blocked_reasons"] == []
    assert payload["post_import_cycle_status"] == "ready_for_first_product_fix"
    assert {record["host"] for record in host_payload["manual_host_ui"]} == {"Codex", "Claude Code"}
    assert {record["host"] for record in host_payload["first_10_minutes_replay"]} == {"Codex", "Claude Code"}
    assert {record["workflow_id"] for record in beta_payload["records"]} == {
        "dataset_health_before_training",
        "noisy_preview_tuning",
        "robustness_distortion_variants",
    }


def test_evidence_import_wizard_writes_no_write_preflight_report(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    codex_manifest = _write_filled_manifest(tmp_path, host="Codex")
    claude_manifest = _write_filled_manifest(tmp_path, host="Claude Code")
    beta_dir = _write_beta_drafts(tmp_path)
    output = tmp_path / "preflight" / "evidence-import-wizard-preflight.md"
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "import-wizard",
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

    assert result.stdout == f"wrote evidence import-wizard to {output}\n"
    assert "# Evidence Import Wizard" in report
    assert "Wizard status: `ready_to_import`" in report
    assert "Writes records: `false`" in report
    assert str(codex_manifest) in report
    assert str(claude_manifest) in report
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_evidence_import_wizard_markdown_explains_template_manifest_blockers(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    codex_manifest = _write_template_manifest(tmp_path, host="Codex")
    claude_manifest = _write_template_manifest(tmp_path, host="Claude Code")
    beta_dir = _write_beta_drafts(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "import-wizard",
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
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Wizard status: `blocked`" in result.stdout
    assert f"`{codex_manifest}`: `blocked`; validation=`template_requires_real_evidence`" in result.stdout
    assert f"`{claude_manifest}`: `blocked`; validation=`template_requires_real_evidence`" in result.stdout
    assert f"albu-mcp evidence validate-manifest --input {codex_manifest} --path {host_records} --format json" in (
        result.stdout
    )
    assert f"albu-mcp evidence proof-runner --input {claude_manifest} --path {host_records}" in result.stdout


def test_evidence_import_wizard_json_includes_per_host_remediation(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    codex_manifest = _write_template_manifest(tmp_path, host="Codex")
    beta_dir = _write_beta_drafts(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "import-wizard",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--host-manifest",
            str(codex_manifest),
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
    host_manifest = payload["host_manifests"][0]

    assert host_manifest["validation_status"] == "template_requires_real_evidence"
    assert host_manifest["required_updates"] == [
        "Set manifest_status to filled only after reviewer-observed real MCP host UI evidence exists.",
        "Replace TODO evidence with redacted reviewer-observed host UI and first-preview details.",
        "Set confirm_real_host_observed to true only after reviewer confirmation.",
        "Keep private_data_included false and artifact references privacy-safe.",
    ]
    assert host_manifest["next_commands"] == [
        f"albu-mcp evidence validate-manifest --input {codex_manifest} --path {host_records} --format json",
        (
            f"albu-mcp evidence proof-runner --input {codex_manifest} --path {host_records} "
            f"--beta-records {beta_records} --format json"
        ),
    ]


def test_evidence_import_wizard_json_includes_beta_template_remediation(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    codex_manifest = _write_filled_manifest(tmp_path, host="Codex")
    beta_dir = tmp_path / "beta-response-templates"
    beta_dir.mkdir()
    beta_draft = beta_dir / "noisy-preview-tuning-beta-response.json"
    beta_draft.write_text(
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

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "import-wizard",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--host-manifest",
            str(codex_manifest),
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
    draft = payload["beta_drafts"][0]

    assert payload["wizard_status"] == "blocked"
    assert payload["blocked_reasons"] == ["beta_draft_not_ready"]
    assert draft["status"] == "blocked"
    assert draft["validation_status"] == "template_requires_participant_evidence"
    assert draft["required_updates"] == [
        "Replace the template summary with a concrete redacted participant outcome.",
        "Keep artifact_refs privacy-safe and tied to reviewed workflow artifacts.",
        "Keep private_data_included false.",
    ]
    assert draft["next_commands"] == [
        f"albu-mcp beta response-validate --input {beta_draft} --format json",
        f"albu-mcp beta response-import --input {beta_draft} --path {beta_records}",
    ]


def test_evidence_import_wizard_rejects_blocked_import_without_partial_writes(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    codex_manifest = _write_filled_manifest(tmp_path, host="Codex")
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
            [
                sys.executable,
                "-m",
                "albumentationsx_mcp",
                "evidence",
                "import-wizard",
                "--host-records",
                str(host_records),
                "--beta-records",
                str(beta_records),
                "--host-manifest",
                str(codex_manifest),
                "--beta-dir",
                str(tmp_path / "missing-beta-dir"),
                "--import-ready",
                "--format",
                "json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
