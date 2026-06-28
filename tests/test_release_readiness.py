import json
import subprocess
import sys
from pathlib import Path

from scripts.check_release_readiness import ReleaseReadinessConfig, check_release_readiness


def test_release_readiness_accepts_current_fast_guards(tmp_path: Path) -> None:
    report = check_release_readiness(ReleaseReadinessConfig(contract_output_work_dir=tmp_path))

    assert report.ok is True
    assert [check.name for check in report.checks] == [
        "manual_host_records",
        "host_acceptance_evidence",
        "first_10_minutes",
        "host_proof_sprint",
        "p0_host_run_preflight",
        "v1_decision_report",
        "v1_evidence_operator_packet",
        "v1_growth_cutover_report",
        "v1_stabilization_plan",
        "v1_rc_readiness_report",
        "p0_host_runbook",
        "p0_host_run_session",
        "p0_evidence_recorder",
        "p0_evidence_import_guide",
        "p0_evidence_regeneration_pack",
        "p0_host_execution_sprint",
        "p0_host_evidence_ledger",
        "p0_evidence_status",
        "p0_blocker_triage",
        "p0_host_unblock_pack",
        "host_evidence_runner",
        "codex_cancellation_triage",
        "claude_code_setup_path",
        "beta_campaign_pack",
        "beta_campaign_execution",
        "beta_feedback_intake",
        "beta_feedback_status",
        "beta_validation_sprint",
        "beta_validation_status",
        "v1_rc_release_packet",
        "v1_rc_cutover_checklist",
        "v1_rc_automation_pack",
        "v1_rc_rehearsal_plan",
        "v1_rc_cutover_gate",
        "rc_cutover_recovery_plan",
        "rc_host_evidence_ops",
        "product_depth_backlog",
        "product_depth_gate",
        "product_depth_selection",
        "host_onboarding_depth_plan",
        "review_agent_v3_plan",
        "dataset_quality_depth_plan",
        "distribution_readiness_pack",
        "distribution_rollout_packet",
        "mcp_contract_snapshot",
        "output_contract_snapshot",
    ]
    assert all(check.message for check in report.checks)
    assert all(not check.diff for check in report.checks)


def test_release_readiness_runs_optional_version_check(tmp_path: Path) -> None:
    report = check_release_readiness(ReleaseReadinessConfig(tag="v1.15.0", contract_output_work_dir=tmp_path))

    assert report.ok is True
    assert report.checks[-1].name == "release_version"
    assert report.checks[-1].message == "release version 1.15.0 is consistent"


def test_release_readiness_reports_version_mismatch(tmp_path: Path) -> None:
    report = check_release_readiness(ReleaseReadinessConfig(tag="v0.0.0", contract_output_work_dir=tmp_path))

    failed = [check for check in report.checks if not check.ok]
    assert report.ok is False
    assert len(failed) == 1
    assert failed[0].name == "release_version"
    assert "does not match tag version '0.0.0'" in failed[0].message


def test_release_readiness_cli_passes_fast_guards(tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/check_release_readiness.py",
            "--contract-output-work-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "release readiness checks passed" in result.stdout
    assert "manual_host_records" in result.stdout
    assert "p0_host_run_preflight" in result.stdout
    assert "v1_decision_report" in result.stdout
    assert "v1_evidence_operator_packet" in result.stdout
    assert "v1_growth_cutover_report" in result.stdout
    assert "v1_stabilization_plan" in result.stdout
    assert "v1_rc_readiness_report" in result.stdout
    assert "p0_host_run_session" in result.stdout
    assert "p0_evidence_import_guide" in result.stdout
    assert "p0_evidence_regeneration_pack" in result.stdout
    assert "p0_evidence_status" in result.stdout
    assert "p0_host_unblock_pack" in result.stdout
    assert "host_evidence_runner" in result.stdout
    assert "codex_cancellation_triage" in result.stdout
    assert "claude_code_setup_path" in result.stdout
    assert "beta_campaign_pack" in result.stdout
    assert "beta_campaign_execution" in result.stdout
    assert "beta_feedback_intake" in result.stdout
    assert "beta_validation_status" in result.stdout
    assert "v1_rc_release_packet" in result.stdout
    assert "v1_rc_cutover_checklist" in result.stdout
    assert "v1_rc_automation_pack" in result.stdout
    assert "v1_rc_rehearsal_plan" in result.stdout
    assert "v1_rc_cutover_gate" in result.stdout
    assert "rc_cutover_recovery_plan" in result.stdout
    assert "rc_host_evidence_ops" in result.stdout
    assert "product_depth_backlog" in result.stdout
    assert "product_depth_gate" in result.stdout
    assert "product_depth_selection" in result.stdout
    assert "host_onboarding_depth_plan" in result.stdout
    assert "dataset_quality_depth_plan" in result.stdout
    assert "distribution_readiness_pack" in result.stdout
    assert "distribution_rollout_packet" in result.stdout
    assert "output_contract_snapshot" in result.stdout


def test_release_readiness_reports_stale_generated_doc(tmp_path: Path) -> None:
    stale_path = tmp_path / "BETA_FEEDBACK_INTAKE.md"
    stale_path.write_text("# stale\n", encoding="utf-8")

    report = check_release_readiness(
        ReleaseReadinessConfig(contract_output_work_dir=tmp_path, beta_feedback_intake_path=stale_path)
    )

    failed = [check for check in report.checks if not check.ok]
    assert report.ok is False
    assert len(failed) == 1
    assert failed[0].name == "beta_feedback_intake"
    assert "is stale; regenerate it with scripts/export_beta_feedback_intake.py" in failed[0].message


def test_release_readiness_cli_prints_failed_check(tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/check_release_readiness.py",
            "--tag",
            "v0.0.0",
            "--contract-output-work-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "[release_version]" in result.stderr
    assert "does not match tag version '0.0.0'" in result.stderr


def test_release_readiness_cli_can_emit_json(tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/check_release_readiness.py",
            "--format",
            "json",
            "--contract-output-work-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["ok"] is True
    assert payload["checks"][0]["name"] == "manual_host_records"
    assert payload["checks"][0]["ok"] is True


def test_release_readiness_cli_writes_github_step_summary(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.md"
    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/check_release_readiness.py",
            "--contract-output-work-dir",
            str(tmp_path / "contracts"),
        ],
        check=True,
        capture_output=True,
        env={"GITHUB_STEP_SUMMARY": str(summary_path)},
        text=True,
    )

    summary = summary_path.read_text(encoding="utf-8")

    assert "release readiness checks passed" in result.stdout
    assert "## Release Readiness" in summary
    assert "| Check | Status | Message |" in summary
    assert "| manual_host_records | passed |" in summary
