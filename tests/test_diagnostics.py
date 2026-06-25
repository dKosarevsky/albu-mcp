from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from albumentationsx_mcp.diagnostics import DiagnosticsService, PublicSurface, build_diagnostics_guide


def test_diagnostics_reports_ok_environment(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"

    report = DiagnosticsService(
        allowed_roots=[tmp_path],
        artifact_root=artifact_root,
        max_preview_runs=7,
        public_surface=_complete_public_surface(),
    ).diagnose(include_write_probe=True)

    assert report.status == "ok"
    assert "albumentationsx_import" in {check.code for check in report.checks}
    assert "artifact_root_write_probe" in {check.code for check in report.checks}
    assert {check.severity for check in report.checks} == {"info"}
    assert [action.code for action in report.remediation_actions] == ["proceed_with_preview_smoke"]
    assert report.remediation_actions[0].severity == "info"
    assert report.environment.allowed_roots == [str(tmp_path.resolve())]
    assert report.environment.artifact_root == str(artifact_root.resolve())
    assert report.environment.max_preview_runs == 7
    assert report.environment.write_probe == "passed"
    assert not (artifact_root / ".albumentationsx-mcp-diagnostics-probe").exists()


def test_diagnostics_warns_for_missing_allowed_root(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing-images"

    report = DiagnosticsService(
        allowed_roots=[missing_root],
        artifact_root=tmp_path / "artifacts",
        max_preview_runs=100,
        public_surface=_complete_public_surface(),
    ).diagnose(include_write_probe=False)

    assert report.status == "warning"
    assert "allowed_root_missing" in {check.code for check in report.checks}
    missing_root_check = next(check for check in report.checks if check.code == "allowed_root_missing")
    assert missing_root_check.severity == "medium"
    allowed_root_action = next(action for action in report.remediation_actions if action.code == "fix_allowed_root")
    assert allowed_root_action.severity == "medium"
    assert allowed_root_action.check_codes == ["allowed_root_missing"]
    assert allowed_root_action.command_hint == "--allowed-root /absolute/path/to/images"
    assert allowed_root_action.docs_uri == "albumentationsx://diagnostics/guide"
    assert report.environment.write_probe == "not_run"
    assert any("--allowed-root" in action for action in report.next_actions)
    assert any(str(missing_root.resolve()) in warning for warning in report.warnings)


def test_diagnostics_errors_when_artifact_root_is_a_file(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifact-file"
    artifact_root.write_text("not a directory", encoding="utf-8")

    report = DiagnosticsService(
        allowed_roots=[tmp_path],
        artifact_root=artifact_root,
        max_preview_runs=100,
        public_surface=_complete_public_surface(),
    ).diagnose(include_write_probe=True)

    assert report.status == "error"
    artifact_root_check = next(check for check in report.checks if check.code == "artifact_root_not_directory")
    assert artifact_root_check.severity == "high"
    artifact_root_action = next(action for action in report.remediation_actions if action.code == "fix_artifact_root")
    assert artifact_root_action.severity == "high"
    assert artifact_root_action.check_codes == ["artifact_root_not_directory"]
    assert report.environment.write_probe == "failed"
    assert any("--artifact-root" in action for action in report.next_actions)


def test_diagnostics_reports_missing_public_surface_remediation(tmp_path: Path) -> None:
    public_surface = _complete_public_surface()
    public_surface.tools.remove("diagnose_environment")

    report = DiagnosticsService(
        allowed_roots=[tmp_path],
        artifact_root=tmp_path / "artifacts",
        max_preview_runs=100,
        public_surface=public_surface,
    ).diagnose(include_write_probe=False)

    assert report.status == "error"
    surface_check = next(check for check in report.checks if check.code == "required_tools_available")
    assert surface_check.severity == "high"
    surface_action = next(action for action in report.remediation_actions if action.code == "refresh_host_surface")
    assert surface_action.severity == "high"
    assert surface_action.check_codes == ["required_tools_available"]
    assert surface_action.command_hint is not None
    assert "albumentationsx-mcp" in surface_action.command_hint


def test_diagnostics_guide_is_agent_legible() -> None:
    guide = build_diagnostics_guide()

    assert guide.name == "diagnostics"
    assert guide.trigger_phrase == "why does AlbumentationsX MCP preview not work?"
    assert [step.tool for step in guide.steps] == [
        "albumentationsx://diagnostics/guide",
        "diagnose_environment",
        "albumentationsx://capabilities",
    ]
    assert any("diagnose_environment" in criterion for criterion in guide.success_criteria)


def test_public_surface_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        PublicSurface.model_validate(
            {
                "tools": [],
                "prompts": [],
                "workflow_resources": [],
                "extra": "not allowed",
            }
        )


def _complete_public_surface() -> PublicSurface:
    return PublicSurface(
        tools=[
            "search_transforms",
            "get_transform_schema",
            "validate_pipeline",
            "recommend_pipeline",
            "adjust_pipeline",
            "explain_pipeline",
            "list_feedback_tags",
            "render_preview",
            "render_preview_batch",
            "compare_preview_runs",
            "plan_preview_review",
            "summarize_tuning_session",
            "start_tuning_session",
            "record_tuning_session_step",
            "list_tuning_sessions",
            "export_tuning_session",
            "close_tuning_session",
            "archive_tuning_session",
            "cleanup_tuning_sessions",
            "rank_preview_candidates",
            "score_dataset_preview_candidates",
            "list_quality_profiles",
            "recommend_recipe",
            "record_preview_feedback",
            "list_preview_feedback",
            "record_tuning_decision",
            "list_tuning_decisions",
            "export_tuning_report",
            "export_preview_report",
            "list_preview_runs",
            "get_preview_manifest",
            "delete_preview_run",
            "cleanup_preview_runs",
            "export_pipeline",
            "diagnose_environment",
            "run_host_smoke_check",
            "validate_preview_request",
            "plan_dataset_onboarding",
        ],
        prompts=[
            "build_robustness_augmentation_session",
            "run_first_preview_review",
            "compare_preview_runs_for_feedback",
            "tune_pipeline_from_preview_feedback",
            "export_reproducible_pipeline",
        ],
        workflow_resources=[
            "albumentationsx://workflows/catalog",
            "albumentationsx://workflows/preview-tuning",
            "albumentationsx://workflows/annotation-preview",
            "albumentationsx://workflows/task-profiles",
            "albumentationsx://recipes/catalog",
            "albumentationsx://diagnostics/guide",
            "albumentationsx://examples/client-smoke",
            "albumentationsx://examples/first-preview",
            "albumentationsx://examples/distortion-review",
            "albumentationsx://examples/dataset-onboarding",
            "albumentationsx://examples/diagnostics",
            "albumentationsx://examples/review-loop",
            "albumentationsx://examples/report-handoff",
        ],
    )
