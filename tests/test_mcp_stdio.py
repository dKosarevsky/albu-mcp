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
        "list_preview_runs",
        "get_preview_manifest",
    }.issubset(tool_names)
