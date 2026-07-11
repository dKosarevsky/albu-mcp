from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ExecutionPackFixture = tuple[Path, Path, Path]


def _write_empty_records(tmp_path: Path) -> tuple[Path, Path]:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")
    return host_records, beta_records


def _generate_execution_pack(
    output_dir: Path,
    *,
    host_records: Path,
    beta_records: Path,
) -> None:
    subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack",
            "--date",
            "2026-07-11",
            "--reviewer",
            "Release operator",
            "--output-dir",
            str(output_dir),
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _fill_execution_pack(output_dir: Path) -> None:
    for manifest_path in output_dir.glob("*-evidence-session-manifest.json"):
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        host = payload["host"]
        payload.update(
            {
                "manifest_status": "filled",
                "status": "passed",
                "evidence": (
                    f"Reviewer observed real {host} MCP host UI, listed AlbumentationsX MCP tools, "
                    "ran run_host_smoke_check, rendered a bounded preview, and confirmed preview_ready=true."
                ),
                "artifacts": ["docs/assets/demo/demo_report.md"],
                "commands_used": ["run_host_smoke_check", "render_preview_batch"],
                "confirm_real_host_observed": True,
                "private_data_included": False,
            }
        )
        manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summaries = {
        "dataset_health_before_training": (
            "Participant found a class-balance issue before training and kept the redacted dataset health report."
        ),
        "noisy_preview_tuning": (
            "Participant softened one excessive noise candidate after reviewing the bounded contact sheet."
        ),
        "robustness_distortion_variants": (
            "Participant selected recognizable distortion variants that matched the intended robustness goal."
        ),
    }
    for draft_path in (output_dir / "beta-responses").glob("*-beta-response.json"):
        payload = json.loads(draft_path.read_text(encoding="utf-8"))
        payload.update(
            {
                "status": "passed",
                "summary": summaries[payload["workflow_id"]],
                "artifact_refs": ["docs/assets/demo/demo_report.md"],
                "private_data_included": False,
            }
        )
        draft_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@pytest.fixture
def execution_pack(tmp_path: Path) -> ExecutionPackFixture:
    output_dir = tmp_path / "evidence-execution"
    host_records, beta_records = _write_empty_records(tmp_path)
    _generate_execution_pack(output_dir, host_records=host_records, beta_records=beta_records)
    return output_dir, host_records, beta_records


def _run_execution_pack_status(
    *,
    output_dir: Path,
    host_records: Path,
    beta_records: Path,
    output_format: str = "json",
    output: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "albumentationsx_mcp",
        "evidence",
        "execution-pack-status",
        "--input-dir",
        str(output_dir),
        "--host-records",
        str(host_records),
        "--beta-records",
        str(beta_records),
        "--format",
        output_format,
    ]
    if output is not None:
        command.extend(["--output", str(output)])
    return subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        command,
        check=True,
        capture_output=True,
        text=True,
    )


def test_evidence_execution_pack_writes_no_record_session_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "evidence-execution"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack",
            "--date",
            "2026-07-09",
            "--reviewer",
            "Release operator",
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == f"wrote evidence execution-pack with 9 artifacts to {output_dir}\n"
    assert (output_dir / "README.md").exists()
    assert (output_dir / "session-plan.md").exists()
    assert (output_dir / "operator-checklist.md").exists()
    assert (output_dir / "post-session-commands.md").exists()
    assert (output_dir / "codex-evidence-session-manifest.json").exists()
    assert (output_dir / "claude-code-evidence-session-manifest.json").exists()
    assert (output_dir / "beta-responses/dataset-health-before-training-beta-response.json").exists()
    assert (output_dir / "beta-responses/noisy-preview-tuning-beta-response.json").exists()
    assert (output_dir / "beta-responses/robustness-distortion-variants-beta-response.json").exists()

    readme = (output_dir / "README.md").read_text(encoding="utf-8")
    commands = (output_dir / "post-session-commands.md").read_text(encoding="utf-8")
    codex_manifest = json.loads((output_dir / "codex-evidence-session-manifest.json").read_text(encoding="utf-8"))
    beta_response = json.loads(
        (output_dir / "beta-responses/noisy-preview-tuning-beta-response.json").read_text(encoding="utf-8")
    )

    assert "Generated execution packs are not evidence" in readme
    assert "writes_records: `false`" in readme
    assert codex_manifest["manifest_status"] == "template"
    assert codex_manifest["confirm_real_host_observed"] is False
    assert codex_manifest["private_data_included"] is False
    assert "replace with" in beta_response["summary"]
    assert beta_response["private_data_included"] is False
    assert "albu-mcp evidence preflight" in commands
    assert "albu-mcp evidence import-wizard" in commands
    assert "--import-ready" in commands
    assert str(output_dir / "codex-evidence-session-manifest.json") in commands
    assert str(output_dir / "claude-code-evidence-session-manifest.json") in commands
    assert str(output_dir / "beta-responses") in commands


