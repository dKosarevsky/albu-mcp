from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from albumentationsx_mcp.policy_assistant import plan_augmentation_policy


def test_policy_assistant_returns_preview_gated_plan() -> None:
    plan = plan_augmentation_policy(
        task="segmentation",
        objective="robustness",
        intensity="medium",
        targets=["image", "mask"],
    )

    assert plan.gate_status == "preview_required"
    assert plan.recommended_next_tool == "render_preview_batch"
    assert "render_preview_batch" in plan.next_tools
    assert "compare_preview_runs" in plan.next_tools
    assert plan.pipeline.seed == 137
    assert any(transform.name == "GaussNoise" for transform in plan.pipeline.transforms)
    assert any("mask" in item.lower() or "annotation" in item.lower() for item in plan.review_checklist)
    assert plan.gate_reason.startswith("Policy recommendations are starter candidates")


def test_policy_assistant_feedback_softens_destructive_policy() -> None:
    base = plan_augmentation_policy(
        task="classification",
        objective="robustness",
        intensity="high",
        targets=["image"],
    )
    softened = plan_augmentation_policy(
        task="classification",
        objective="robustness",
        intensity="high",
        targets=["image"],
        feedback_tags=["too_noisy:high", "object_unrecognizable"],
    )

    base_noise = next(transform for transform in base.pipeline.transforms if transform.name == "GaussNoise")
    softened_noise = next(transform for transform in softened.pipeline.transforms if transform.name == "GaussNoise")

    assert softened.applied_feedback_tags == ["object_unrecognizable", "too_noisy:high"]
    assert softened_noise.p is not None
    assert base_noise.p is not None
    assert softened_noise.p < base_noise.p
    assert softened.recommended_next_tool == "render_preview_batch"


def test_mcp_server_lists_policy_assistant_tool(tmp_path: Path) -> None:
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

    assert "plan_augmentation_policy" in tool_names
