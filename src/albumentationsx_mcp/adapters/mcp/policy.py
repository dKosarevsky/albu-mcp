"""FastMCP pipeline and policy registration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface
from albumentationsx_mcp.advisor import explain_pipeline
from albumentationsx_mcp.models import ComposeSpec, TargetSpec
from albumentationsx_mcp.policy_assistant import (
    plan_augmentation_policy,
    plan_augmentation_policy_candidates,
    plan_policy_iteration,
)
from albumentationsx_mcp.presets import Intensity, adjust_pipeline, recommend_pipeline

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from albumentationsx_mcp.catalog import TransformCatalog
    from albumentationsx_mcp.pipeline import PipelineService

OutputFormat = Literal["python", "json", "yaml"]

SURFACE = AdapterSurface(
    adapter="policy",
    tools=(
        "validate_pipeline",
        "recommend_pipeline",
        "adjust_pipeline",
        "explain_pipeline",
        "plan_augmentation_policy",
        "plan_augmentation_policy_candidates",
        "plan_policy_iteration",
        "export_pipeline",
    ),
    resources=("albumentationsx://policy-assistant/contract",),
)


def register_policy_adapter(
    mcp: FastMCP,
    *,
    catalog: TransformCatalog,
    pipeline_service: PipelineService,
) -> None:
    """Register pipeline validation, recommendation, adjustment, and policy planning."""

    @mcp.resource("albumentationsx://policy-assistant/contract")
    def policy_assistant_contract_resource() -> str:
        """Return the preview-gated policy assistant safety contract."""
        return json.dumps(
            {
                "acceptance_rule": (
                    "Policy assistant output is a starter candidate; render previews and record feedback "
                    "before accepting or exporting it for training."
                ),
                "follow_up_tools": [
                    "render_preview_batch",
                    "compare_preview_runs",
                    "interpret_preview_feedback",
                    "adjust_pipeline",
                    "record_preview_feedback",
                ],
                "gate_status": "preview_required",
                "primary_tool": "plan_augmentation_policy",
                "v2_tool": "plan_augmentation_policy_candidates",
            },
            sort_keys=True,
        )

    @mcp.tool()
    def validate_pipeline(pipeline: dict[str, Any], target: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate a pipeline spec before previewing or exporting it."""
        spec = ComposeSpec.model_validate(pipeline)
        target_spec = TargetSpec.model_validate(target or {})
        return pipeline_service.validate_pipeline(spec, target_spec).model_dump(mode="json", exclude_none=True)

    @mcp.tool(name="recommend_pipeline")
    def recommend_pipeline_tool(
        task: str,
        intensity: Intensity = "medium",
        targets: list[str] | None = None,
    ) -> dict[str, Any]:
        """Recommend a conservative starter pipeline for a CV task."""
        return recommend_pipeline(task=task, intensity=intensity, targets=targets).model_dump(
            mode="json",
            exclude_none=True,
        )

    @mcp.tool(name="adjust_pipeline")
    def adjust_pipeline_tool(pipeline: dict[str, Any], feedback_tags: list[str]) -> dict[str, Any]:
        """Adjust a pipeline from structured preview feedback tags."""
        spec = ComposeSpec.model_validate(pipeline)
        return adjust_pipeline(spec, feedback_tags).model_dump(mode="json", exclude_none=True)

    @mcp.tool(name="explain_pipeline")
    def explain_pipeline_tool(pipeline: dict[str, Any], target: dict[str, Any] | None = None) -> dict[str, Any]:
        """Explain likely pipeline effects, risks, and useful preview feedback tags."""
        spec = ComposeSpec.model_validate(pipeline)
        target_spec = TargetSpec.model_validate(target or {})
        return explain_pipeline(spec, target_spec, catalog=catalog).model_dump(mode="json", exclude_none=True)

    @mcp.tool(name="plan_augmentation_policy")
    def plan_augmentation_policy_tool(
        task: str,
        objective: str = "robustness",
        intensity: Intensity = "medium",
        targets: list[str] | None = None,
        feedback_tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Plan a preview-gated augmentation policy for a task and objective."""
        return plan_augmentation_policy(
            task=task,
            objective=objective,
            intensity=intensity,
            targets=targets,
            feedback_tags=feedback_tags,
            catalog=catalog,
        ).model_dump(mode="json", exclude_none=True)

    @mcp.tool(name="plan_augmentation_policy_candidates")
    def plan_augmentation_policy_candidates_tool(
        task: str,
        objective: str = "robustness",
        targets: list[str] | None = None,
        feedback_tags: list[str] | None = None,
        candidate_count: int = 3,
    ) -> dict[str, Any]:
        """Plan 3-5 preview-gated augmentation policy candidates for side-by-side review."""
        return plan_augmentation_policy_candidates(
            task=task,
            objective=objective,
            targets=targets,
            feedback_tags=feedback_tags,
            candidate_count=candidate_count,
            catalog=catalog,
        ).model_dump(mode="json", exclude_none=True)

    @mcp.tool(name="plan_policy_iteration")
    def plan_policy_iteration_tool(  # noqa: PLR0913 - mirrors the MCP tool input contract.
        task: str,
        objective: str = "robustness",
        targets: list[str] | None = None,
        feedback_tags: list[str] | None = None,
        rejected_candidate_ids: list[str] | None = None,
        accepted_candidate_id: str | None = None,
        iteration: int = 1,
        candidate_count: int = 3,
    ) -> dict[str, Any]:
        """Plan the next preview-gated policy iteration from concrete review feedback."""
        return plan_policy_iteration(
            task=task,
            objective=objective,
            targets=targets,
            feedback_tags=feedback_tags,
            rejected_candidate_ids=rejected_candidate_ids,
            accepted_candidate_id=accepted_candidate_id,
            iteration=iteration,
            candidate_count=candidate_count,
            catalog=catalog,
        ).model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    def export_pipeline(pipeline: dict[str, Any], output_format: OutputFormat = "python") -> dict[str, Any]:
        """Export a validated pipeline as Python, JSON, or YAML."""
        spec = ComposeSpec.model_validate(pipeline)
        return pipeline_service.export_pipeline(spec, output_format=output_format).model_dump(mode="json")
