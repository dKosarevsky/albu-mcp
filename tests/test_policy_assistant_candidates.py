from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from albumentationsx_mcp.policy_assistant import plan_augmentation_policy_candidates


def test_policy_assistant_v2_returns_ranked_preview_gated_candidates() -> None:
    result = plan_augmentation_policy_candidates(
        task="segmentation",
        objective="robustness",
        targets=["image", "mask"],
        candidate_count=4,
    )

    assert result.gate_status == "preview_required"
    assert result.recommended_next_tool == "render_preview_batch"
    assert result.candidate_count == 4
    assert [candidate.rank for candidate in result.candidates] == [1, 2, 3, 4]
    assert len({candidate.candidate_id for candidate in result.candidates}) == 4
    assert {"low", "medium", "high"}.issubset({candidate.plan.intensity for candidate in result.candidates})
    assert all(candidate.tradeoff for candidate in result.candidates)
    assert all(candidate.preview_request_hint["variants_per_image"] == 4 for candidate in result.candidates)
    assert all(candidate.plan.gate_status == "preview_required" for candidate in result.candidates)


def test_policy_assistant_v2_preserves_feedback_in_candidates() -> None:
    result = plan_augmentation_policy_candidates(
        task="classification",
        objective="robustness",
        targets=["image"],
        feedback_tags=["too_noisy:high"],
        candidate_count=3,
    )

    assert result.applied_feedback_tags == ["too_noisy:high"]
    assert all(candidate.plan.applied_feedback_tags == ["too_noisy:high"] for candidate in result.candidates)
    assert any("feedback" in candidate.tradeoff.lower() for candidate in result.candidates)


def test_mcp_server_lists_policy_assistant_candidates_tool(tmp_path: Path) -> None:
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

    assert "plan_augmentation_policy_candidates" in tool_names
