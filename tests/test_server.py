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
        "list_preview_runs",
        "get_preview_manifest",
        "delete_preview_run",
        "cleanup_preview_runs",
        "export_pipeline",
    }.issubset(tool_names)


def test_server_exposes_agent_workflow_prompts() -> None:
    server = create_mcp_server()

    prompt_names = set(server._prompt_manager._prompts)

    assert {
        "build_robustness_augmentation_session",
        "compare_preview_runs_for_feedback",
        "tune_pipeline_from_preview_feedback",
        "export_reproducible_pipeline",
    }.issubset(prompt_names)


def test_server_exposes_agent_workflow_resources() -> None:
    server = create_mcp_server()

    resources = server._resource_manager._resources
    workflow_catalog = cast("Any", resources["albumentationsx://workflows/catalog"]).fn()
    preview_tuning = cast("Any", resources["albumentationsx://workflows/preview-tuning"]).fn()
    capabilities = cast("Any", resources["albumentationsx://capabilities"]).fn()

    assert "preview-tuning" in workflow_catalog
    assert "recommend_pipeline" in preview_tuning
    assert "adjust_pipeline" in preview_tuning
    assert "workflow_resources" in capabilities
    assert "compare_preview_runs_for_feedback" in capabilities
    assert "summarize_tuning_session" in capabilities
