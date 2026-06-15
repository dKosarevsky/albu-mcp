from __future__ import annotations

from pathlib import Path

from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.diagnostics import DiagnosticsService, PublicSurface
from albumentationsx_mcp.host_smoke import build_host_smoke_report
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.recipes import recommend_recipe


def test_host_smoke_report_is_preview_ready_when_diagnostics_and_validation_pass(tmp_path: Path) -> None:
    catalog = TransformCatalog()
    pipeline_service = PipelineService(catalog)
    recipe = recommend_recipe("classification", intensity="low", targets=["image"])
    validation = pipeline_service.validate_pipeline(recipe.pipeline)
    diagnostics = DiagnosticsService(
        allowed_roots=[tmp_path],
        artifact_root=tmp_path / "artifacts",
        max_preview_runs=100,
        public_surface=_complete_public_surface_with_host_smoke(),
    ).diagnose(include_write_probe=True)

    report = build_host_smoke_report(diagnostics=diagnostics, recipe=recipe, validation=validation)

    assert report.status == "ok"
    assert report.preview_ready is True
    assert [check.code for check in report.checks] == [
        "diagnostics",
        "recipe_recommendation",
        "pipeline_validation",
        "preview_request_template",
    ]
    assert report.preview_request_template is not None
    assert report.preview_request_template.tool == "render_preview_batch"
    assert report.preview_request_template.request["variants_per_image"] == 1
    assert report.preview_request_template.request["seed"] == 0
    assert report.preview_request_template.request["input_paths"] == [str(tmp_path.resolve() / "example.jpg")]
    assert any("render_preview_batch" in action for action in report.next_actions)


def test_host_smoke_report_blocks_preview_when_diagnostics_warn(tmp_path: Path) -> None:
    catalog = TransformCatalog()
    pipeline_service = PipelineService(catalog)
    recipe = recommend_recipe("classification", intensity="low", targets=["image"])
    validation = pipeline_service.validate_pipeline(recipe.pipeline)
    diagnostics = DiagnosticsService(
        allowed_roots=[tmp_path / "missing"],
        artifact_root=tmp_path / "artifacts",
        max_preview_runs=100,
        public_surface=_complete_public_surface_with_host_smoke(),
    ).diagnose(include_write_probe=False)

    report = build_host_smoke_report(diagnostics=diagnostics, recipe=recipe, validation=validation)

    assert report.status == "warning"
    assert report.preview_ready is False
    assert report.preview_request_template is None
    assert [action.code for action in report.remediation_actions] == ["fix_allowed_root"]
    template_check = next(check for check in report.checks if check.code == "preview_request_template")
    assert template_check.status == "warning"
    assert template_check.severity == "medium"


def _complete_public_surface_with_host_smoke() -> PublicSurface:
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
            "summarize_tuning_session",
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
        ],
        prompts=[
            "build_robustness_augmentation_session",
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
            "albumentationsx://examples/diagnostics",
            "albumentationsx://examples/review-loop",
            "albumentationsx://examples/report-handoff",
        ],
    )
