from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_mcp_stdio_lists_documented_tools(tmp_path: Path) -> None:
    async def run_client() -> list[str]:
        params = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "albumentationsx_mcp",
                "--allowed-root",
                str(tmp_path),
                "--artifact-root",
                str(tmp_path / "artifacts"),
            ],
            cwd=str(Path.cwd()),
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [tool.name for tool in tools.tools]

    tool_names = asyncio.run(run_client())

    assert {
        "search_transforms",
        "get_transform_schema",
        "validate_pipeline",
        "recommend_pipeline",
        "adjust_pipeline",
        "explain_pipeline",
        "list_feedback_tags",
        "export_pipeline",
        "render_preview",
        "render_preview_batch",
        "compare_preview_runs",
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
        "diagnose_environment",
        "run_host_smoke_check",
        "validate_preview_request",
        "plan_dataset_onboarding",
        "build_review_packet",
        "inspect_dataset_quality",
    }.issubset(tool_names)