def test_evidence_execution_pack_embeds_runnable_status_handoff_for_quoted_paths(tmp_path: Path) -> None:
    records_dir = tmp_path / "record files"
    records_dir.mkdir()
    host_records, beta_records = _write_empty_records(records_dir)
    output_dir = tmp_path / "evidence session"
    status_path = output_dir / "status.md"
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    _generate_execution_pack(output_dir, host_records=host_records, beta_records=beta_records)

    expected_command = shlex.join(
        [
            "albu-mcp",
            "evidence",
            "execution-pack-status",
            "--input-dir",
            str(output_dir),
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--format",
            "markdown",
            "--output",
            str(status_path),
        ]
    )
    readme = (output_dir / "README.md").read_text(encoding="utf-8")
    commands = (output_dir / "post-session-commands.md").read_text(encoding="utf-8")

    assert "## Operator Status" in readme
    assert f"`{expected_command}`" in readme
    assert f"`{expected_command}`" in commands
    assert not status_path.exists()
    assert commands.index("## Pack Status") < commands.index("## Validate Host Manifests")
    assert commands.index("## Validate Beta Responses") < commands.index("## Import Wizard (No Write)")
    assert commands.index("## Import Wizard (No Write)") < commands.index("## Reviewed Import (Writes Records)")

    command_parts = shlex.split(expected_command)
    result = subprocess.run(  # noqa: S603 - rendered package CLI command with controlled fixture paths.
        [sys.executable, "-m", "albumentationsx_mcp", *command_parts[1:]],
        check=True,
        capture_output=True,
        text=True,
    )
    status_report = status_path.read_text(encoding="utf-8")

    assert result.stdout == f"wrote evidence execution-pack-status to {status_path}\n"
    assert "Status: `needs_real_session_input`" in status_report
    assert "Writes records: `false`" in status_report
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_evidence_execution_pack_can_target_one_host(tmp_path: Path) -> None:
    output_dir = tmp_path / "claude-pack"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack",
            "--host",
            "Claude Code",
            "--date",
            "2026-07-09",
            "--reviewer",
            "Release operator",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == f"wrote evidence execution-pack with 8 artifacts to {output_dir}\n"
    assert (output_dir / "claude-code-evidence-session-manifest.json").exists()
    assert not (output_dir / "codex-evidence-session-manifest.json").exists()

    session_plan = (output_dir / "session-plan.md").read_text(encoding="utf-8")
    assert "Claude Code" in session_plan
    assert "Codex" not in session_plan


