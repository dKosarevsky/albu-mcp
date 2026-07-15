"""FastMCP dataset onboarding and quality registration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface, ProfileSurface
from albumentationsx_mcp.capabilities import DATASET_PROFILE_MEMBERSHIP, REVIEW_DATASET_PROFILE_MEMBERSHIP
from albumentationsx_mcp.dataset import score_dataset_preview_candidates as score_dataset_candidates
from albumentationsx_mcp.dataset_quality import inspect_dataset_quality
from albumentationsx_mcp.models import QualityProfileName
from albumentationsx_mcp.onboarding import build_dataset_onboarding_report
from albumentationsx_mcp.presets import Intensity
from albumentationsx_mcp.recipes import recommend_recipe
from albumentationsx_mcp.review_packet import build_review_packet

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from albumentationsx_mcp.pipeline import PipelineService
    from albumentationsx_mcp.preview import PathPolicy, PreviewService

_TOOLS = (
    "plan_dataset_onboarding",
    "build_review_packet",
    "inspect_dataset_quality",
    "score_dataset_preview_candidates",
)
_DATASET_ONLY_TOOLS = _TOOLS[:-1]
_SHARED_SCORING_TOOLS = _TOOLS[-1:]
SURFACE = AdapterSurface(
    adapter="dataset",
    tools=_TOOLS,
    profile_surfaces=(
        ProfileSurface(profiles=DATASET_PROFILE_MEMBERSHIP, tools=_DATASET_ONLY_TOOLS),
        ProfileSurface(profiles=REVIEW_DATASET_PROFILE_MEMBERSHIP, tools=_SHARED_SCORING_TOOLS),
    ),
)


def register_dataset_adapter(
    mcp: FastMCP,
    *,
    path_policy: PathPolicy,
    pipeline_service: PipelineService,
    preview_service: PreviewService,
    available_tools: set[str] | None = None,
) -> None:
    """Register bounded dataset onboarding, review, quality, and scoring tools."""

    @mcp.tool(name="plan_dataset_onboarding")
    def plan_dataset_onboarding_tool(
        dataset_path: str,
        task: str = "classification",
        intensity: Intensity = "low",
        targets: list[str] | None = None,
        max_images: int = 8,
    ) -> dict[str, Any]:
        """Plan the first safe preview for one local image or an image directory."""
        return build_dataset_onboarding_report(
            dataset_path=Path(dataset_path),
            task=task,
            intensity=intensity,
            targets=targets,
            max_images=max_images,
            path_policy=path_policy,
            pipeline_service=pipeline_service,
            recipe_builder=lambda **kwargs: recommend_recipe(**kwargs, available_tools=available_tools),
        ).model_dump(mode="json", exclude_none=True)

    @mcp.tool(name="build_review_packet")
    def build_review_packet_tool(
        dataset_path: str,
        task: str = "classification",
        intensity: Intensity = "low",
        targets: list[str] | None = None,
        max_images: int = 8,
    ) -> dict[str, Any]:
        """Build one host-facing first-preview handoff for one image or an image directory."""
        return build_review_packet(
            dataset_path=Path(dataset_path),
            task=task,
            intensity=intensity,
            targets=targets,
            max_images=max_images,
            path_policy=path_policy,
            pipeline_service=pipeline_service,
            recipe_builder=lambda **kwargs: recommend_recipe(**kwargs, available_tools=available_tools),
        ).model_dump(mode="json", exclude_none=True)

    @mcp.tool(name="inspect_dataset_quality")
    def inspect_dataset_quality_tool(dataset_path: str, max_images: int = 8) -> dict[str, Any]:
        """Inspect local dataset image quality before first preview rendering."""
        return inspect_dataset_quality(
            dataset_path=Path(dataset_path),
            max_images=max_images,
            path_policy=path_policy,
        ).model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    def score_dataset_preview_candidates(
        baseline_run_id: str,
        candidate_run_ids: list[str],
        feedback_tags_by_candidate: dict[str, list[str]] | None = None,
        accepted_candidate_ids: list[str] | None = None,
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Score several preview candidates as one dataset-level decision set."""
        if not candidate_run_ids:
            msg = "candidate_run_ids must contain at least one run id"
            raise ValueError(msg)
        comparisons = [
            preview_service.compare_preview_runs(
                baseline_run_id,
                candidate_run_id,
                quality_profile=quality_profile,
            )
            for candidate_run_id in candidate_run_ids[:20]
        ]
        return score_dataset_candidates(
            comparisons,
            feedback_tags_by_candidate=feedback_tags_by_candidate or {},
            accepted_candidate_ids=set(accepted_candidate_ids or []),
            quality_profile=quality_profile,
        ).model_dump(mode="json")
