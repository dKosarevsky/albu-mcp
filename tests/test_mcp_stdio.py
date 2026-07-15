from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextResourceContents
from PIL import Image
from pydantic import AnyUrl

from albumentationsx_mcp.adapters.mcp.registration import surface_for_profile
from albumentationsx_mcp.capabilities import CapabilityProfile


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
        "interpret_preview_feedback",
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
        "diagnose_environment",
        "run_host_smoke_check",
        "validate_preview_request",
        "plan_dataset_onboarding",
        "build_review_packet",
        "inspect_dataset_quality",
    }.issubset(tool_names)


def test_mcp_stdio_core_profile_lists_only_core_tools(tmp_path: Path) -> None:
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
                "--capability-profile",
                "core",
            ],
            cwd=str(Path.cwd()),
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [tool.name for tool in tools.tools]

    tool_names = asyncio.run(run_client())

    assert tool_names == list(surface_for_profile(CapabilityProfile.CORE).tools)


def test_mcp_stdio_review_profile_executes_preview_resource_flow(tmp_path: Path) -> None:
    image_path = tmp_path / "review.png"
    Image.new("RGB", (24, 24), (96, 128, 160)).save(image_path)

    async def run_client() -> dict[str, Any]:
        async with (
            stdio_client(_profile_server_parameters(tmp_path, CapabilityProfile.REVIEW)) as (
                read,
                write,
            ),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            example = await session.read_resource(AnyUrl("albumentationsx://examples/first-preview"))
            smoke = await session.call_tool("run_host_smoke_check", {"include_write_probe": False})
            request = _preview_request(image_path)
            validation = await session.call_tool("validate_preview_request", {"request": request})
            preview = await session.call_tool("render_preview_batch", {"request": request})
            example_content = example.contents[0]
            assert isinstance(example_content, TextResourceContents)
            return {
                "tools": [tool.name for tool in tools.tools],
                "example": example_content.text,
                "smoke": smoke.structuredContent,
                "validation": validation.structuredContent,
                "preview": preview.structuredContent,
                "errors": [smoke.isError, validation.isError, preview.isError],
            }

    result = asyncio.run(run_client())

    assert result["tools"] == list(surface_for_profile(CapabilityProfile.REVIEW).tools)
    assert "render_preview_batch" in result["example"]
    assert result["smoke"]["preview_ready"] is True
    assert result["validation"]["valid"] is True
    assert result["preview"]["run_id"]
    assert result["errors"] == [False, False, False]


def test_mcp_stdio_dataset_profile_executes_onboarding_preview_flow(tmp_path: Path) -> None:
    image_path = tmp_path / "dataset.png"
    Image.new("RGB", (24, 24), (160, 128, 96)).save(image_path)

    async def run_client() -> dict[str, Any]:
        async with (
            stdio_client(_profile_server_parameters(tmp_path, CapabilityProfile.DATASET)) as (
                read,
                write,
            ),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            example = await session.read_resource(AnyUrl("albumentationsx://examples/dataset-onboarding"))
            onboarding = await session.call_tool(
                "plan_dataset_onboarding",
                {"dataset_path": str(image_path), "max_images": 1},
            )
            assert onboarding.structuredContent is not None
            request = onboarding.structuredContent["preview_request_template"]["request"]
            validation = await session.call_tool("validate_preview_request", {"request": request})
            preview = await session.call_tool("render_preview_batch", {"request": request})
            example_content = example.contents[0]
            assert isinstance(example_content, TextResourceContents)
            return {
                "tools": [tool.name for tool in tools.tools],
                "example": example_content.text,
                "onboarding": onboarding.structuredContent,
                "validation": validation.structuredContent,
                "preview": preview.structuredContent,
                "errors": [onboarding.isError, validation.isError, preview.isError],
            }

    result = asyncio.run(run_client())

    assert result["tools"] == list(surface_for_profile(CapabilityProfile.DATASET).tools)
    assert "plan_dataset_onboarding" in result["example"]
    assert result["onboarding"]["preview_ready"] is True
    assert result["validation"]["valid"] is True
    assert result["preview"]["run_id"]
    assert result["errors"] == [False, False, False]


def _profile_server_parameters(tmp_path: Path, profile: CapabilityProfile) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "albumentationsx_mcp",
            "--allowed-root",
            str(tmp_path),
            "--artifact-root",
            str(tmp_path / "artifacts"),
            "--capability-profile",
            profile.value,
        ],
        cwd=str(Path.cwd()),
    )


def _preview_request(image_path: Path) -> dict[str, Any]:
    return {
        "input_paths": [str(image_path)],
        "pipeline": {"transforms": [{"name": "HorizontalFlip", "params": {}, "p": 1.0}]},
        "variants_per_image": 1,
        "seed": 7,
    }