def test_evidence_execution_pack_audit_reports_generated_pack_ready_for_session(tmp_path: Path) -> None:
    output_dir = tmp_path / "evidence-execution"
    subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack",
            "--date",
            "2026-07-09",
            "--reviewer",
            "Release operator",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack-audit",
            "--input-dir",
            str(output_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["audit_status"] == "ready_for_real_session"
    assert payload["writes_records"] is False
    assert payload["missing_files"] == []
    assert payload["blocking_reasons"] == []
    assert payload["host_manifest_count"] == 2
    assert payload["beta_draft_count"] == 3
    assert {item["validation_status"] for item in payload["host_manifests"]} == {"template_requires_real_evidence"}
    assert {item["validation_status"] for item in payload["beta_drafts"]} == {"template_requires_participant_evidence"}
    assert "albu-mcp evidence import-wizard" in payload["next_commands"][-1]


def test_evidence_execution_pack_audit_blocks_incomplete_pack(tmp_path: Path) -> None:
    output_dir = tmp_path / "evidence-execution"
    subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack",
            "--date",
            "2026-07-09",
            "--reviewer",
            "Release operator",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    missing = output_dir / "beta-responses/noisy-preview-tuning-beta-response.json"
    missing.unlink()

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack-audit",
            "--input-dir",
            str(output_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["audit_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["missing_files"] == ["beta-responses/noisy-preview-tuning-beta-response.json"]
    assert payload["blocking_reasons"] == ["missing_beta_response:noisy-preview-tuning-beta-response.json"]


def test_evidence_execution_pack_progress_lists_fields_for_unfilled_pack(tmp_path: Path) -> None:
    output_dir = tmp_path / "evidence-execution"
    subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack",
            "--date",
            "2026-07-10",
            "--reviewer",
            "Release operator",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack-progress",
            "--input-dir",
            str(output_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["progress_status"] == "needs_real_session_input"
    assert payload["writes_records"] is False
    assert payload["required_item_count"] == 5
    assert payload["completed_item_count"] == 0
    assert payload["blocking_reasons"] == []
    assert len(payload["host_updates"]) == 2
    assert len(payload["beta_updates"]) == 3
    assert {item["required_fields"][0] for item in payload["host_updates"]} == {"manifest_status"}
    assert {"evidence", "confirm_real_host_observed"}.issubset(payload["host_updates"][0]["required_fields"])
    assert {item["required_fields"][-1] for item in payload["beta_updates"]} == {"summary"}
    assert payload["next_commands"][0].startswith("Open ")
    assert "execution-pack-audit" in payload["next_commands"][-1]


def test_evidence_execution_pack_progress_reports_audit_blockers(tmp_path: Path) -> None:
    output_dir = tmp_path / "evidence-execution"
    subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack",
            "--date",
            "2026-07-10",
            "--reviewer",
            "Release operator",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    (output_dir / "operator-checklist.md").unlink()

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack-progress",
            "--input-dir",
            str(output_dir),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["progress_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["blocking_reasons"] == ["missing_pack_file:operator-checklist.md"]
    assert payload["host_updates"] == []
    assert payload["beta_updates"] == []


def test_evidence_execution_pack_status_summarizes_unfilled_pack(execution_pack: ExecutionPackFixture) -> None:
    output_dir, host_records, beta_records = execution_pack
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = _run_execution_pack_status(
        output_dir=output_dir,
        host_records=host_records,
        beta_records=beta_records,
    )
    payload = json.loads(result.stdout)

    assert payload["status"] == "needs_real_session_input"
    assert payload["writes_records"] is False
    assert payload["audit_status"] == "ready_for_real_session"
    assert payload["progress_status"] == "needs_real_session_input"
    assert payload["import_wizard_status"] == "blocked"
    assert payload["required_item_count"] == 5
    assert payload["completed_item_count"] == 0
    assert payload["pending_host_count"] == 2
    assert payload["pending_beta_count"] == 3
    assert payload["import_ready_command_available"] is False
    assert payload["blocking_reasons"] == []
    assert payload["next_action"] == "fill_real_session_evidence"
    assert 1 <= len(payload["next_commands"]) <= 3
    assert "execution-pack-status" in payload["next_commands"][-1]
    assert payload["audit"]["audit_status"] == "ready_for_real_session"
    assert payload["progress"]["progress_status"] == "needs_real_session_input"
    assert payload["import_wizard"]["wizard_status"] == "blocked"
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_evidence_execution_pack_status_stops_on_audit_blocker(execution_pack: ExecutionPackFixture) -> None:
    output_dir, host_records, beta_records = execution_pack
    (output_dir / "operator-checklist.md").unlink()
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = _run_execution_pack_status(
        output_dir=output_dir,
        host_records=host_records,
        beta_records=beta_records,
    )
    payload = json.loads(result.stdout)

    assert payload["status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["audit_status"] == "blocked"
    assert payload["progress_status"] == "blocked"
    assert payload["import_wizard_status"] == "not_run"
    assert payload["import_ready_command_available"] is False
    assert payload["blocking_reasons"] == ["missing_pack_file:operator-checklist.md"]
    assert payload["next_action"] == "repair_execution_pack"
    assert 1 <= len(payload["next_commands"]) <= 3
    assert payload["import_wizard"] is None
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_evidence_execution_pack_status_reports_ready_inputs(execution_pack: ExecutionPackFixture) -> None:
    output_dir, host_records, beta_records = execution_pack
    _fill_execution_pack(output_dir)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = _run_execution_pack_status(
        output_dir=output_dir,
        host_records=host_records,
        beta_records=beta_records,
    )
    payload = json.loads(result.stdout)

    assert payload["status"] == "ready_for_import_review"
    assert payload["writes_records"] is False
    assert payload["audit_status"] == "ready_for_import_review"
    assert payload["progress_status"] == "ready_for_import_review"
    assert payload["import_wizard_status"] == "ready_to_import"
    assert payload["required_item_count"] == 5
    assert payload["completed_item_count"] == 5
    assert payload["pending_host_count"] == 0
    assert payload["pending_beta_count"] == 0
    assert payload["import_ready_command_available"] is True
    assert payload["blocking_reasons"] == []
    assert payload["next_action"] == "review_and_run_import"
    assert "--import-ready" in payload["next_commands"][0]
    assert len(payload["next_commands"]) <= 3
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_evidence_execution_pack_status_writes_markdown_report(execution_pack: ExecutionPackFixture) -> None:
    output_dir, host_records, beta_records = execution_pack
    report_path = output_dir.parent / "reports" / "execution-pack-status.md"
    _fill_execution_pack(output_dir)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = _run_execution_pack_status(
        output_dir=output_dir,
        host_records=host_records,
        beta_records=beta_records,
        output_format="markdown",
        output=report_path,
    )
    report = report_path.read_text(encoding="utf-8")

    assert result.stdout == f"wrote evidence execution-pack-status to {report_path}\n"
    assert "# Evidence Execution Pack Status" in report
    assert "Status: `ready_for_import_review`" in report
    assert "Writes records: `false`" in report
    assert "Completed: `5/5`" in report
    assert "Import wizard: `ready_to_import`" in report
    assert "Import-ready command available: `true`" in report
    assert "## Blocking Reasons\n\n- none" in report
    assert "## Next Commands" in report
    assert "--import-ready" in report
    assert "## Non-Fabrication Policy" in report
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before


def test_evidence_execution_pack_status_hides_import_command_when_wizard_blocks(
    execution_pack: ExecutionPackFixture,
) -> None:
    output_dir, host_records, beta_records = execution_pack
    _fill_execution_pack(output_dir)
    (output_dir / "beta-responses/unexpected-beta-response.json").write_text("not-json\n", encoding="utf-8")

    result = _run_execution_pack_status(
        output_dir=output_dir,
        host_records=host_records,
        beta_records=beta_records,
    )
    payload = json.loads(result.stdout)

    assert payload["audit_status"] == "ready_for_import_review"
    assert payload["progress_status"] == "ready_for_import_review"
    assert payload["status"] == "blocked"
    assert payload["import_wizard_status"] == "blocked"
    assert payload["import_ready_command_available"] is False
    assert payload["blocking_reasons"] == ["import_wizard:beta_draft_invalid"]
    assert payload["next_action"] == "resolve_import_wizard_blockers"
    assert all("--import-ready" not in command for command in payload["next_commands"])
