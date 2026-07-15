"""FastMCP prompt registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface, ProfileSurface
from albumentationsx_mcp.capabilities import REVIEW_PROFILE_MEMBERSHIP
from albumentationsx_mcp.prompts import (
    build_robustness_augmentation_session as build_robustness_prompt,
)
from albumentationsx_mcp.prompts import (
    compare_preview_runs_for_feedback as compare_preview_runs_prompt,
)
from albumentationsx_mcp.prompts import (
    export_reproducible_pipeline as export_pipeline_prompt,
)
from albumentationsx_mcp.prompts import (
    run_first_preview_review as first_preview_prompt,
)
from albumentationsx_mcp.prompts import (
    tune_pipeline_from_preview_feedback as tune_feedback_prompt,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

_PROMPTS = (
    "build_robustness_augmentation_session",
    "compare_preview_runs_for_feedback",
    "run_first_preview_review",
    "tune_pipeline_from_preview_feedback",
    "export_reproducible_pipeline",
)
SURFACE = AdapterSurface(
    adapter="prompts",
    prompts=_PROMPTS,
    profile_surfaces=(ProfileSurface(profiles=REVIEW_PROFILE_MEMBERSHIP, prompts=_PROMPTS),),
)


def register_prompt_adapter(mcp: FastMCP) -> None:
    """Register the public agent workflow prompts."""

    @mcp.prompt()
    def build_robustness_augmentation_session(task: str, targets: str = "image") -> str:
        """Guide an assistant through preview-driven augmentation tuning."""
        return build_robustness_prompt(task, targets)

    @mcp.prompt()
    def compare_preview_runs_for_feedback(baseline_run_id: str, candidate_run_id: str) -> str:
        """Guide an assistant through preview run comparison before adjustment."""
        return compare_preview_runs_prompt(baseline_run_id, candidate_run_id)

    @mcp.prompt()
    def run_first_preview_review(
        task: str = "classification",
        input_path: str = "/absolute/path/to/images/sample.jpg",
        targets: str = "image",
    ) -> str:
        """Guide an assistant through a first local preview with request validation."""
        return first_preview_prompt(task, input_path, targets)

    @mcp.prompt()
    def tune_pipeline_from_preview_feedback(task: str, run_id: str, feedback_tags: str) -> str:
        """Guide an assistant through structured preview feedback adjustment."""
        return tune_feedback_prompt(task, run_id, feedback_tags)

    @mcp.prompt()
    def export_reproducible_pipeline(run_id: str, output_format: str = "python") -> str:
        """Guide final reproducible pipeline export after preview acceptance."""
        return export_pipeline_prompt(run_id, output_format)
