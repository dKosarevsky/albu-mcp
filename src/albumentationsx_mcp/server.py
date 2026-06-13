"""FastMCP server registration for AlbumentationsX."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from albumentationsx_mcp.advisor import explain_pipeline, list_feedback_tags
from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.models import ComposeSpec, PreviewRequest, QualityProfileName, TargetSpec
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.presets import Intensity, adjust_pipeline, recommend_pipeline
from albumentationsx_mcp.preview import ArtifactStore, PathPolicy, PreviewService
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
    tune_pipeline_from_preview_feedback as tune_feedback_prompt,
)
from albumentationsx_mcp.quality import list_quality_profiles
from albumentationsx_mcp.ranking import rank_preview_candidates as rank_candidates
from albumentationsx_mcp.tuning import TuningDecisionStore, build_tuning_session_summary
from albumentationsx_mcp.workflows import get_agent_workflow, list_agent_workflows, list_task_profiles


class ServerSettings(BaseModel):
    """Runtime settings for local preview and artifact access."""

    allowed_roots: list[Path] = Field(default_factory=lambda: [Path.cwd()])
    artifact_root: Path = Field(default_factory=lambda: Path.cwd() / "artifacts")
    max_preview_runs: int = Field(default=100, ge=1)


def settings_from_environment() -> ServerSettings:
    """Create settings from environment variables."""
    allowed = os.getenv("ALBU_MCP_ALLOWED_ROOTS")
    artifact_root = os.getenv("ALBU_MCP_ARTIFACT_ROOT")
    max_preview_runs = os.getenv("ALBU_MCP_MAX_PREVIEW_RUNS")
    return ServerSettings(
        allowed_roots=[Path(item) for item in allowed.split(os.pathsep)] if allowed else [Path.cwd()],
        artifact_root=Path(artifact_root) if artifact_root else Path.cwd() / "artifacts",
        max_preview_runs=int(max_preview_runs) if max_preview_runs else 100,
    )


OutputFormat = Literal["python", "json", "yaml"]


def create_mcp_server(settings: ServerSettings | None = None) -> FastMCP:  # noqa: PLR0915
    """Create and register the AlbumentationsX FastMCP server."""
    settings = settings or settings_from_environment()
    catalog = TransformCatalog()
    pipeline_service = PipelineService(catalog)
    preview_service = PreviewService(
        pipeline_service,
        PathPolicy(settings.allowed_roots),
        ArtifactStore(settings.artifact_root, max_runs=settings.max_preview_runs),
    )
    tuning_store = TuningDecisionStore(settings.artifact_root)
    mcp = FastMCP("AlbumentationsX MCP")

    @mcp.resource("albumentationsx://transforms/catalog")
    def transforms_catalog() -> str:
        """Return the transform catalog as compact JSON."""
        data = [item.model_dump(mode="json", exclude_none=True) for item in catalog.list_transforms()]
        return json.dumps(data, sort_keys=True)

    @mcp.resource("albumentationsx://transforms/{name}")
    def transform_resource(name: str) -> str:
        """Return metadata for one AlbumentationsX transform."""
        return catalog.get_transform_schema(name).model_dump_json(exclude_none=True)

    @mcp.resource("albumentationsx://schemas/pipeline")
    def pipeline_schema() -> str:
        """Return the JSON schema for pipeline specs."""
        return json.dumps(ComposeSpec.model_json_schema(), sort_keys=True)

    @mcp.resource("albumentationsx://feedback-tags")
    def feedback_tags_resource() -> str:
        """Return structured feedback tags accepted by adjustment tools."""
        data = [tag.model_dump(mode="json") for tag in list_feedback_tags()]
        return json.dumps(data, sort_keys=True)

    @mcp.resource("albumentationsx://quality-profiles")
    def quality_profiles_resource() -> str:
        """Return task-aware quality profiles accepted by comparison tools."""
        data = [profile.model_dump(mode="json") for profile in list_quality_profiles()]
        return json.dumps(data, sort_keys=True)

    @mcp.resource("albumentationsx://capabilities")
    def capabilities_resource() -> str:
        """Return operational limits and safety boundaries for this MCP server."""
        return json.dumps(
            {
                "allowed_roots": [str(path.resolve()) for path in settings.allowed_roots],
                "artifact_root": str(settings.artifact_root.resolve()),
                "preview_limits": {
                    "max_input_paths": 32,
                    "max_variants_per_image": 16,
                    "max_side": 4096,
                    "max_preview_runs": settings.max_preview_runs,
                },
                "tools": [
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
                    "rank_preview_candidates",
                    "list_quality_profiles",
                    "record_tuning_decision",
                    "list_tuning_decisions",
                    "list_preview_runs",
                    "get_preview_manifest",
                    "delete_preview_run",
                    "cleanup_preview_runs",
                    "export_pipeline",
                ],
                "prompts": [
                    "build_robustness_augmentation_session",
                    "compare_preview_runs_for_feedback",
                    "tune_pipeline_from_preview_feedback",
                    "export_reproducible_pipeline",
                ],
                "workflow_resources": [
                    "albumentationsx://workflows/catalog",
                    "albumentationsx://workflows/preview-tuning",
                    "albumentationsx://workflows/annotation-preview",
                    "albumentationsx://workflows/task-profiles",
                ],
            },
            sort_keys=True,
        )

    @mcp.resource("albumentationsx://workflows/catalog")
    def workflows_catalog() -> str:
        """Return built-in agent workflow guides as compact JSON."""
        data = [workflow.model_dump(mode="json") for workflow in list_agent_workflows()]
        return json.dumps(data, sort_keys=True)

    @mcp.resource("albumentationsx://workflows/task-profiles")
    def task_profiles_resource() -> str:
        """Return task-specific workflow profiles as compact JSON."""
        data = [profile.model_dump(mode="json") for profile in list_task_profiles()]
        return json.dumps(data, sort_keys=True)

    @mcp.resource("albumentationsx://workflows/preview-tuning")
    def preview_tuning_workflow() -> str:
        """Return the preview-driven augmentation tuning workflow guide."""
        return get_agent_workflow("preview-tuning").model_dump_json()

    @mcp.resource("albumentationsx://workflows/annotation-preview")
    def annotation_preview_workflow() -> str:
        """Return the annotation-aware preview workflow guide."""
        return get_agent_workflow("annotation-preview").model_dump_json()

    @mcp.tool()
    def search_transforms(
        query: str = "",
        targets: list[str] | None = None,
        transform_type: str | None = None,
        bbox_type: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search AlbumentationsX transform metadata."""
        results = catalog.search_transforms(
            query,
            targets=targets,
            transform_type=transform_type,
            bbox_type=bbox_type,
            limit=limit,
        )
        return {"results": [result.model_dump(mode="json", exclude_none=True) for result in results]}

    @mcp.tool()
    def get_transform_schema(name: str) -> dict[str, Any]:
        """Get parameter schema, target support, and summary for one transform."""
        return catalog.get_transform_schema(name).model_dump(mode="json", exclude_none=True)

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

    @mcp.tool(name="list_feedback_tags")
    def list_feedback_tags_tool() -> dict[str, Any]:
        """List structured feedback tags accepted by adjust_pipeline."""
        return {"tags": [tag.model_dump(mode="json") for tag in list_feedback_tags()]}

    @mcp.tool(name="list_quality_profiles")
    def list_quality_profiles_tool() -> dict[str, Any]:
        """List task-aware quality profiles accepted by preview comparison tools."""
        return {"profiles": [profile.model_dump(mode="json") for profile in list_quality_profiles()]}

    @mcp.tool()
    def export_pipeline(pipeline: dict[str, Any], output_format: OutputFormat = "python") -> dict[str, Any]:
        """Export a validated pipeline as Python, JSON, or YAML."""
        spec = ComposeSpec.model_validate(pipeline)
        return pipeline_service.export_pipeline(spec, output_format=output_format).model_dump(mode="json")

    @mcp.tool()
    def render_preview(request: dict[str, Any]) -> dict[str, Any]:
        """Render deterministic preview artifacts for local input images."""
        preview_request = PreviewRequest.model_validate(request)
        return preview_service.render_preview(preview_request).model_dump(mode="json")

    @mcp.tool()
    def render_preview_batch(request: dict[str, Any]) -> dict[str, Any]:
        """Render deterministic batch preview artifacts and contact sheets for local input images."""
        preview_request = PreviewRequest.model_validate(request)
        return preview_service.render_preview(preview_request).model_dump(mode="json")

    @mcp.tool()
    def compare_preview_runs(
        baseline_run_id: str,
        candidate_run_id: str,
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Compare two preview manifests to guide structured feedback and reproducible tuning."""
        return preview_service.compare_preview_runs(
            baseline_run_id,
            candidate_run_id,
            quality_profile=quality_profile,
        ).model_dump(mode="json")

    @mcp.tool()
    def summarize_tuning_session(
        baseline_run_id: str,
        candidate_run_id: str,
        feedback_tags: list[str] | None = None,
        accepted: bool = False,  # noqa: FBT001, FBT002
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Summarize a baseline-to-candidate preview tuning step."""
        comparison = preview_service.compare_preview_runs(
            baseline_run_id,
            candidate_run_id,
            quality_profile=quality_profile,
        )
        return build_tuning_session_summary(
            comparison,
            feedback_tags=feedback_tags or [],
            accepted=accepted,
        ).model_dump(mode="json")

    @mcp.tool()
    def rank_preview_candidates(
        baseline_run_id: str,
        candidate_run_ids: list[str],
        feedback_tags_by_candidate: dict[str, list[str]] | None = None,
        accepted_candidate_ids: list[str] | None = None,
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Rank multiple candidate preview runs against one baseline."""
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
        return rank_candidates(
            comparisons,
            feedback_tags_by_candidate=feedback_tags_by_candidate or {},
            accepted_candidate_ids=set(accepted_candidate_ids or []),
            quality_profile=quality_profile,
        ).model_dump(mode="json")

    @mcp.tool()
    def record_tuning_decision(  # noqa: PLR0913
        baseline_run_id: str,
        candidate_run_id: str,
        feedback_tags: list[str] | None = None,
        accepted: bool = False,  # noqa: FBT001, FBT002
        reviewer_notes: list[str] | None = None,
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Persist a local tuning decision for one preview comparison."""
        comparison = preview_service.compare_preview_runs(
            baseline_run_id,
            candidate_run_id,
            quality_profile=quality_profile,
        )
        summary = build_tuning_session_summary(
            comparison,
            feedback_tags=feedback_tags or [],
            accepted=accepted,
        )
        return tuning_store.record_decision(summary, reviewer_notes).model_dump(mode="json")

    @mcp.tool()
    def list_tuning_decisions(
        limit: int = 20,
        accepted_only: bool = False,  # noqa: FBT001, FBT002
        ranked: bool = False,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """List persisted local tuning decisions."""
        return tuning_store.list_decisions(limit=limit, accepted_only=accepted_only, ranked=ranked).model_dump(
            mode="json"
        )

    @mcp.tool()
    def list_preview_runs(limit: int = 20) -> dict[str, Any]:
        """List recent preview runs recorded under the configured artifact root."""
        bounded_limit = max(1, min(limit, 100))
        return {
            "runs": [run.model_dump(mode="json") for run in preview_service.artifact_store.list_runs(bounded_limit)]
        }

    @mcp.tool()
    def get_preview_manifest(run_id: str) -> dict[str, Any]:
        """Return the manifest JSON for one recorded preview run."""
        return preview_service.artifact_store.read_manifest(run_id)

    @mcp.tool()
    def delete_preview_run(run_id: str) -> dict[str, Any]:
        """Delete one preview run and its artifacts from the configured artifact root."""
        deleted = preview_service.artifact_store.delete_run(run_id)
        return {"deleted": deleted.model_dump(mode="json")}

    @mcp.tool()
    def cleanup_preview_runs(keep_last: int | None = None) -> dict[str, Any]:
        """Delete older preview runs beyond a retention count."""
        deleted = preview_service.artifact_store.cleanup_runs(keep_last)
        return {"deleted_runs": [run.model_dump(mode="json") for run in deleted]}

    @mcp.prompt()
    def build_robustness_augmentation_session(task: str, targets: str = "image") -> str:
        """Guide an assistant through preview-driven augmentation tuning."""
        return build_robustness_prompt(task, targets)

    @mcp.prompt()
    def compare_preview_runs_for_feedback(baseline_run_id: str, candidate_run_id: str) -> str:
        """Guide an assistant through preview run comparison before adjustment."""
        return compare_preview_runs_prompt(baseline_run_id, candidate_run_id)

    @mcp.prompt()
    def tune_pipeline_from_preview_feedback(task: str, run_id: str, feedback_tags: str) -> str:
        """Guide an assistant through structured preview feedback adjustment."""
        return tune_feedback_prompt(task, run_id, feedback_tags)

    @mcp.prompt()
    def export_reproducible_pipeline(run_id: str, output_format: str = "python") -> str:
        """Guide final reproducible pipeline export after preview acceptance."""
        return export_pipeline_prompt(run_id, output_format)

    return mcp
