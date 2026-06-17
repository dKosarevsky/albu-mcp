from typing import Any, cast

from albumentationsx_mcp.server import create_mcp_server


def test_create_mcp_server_registers_fastmcp_instance() -> None:
    server = create_mcp_server()

    assert server.name == "AlbumentationsX MCP"


def test_server_exposes_documented_tool_names() -> None:
    server = create_mcp_server()

    tool_names = set(server._tool_manager._tools)

    assert {
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
        "validate_preview_request",
    }.issubset(tool_names)


def test_server_exposes_agent_workflow_prompts() -> None:
    server = create_mcp_server()

    prompt_names = set(server._prompt_manager._prompts)

    assert {
        "build_robustness_augmentation_session",
        "run_first_preview_review",
        "compare_preview_runs_for_feedback",
        "tune_pipeline_from_preview_feedback",
        "export_reproducible_pipeline",
    }.issubset(prompt_names)


def test_server_exposes_agent_workflow_resources() -> None:
    server = create_mcp_server()

    resources = server._resource_manager._resources
    workflow_catalog = cast("Any", resources["albumentationsx://workflows/catalog"]).fn()
    preview_tuning = cast("Any", resources["albumentationsx://workflows/preview-tuning"]).fn()
    task_profiles = cast("Any", resources["albumentationsx://workflows/task-profiles"]).fn()
    quality_profiles = cast("Any", resources["albumentationsx://quality-profiles"]).fn()
    recipes_catalog = cast("Any", resources["albumentationsx://recipes/catalog"]).fn()
    diagnostics_guide = cast("Any", resources["albumentationsx://diagnostics/guide"]).fn()
    client_smoke_example = cast("Any", resources["albumentationsx://examples/client-smoke"]).fn()
    first_preview_example = cast("Any", resources["albumentationsx://examples/first-preview"]).fn()
    diagnostics_example = cast("Any", resources["albumentationsx://examples/diagnostics"]).fn()
    review_loop_example = cast("Any", resources["albumentationsx://examples/review-loop"]).fn()
    report_handoff_example = cast("Any", resources["albumentationsx://examples/report-handoff"]).fn()
    capabilities = cast("Any", resources["albumentationsx://capabilities"]).fn()

    assert "preview-tuning" in workflow_catalog
    assert "recommend_pipeline" in preview_tuning
    assert "classification-robustness" in task_profiles
    assert "segmentation" in quality_profiles
    assert "object_detection" in recipes_catalog
    assert "diagnose_environment" in diagnostics_guide
    assert "is AlbumentationsX MCP connected?" in client_smoke_example
    assert "run the first AlbumentationsX preview" in first_preview_example
    assert "why does AlbumentationsX MCP preview not work?" in diagnostics_example
    assert "record_preview_feedback" in review_loop_example
    assert "export_preview_report" in report_handoff_example
    assert "adjust_pipeline" in preview_tuning
    assert "workflow_resources" in capabilities
    assert "compare_preview_runs_for_feedback" in capabilities
    assert "run_first_preview_review" in capabilities
    assert "summarize_tuning_session" in capabilities
    assert "rank_preview_candidates" in capabilities
    assert "score_dataset_preview_candidates" in capabilities
    assert "list_quality_profiles" in capabilities
    assert "recommend_recipe" in capabilities
    assert "record_preview_feedback" in capabilities
    assert "list_preview_feedback" in capabilities
    assert "record_tuning_decision" in capabilities
    assert "export_tuning_report" in capabilities
    assert "export_preview_report" in capabilities
    assert "diagnose_environment" in capabilities
    assert "run_host_smoke_check" in capabilities
    assert "validate_preview_request" in capabilities
    assert "albumentationsx://diagnostics/guide" in capabilities
    assert "albumentationsx://recipes/catalog" in capabilities
    assert "albumentationsx://examples/client-smoke" in capabilities
    assert "albumentationsx://examples/first-preview" in capabilities
    assert "albumentationsx://examples/diagnostics" in capabilities
    assert "albumentationsx://examples/review-loop" in capabilities
    assert "albumentationsx://examples/report-handoff" in capabilities
    assert "albumentationsx://workflows/task-profiles" in capabilities
