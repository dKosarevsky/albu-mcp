from __future__ import annotations

import asyncio
import base64
import sys
from pathlib import Path
from typing import Any

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import BlobResourceContents, TextResourceContents
from mcp.types.version import LATEST_MODERN_VERSION
from PIL import Image

from albumentationsx_mcp.adapters.mcp.registration import surface_for_profile
from albumentationsx_mcp.capabilities import CapabilityProfile


@pytest.mark.parametrize("mode", [LATEST_MODERN_VERSION, "legacy"])
def test_mcp_stdio_lists_documented_tools(tmp_path: Path, mode: str) -> None:
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
        async with Client(stdio_client(params), mode=mode) as client:
            tools = await client.list_tools()
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
        "trace_preview_variant",
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
        "run_first_preview",
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
        async with Client(stdio_client(params), mode="auto") as client:
            tools = await client.list_tools()
            return [tool.name for tool in tools.tools]

    tool_names = asyncio.run(run_client())

    assert tool_names == list(surface_for_profile(CapabilityProfile.CORE).tools)


def test_mcp_stdio_review_profile_executes_preview_resource_flow(tmp_path: Path) -> None:
    image_path = tmp_path / "review.png"
    Image.new("RGB", (24, 24), (96, 128, 160)).save(image_path)

    async def run_client() -> dict[str, Any]:
        async with Client(
            stdio_client(_profile_server_parameters(tmp_path, CapabilityProfile.REVIEW)),
            mode="auto",
        ) as client:
            tools = await client.list_tools()
            example = await client.read_resource("albumentationsx://examples/first-preview")
            smoke = await client.call_tool("run_host_smoke_check", {"include_write_probe": False})
            request = _preview_request(image_path)
            validation = await client.call_tool("validate_preview_request", {"request": request})
            preview = await client.call_tool("render_preview_batch", {"request": request})
            example_content = example.contents[0]
            assert isinstance(example_content, TextResourceContents)
            return {
                "tools": [tool.name for tool in tools.tools],
                "example": example_content.text,
                "smoke": smoke.structured_content,
                "validation": validation.structured_content,
                "preview": preview.structured_content,
                "errors": [smoke.is_error, validation.is_error, preview.is_error],
            }

    result = asyncio.run(run_client())

    assert set(result["tools"]) == set(surface_for_profile(CapabilityProfile.REVIEW).tools)
    assert "render_preview_batch" in result["example"]
    assert result["smoke"]["preview_ready"] is True
    assert result["validation"]["valid"] is True
    assert result["preview"]["run_id"]
    assert result["errors"] == [False, False, False]


def test_mcp_stdio_dataset_profile_executes_guided_preview_trace_resource_flow(tmp_path: Path) -> None:
    image_path = tmp_path / "dataset.png"
    Image.new("RGB", (24, 24), (160, 128, 96)).save(image_path)

    async def run_client() -> dict[str, Any]:
        async with Client(
            stdio_client(_profile_server_parameters(tmp_path, CapabilityProfile.DATASET)),
            mode="auto",
        ) as client:
            tools = await client.list_tools()
            guided = await client.call_tool(
                "run_first_preview",
                {"dataset_path": str(image_path), "intensity": "high", "max_images": 1},
            )
            assert guided.structured_content is not None
            preview = guided.structured_content["preview"]
            trace = await client.call_tool(
                "trace_preview_variant",
                {
                    "run_id": preview["run_id"],
                    "image_index": 0,
                    "variant_index": 0,
                },
            )
            contact_sheet = await client.read_resource(guided.structured_content["contact_sheet"]["uri"])
            contact_sheet_content = contact_sheet.contents[0]
            assert isinstance(contact_sheet_content, BlobResourceContents)
            return {
                "tools": [tool.name for tool in tools.tools],
                "guided": guided.structured_content,
                "trace": trace.structured_content,
                "contact_sheet_mime_type": contact_sheet_content.mime_type,
                "contact_sheet_blob": contact_sheet_content.blob,
                "errors": [guided.is_error, trace.is_error],
            }

    result = asyncio.run(run_client())

    assert set(result["tools"]) == set(surface_for_profile(CapabilityProfile.DATASET).tools)
    assert result["guided"]["status"] == "rendered"
    assert result["guided"]["trace_available"] is True
    assert result["trace"]["available"] is True
    assert result["trace"]["trace"]["applied_transforms"]
    assert result["contact_sheet_mime_type"] == "image/png"
    assert base64.b64decode(result["contact_sheet_blob"]).startswith(b"\x89PNG\r\n\x1a\n")
    assert result["errors"] == [False, False]


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
