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
from albumentationsx_mcp.dataset import score_dataset_preview_candidates as score_dataset_candidates
from albumentationsx_mcp.dataset_quality import inspect_dataset_quality
from albumentationsx_mcp.diagnostics import DiagnosticsService, PublicSurface, build_diagnostics_guide
from albumentationsx_mcp.host_smoke import build_host_smoke_report
from albumentationsx_mcp.models import (
    ArtifactRef,
    ComposeSpec,
    InteractiveTuningSession,
    PreviewFeedbackRecord,
    PreviewRequest,
    QualityProfileName,
    TargetSpec,
)
from albumentationsx_mcp.onboarding import build_dataset_onboarding_report
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.presets import Intensity, adjust_pipeline, recommend_pipeline
from albumentationsx_mcp.preview import ArtifactStore, PathPolicy, PreviewService
from albumentationsx_mcp.preview_validation import PreviewRequestValidator
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
from albumentationsx_mcp.quality import list_quality_profiles
from albumentationsx_mcp.ranking import rank_preview_candidates as rank_candidates
from albumentationsx_mcp.recipes import list_recipe_catalog, recommend_recipe
from albumentationsx_mcp.reports import PreviewReportService
from albumentationsx_mcp.review import PreviewFeedbackStore
from albumentationsx_mcp.review_agent import (
    build_review_agent_plan,
)
from albumentationsx_mcp.review_agent import (
    interpret_preview_feedback as interpret_feedback_note,
)
from albumentationsx_mcp.review_packet import build_review_packet
from albumentationsx_mcp.sessions import InteractiveTuningSessionStore
from albumentationsx_mcp.tuning import TuningDecisionStore, build_tuning_session_summary
from albumentationsx_mcp.workflows import (
    get_agent_workflow,
    get_host_example,
    list_agent_workflows,
    list_task_profiles,
)

_PUBLIC_TOOLS = [
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
    "export_pipeline",
    "diagnose_environment",
    "run_host_smoke_check",
    "validate_preview_request",
    "plan_dataset_onboarding",
    "build_review_packet",
    "inspect_dataset_quality",
]
_PUBLIC_PROMPTS = [
    "build_robustness_augmentation_session",
    "run_first_preview_review",
    "compare_preview_runs_for_feedback",
    "tune_pipeline_from_preview_feedback",
    "export_reproducible_pipeline",
]
_PUBLIC_WORKFLOW_RESOURCES = [
    "albumentationsx://workflows/catalog",
    "albumentationsx://workflows/preview-tuning",
    "albumentationsx://workflows/annotation-preview",
    "albumentationsx://workflows/task-profiles",
    "albumentationsx://recipes/catalog",
    "albumentationsx://diagnostics/guide",
    "albumentationsx://examples/client-smoke",
    "albumentationsx://examples/first-preview",
    "albumentationsx://examples/distortion-review",
    "albumentationsx://examples/dataset-onboarding",
    "albumentationsx://examples/diagnostics",
    "albumentationsx://examples/review-loop",
    "albumentationsx://examples/report-handoff",
]


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
    preview_validator = PreviewRequestValidator(
        pipeline_service=pipeline_service,
        path_policy=PathPolicy(settings.allowed_roots),
    )
    tuning_store = TuningDecisionStore(settings.artifact_root)
    session_store = InteractiveTuningSessionStore(settings.artifact_root)
    feedback_store = PreviewFeedbackStore(settings.artifact_root)
    report_service = PreviewReportService(settings.artifact_root)
    public_surface = PublicSurface(
        tools=_PUBLIC_TOOLS,
        prompts=_PUBLIC_PROMPTS,
        workflow_resources=_PUBLIC_WORKFLOW_RESOURCES,
    )
    diagnostics_service = DiagnosticsService(
        allowed_roots=settings.allowed_roots,
        artifact_root=settings.artifact_root,
        max_preview_runs=settings.max_preview_runs,
        public_surface=public_surface,
    )
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

    @mcp.resource("albumentationsx://recipes/catalog")
    def recipes_catalog_resource() -> str:
        """Return task-aware recipe recommendations as compact JSON."""
        data = [recipe.model_dump(mode="json") for recipe in list_recipe_catalog()]
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
                "tools": _PUBLIC_TOOLS,
                "prompts": _PUBLIC_PROMPTS,
                "workflow_resources": _PUBLIC_WORKFLOW_RESOURCES,
            },
            sort_keys=True,
        )

    @mcp.resource("albumentationsx://diagnostics/guide")
    def diagnostics_guide_resource() -> str:
        """Return the MCP host diagnostics playbook."""
        return build_diagnostics_guide().model_dump_json()

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

    @mcp.resource("albumentationsx://examples/client-smoke")
    def client_smoke_example() -> str:
        """Return the MCP host smoke-check example."""
        return get_host_example("client-smoke").model_dump_json()

    @mcp.resource("albumentationsx://examples/first-preview")
    def first_preview_example() -> str:
        """Return the MCP first local preview host example."""
        return get_host_example("first-preview").model_dump_json()

    @mcp.resource("albumentationsx://examples/distortion-review")
    def distortion_review_example() -> str:
        """Return the MCP distorted robustness review example."""
        return get_host_example("distortion-review").model_dump_json()

    @mcp.resource("albumentationsx://examples/dataset-onboarding")
    def dataset_onboarding_example() -> str:
        """Return the MCP dataset onboarding host example."""
        return get_host_example("dataset-onboarding").model_dump_json()

    @mcp.resource("albumentationsx://examples/diagnostics")
    def diagnostics_example() -> str:
        """Return the MCP host diagnostics example."""
        return get_host_example("diagnostics").model_dump_json()

    @mcp.resource("albumentationsx://examples/review-loop")
    def review_loop_example() -> str:
        """Return the concrete preview feedback host example."""
        return get_host_example("review-loop").model_dump_json()

    @mcp.resource("albumentationsx://examples/report-handoff")
    def report_handoff_example() -> str:
        """Return the visual report handoff host example."""
        return get_host_example("report-handoff").model_dump_json()

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

    @mcp.tool(name="recommend_recipe")
    def recommend_recipe_tool(
        task: str,
        intensity: Intensity = "medium",
        targets: list[str] | None = None,
    ) -> dict[str, Any]:
        """Recommend a task-aware starter pipeline, quality profile, and preview workflow."""
        return recommend_recipe(task=task, intensity=intensity, targets=targets).model_dump(
            mode="json",
            exclude_none=True,
        )

    @mcp.tool()
    def export_pipeline(pipeline: dict[str, Any], output_format: OutputFormat = "python") -> dict[str, Any]:
        """Export a validated pipeline as Python, JSON, or YAML."""
        spec = ComposeSpec.model_validate(pipeline)
        return pipeline_service.export_pipeline(spec, output_format=output_format).model_dump(mode="json")

    @mcp.tool(name="diagnose_environment")
    def diagnose_environment_tool(include_write_probe: bool = True) -> dict[str, Any]:  # noqa: FBT001, FBT002
        """Diagnose local MCP setup, root access, artifact writes, and public surface discovery."""
        return diagnostics_service.diagnose(include_write_probe=include_write_probe).model_dump(mode="json")

    @mcp.tool(name="run_host_smoke_check")
    def run_host_smoke_check_tool(
        include_write_probe: bool = True,  # noqa: FBT001, FBT002
        task: str = "classification",
        intensity: Intensity = "low",
        targets: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a read-only host preflight before rendering local previews."""
        diagnostics = diagnostics_service.diagnose(include_write_probe=include_write_probe)
        recipe = recommend_recipe(task=task, intensity=intensity, targets=targets)
        validation = pipeline_service.validate_pipeline(recipe.pipeline, TargetSpec(targets=recipe.targets))
        return build_host_smoke_report(
            diagnostics=diagnostics,
            recipe=recipe,
            validation=validation,
        ).model_dump(mode="json")

    @mcp.tool(name="validate_preview_request")
    def validate_preview_request_tool(request: dict[str, Any], target: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate a preview request before rendering local preview artifacts."""
        target_spec = TargetSpec.model_validate(target or {})
        return preview_validator.validate(request, target=target_spec).model_dump(mode="json")

    @mcp.tool(name="plan_dataset_onboarding")
    def plan_dataset_onboarding_tool(
        dataset_path: str,
        task: str = "classification",
        intensity: Intensity = "low",
        targets: list[str] | None = None,
        max_images: int = 8,
    ) -> dict[str, Any]:
        """Plan the first safe preview for a local image dataset folder."""
        return build_dataset_onboarding_report(
            dataset_path=Path(dataset_path),
            task=task,
            intensity=intensity,
            targets=targets,
            max_images=max_images,
            path_policy=PathPolicy(settings.allowed_roots),
            pipeline_service=pipeline_service,
            recipe_builder=recommend_recipe,
        ).model_dump(mode="json", exclude_none=True)

    @mcp.tool(name="build_review_packet")
    def build_review_packet_tool(
        dataset_path: str,
        task: str = "classification",
        intensity: Intensity = "low",
        targets: list[str] | None = None,
        max_images: int = 8,
    ) -> dict[str, Any]:
        """Build one host-facing first-preview handoff packet for a local dataset."""
        return build_review_packet(
            dataset_path=Path(dataset_path),
            task=task,
            intensity=intensity,
            targets=targets,
            max_images=max_images,
            path_policy=PathPolicy(settings.allowed_roots),
            pipeline_service=pipeline_service,
            recipe_builder=recommend_recipe,
        ).model_dump(mode="json", exclude_none=True)

    @mcp.tool(name="inspect_dataset_quality")
    def inspect_dataset_quality_tool(dataset_path: str, max_images: int = 8) -> dict[str, Any]:
        """Inspect local dataset image quality before first preview rendering."""
        return inspect_dataset_quality(
            dataset_path=Path(dataset_path),
            max_images=max_images,
            path_policy=PathPolicy(settings.allowed_roots),
        ).model_dump(mode="json", exclude_none=True)

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
    def interpret_preview_feedback(feedback_note: str) -> dict[str, Any]:
        """Convert free-form preview feedback into structured feedback tags."""
        return interpret_feedback_note(feedback_note).model_dump(mode="json")

    @mcp.tool()
    def plan_preview_review(  # noqa: PLR0913
        baseline_run_id: str,
        candidate_run_id: str,
        feedback_tags: list[str] | None = None,
        feedback_note: str | None = None,
        accepted: bool = False,  # noqa: FBT001, FBT002
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Plan the next review action for one baseline-to-candidate preview comparison."""
        comparison = preview_service.compare_preview_runs(
            baseline_run_id,
            candidate_run_id,
            quality_profile=quality_profile,
        )
        return build_review_agent_plan(
            comparison,
            feedback_tags=feedback_tags or [],
            feedback_note=feedback_note,
            accepted=accepted,
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
    def start_tuning_session(
        task: str,
        targets: list[str] | None = None,
        baseline_run_id: str | None = None,
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Start a persistent multi-step preview tuning session."""
        if baseline_run_id is not None:
            preview_service.artifact_store.read_manifest(baseline_run_id)
        return session_store.start_session(
            task=task,
            targets=targets or ["image"],
            baseline_run_id=baseline_run_id,
            quality_profile=quality_profile,
        ).model_dump(mode="json")

    @mcp.tool()
    def record_tuning_session_step(  # noqa: PLR0913
        session_id: str,
        baseline_run_id: str,
        candidate_run_id: str,
        feedback_tags: list[str] | None = None,
        accepted: bool = False,  # noqa: FBT001, FBT002
        reviewer_notes: list[str] | None = None,
        quality_profile: QualityProfileName = "balanced",
    ) -> dict[str, Any]:
        """Record one candidate comparison inside an interactive tuning session."""
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
        return session_store.record_step(
            session_id,
            summary=summary,
            reviewer_notes=reviewer_notes,
        ).model_dump(mode="json")

    @mcp.tool()
    def list_tuning_sessions(
        limit: int = 20,
        status: Literal["active", "accepted", "rejected", "archived"] | None = None,
    ) -> dict[str, Any]:
        """List persisted interactive preview tuning sessions."""
        return session_store.list_sessions(limit=limit, status=status).model_dump(mode="json")

    @mcp.tool()
    def export_tuning_session(
        session_id: str,
        output_format: Literal["markdown", "json"] = "markdown",
    ) -> dict[str, Any]:
        """Export one interactive tuning session as Markdown or JSON."""
        return session_store.export_session(session_id, output_format=output_format).model_dump(mode="json")

    @mcp.tool()
    def close_tuning_session(
        session_id: str,
        status: Literal["accepted", "rejected"],
        accepted_candidate_run_id: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Close an interactive tuning session as accepted or rejected."""
        return session_store.close_session(
            session_id,
            status=status,
            accepted_candidate_run_id=accepted_candidate_run_id,
            note=note,
        ).model_dump(mode="json")

    @mcp.tool()
    def archive_tuning_session(session_id: str, note: str | None = None) -> dict[str, Any]:
        """Archive an interactive tuning session without deleting its audit trail."""
        return session_store.archive_session(session_id, note=note).model_dump(mode="json")

    @mcp.tool()
    def cleanup_tuning_sessions(
        keep_last: int = 100,
        include_active: bool = False,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """Delete older interactive tuning sessions, protecting active sessions by default."""
        return session_store.cleanup_sessions(keep_last=keep_last, include_active=include_active).model_dump(
            mode="json"
        )

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

    @mcp.tool()
    def record_preview_feedback(  # noqa: PLR0913
        run_id: str,
        image_index: int,
        variant_index: int,
        feedback_tags: list[str] | None = None,
        note: str = "",
        accepted: bool = False,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """Persist user feedback for one concrete preview image variant."""
        manifest = preview_service.artifact_store.read_manifest(run_id)
        _validate_feedback_target(manifest, image_index=image_index, variant_index=variant_index)
        return feedback_store.record_feedback(
            run_id=run_id,
            image_index=image_index,
            variant_index=variant_index,
            feedback_tags=feedback_tags or [],
            note=note,
            accepted=accepted,
        ).model_dump(mode="json")

    @mcp.tool()
    def list_preview_feedback(
        run_id: str | None = None,
        limit: int = 20,
        accepted_only: bool = False,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """List concrete preview feedback records."""
        return feedback_store.list_feedback(
            run_id=run_id,
            limit=limit,
            accepted_only=accepted_only,
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
    def export_tuning_report(
        output_format: Literal["markdown", "json"] = "markdown",
        limit: int = 20,
        accepted_only: bool = False,  # noqa: FBT001, FBT002
        ranked: bool = True,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """Export persisted tuning decisions as markdown or JSON."""
        return tuning_store.export_report(
            output_format=output_format,
            limit=limit,
            accepted_only=accepted_only,
            ranked=ranked,
        ).model_dump(mode="json")

    @mcp.tool()
    def export_preview_report(  # noqa: PLR0913
        baseline_run_id: str,
        candidate_run_ids: list[str],
        output_format: Literal["markdown", "html"] = "markdown",
        feedback_tags_by_candidate: dict[str, list[str]] | None = None,
        accepted_candidate_ids: list[str] | None = None,
        quality_profile: QualityProfileName = "balanced",
        include_decisions: bool = True,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """Export a visual preview report with ranking, contact sheets, and decisions."""
        if not candidate_run_ids:
            msg = "candidate_run_ids must contain at least one run id"
            raise ValueError(msg)
        bounded_candidate_ids = candidate_run_ids[:20]
        comparisons = [
            preview_service.compare_preview_runs(
                baseline_run_id,
                candidate_run_id,
                quality_profile=quality_profile,
            )
            for candidate_run_id in bounded_candidate_ids
        ]
        score = score_dataset_candidates(
            comparisons,
            feedback_tags_by_candidate=feedback_tags_by_candidate or {},
            accepted_candidate_ids=set(accepted_candidate_ids or []),
            quality_profile=quality_profile,
        )
        tuning_sessions = _matching_tuning_sessions(
            session_store,
            baseline_run_id=baseline_run_id,
            candidate_run_ids=set(bounded_candidate_ids),
        )
        return report_service.export_report(
            score,
            baseline_manifest=preview_service.artifact_store.read_manifest(baseline_run_id),
            candidate_manifests=[
                preview_service.artifact_store.read_manifest(candidate_run_id)
                for candidate_run_id in bounded_candidate_ids
            ],
            decisions=_matching_tuning_decisions(
                tuning_store,
                baseline_run_id=baseline_run_id,
                candidate_run_ids=set(bounded_candidate_ids),
                include_decisions=include_decisions,
            ),
            feedback_records=_matching_preview_feedback(
                feedback_store,
                run_ids={baseline_run_id, *bounded_candidate_ids},
            ),
            tuning_sessions=tuning_sessions,
            tuning_session_artifacts=_export_tuning_session_artifacts(session_store, tuning_sessions),
            output_format=output_format,
        ).model_dump(mode="json")

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

    return mcp


def _matching_tuning_decisions(
    tuning_store: TuningDecisionStore,
    *,
    baseline_run_id: str,
    candidate_run_ids: set[str],
    include_decisions: bool,
) -> list[Any]:
    if not include_decisions:
        return []
    decisions = tuning_store.list_decisions(limit=100, ranked=True).decisions
    return [
        decision
        for decision in decisions
        if decision.baseline_run_id == baseline_run_id and decision.candidate_run_id in candidate_run_ids
    ]


def _matching_preview_feedback(
    feedback_store: PreviewFeedbackStore,
    *,
    run_ids: set[str],
) -> list[PreviewFeedbackRecord]:
    records: list[PreviewFeedbackRecord] = []
    for run_id in sorted(run_ids):
        records.extend(feedback_store.list_feedback(run_id=run_id, limit=100).feedback)
    return sorted(records, key=lambda record: record.created_at, reverse=True)


def _matching_tuning_sessions(
    session_store: InteractiveTuningSessionStore,
    *,
    baseline_run_id: str,
    candidate_run_ids: set[str],
) -> list[InteractiveTuningSession]:
    sessions = session_store.list_sessions(limit=100).sessions
    return [
        session
        for session in sessions
        if session.baseline_run_id == baseline_run_id
        and (
            session.accepted_candidate_run_id in candidate_run_ids
            or any(step.candidate_run_id in candidate_run_ids for step in session.steps)
        )
    ]


def _export_matching_tuning_session_artifacts(
    session_store: InteractiveTuningSessionStore,
    *,
    baseline_run_id: str,
    candidate_run_ids: set[str],
) -> list[ArtifactRef]:
    return _export_tuning_session_artifacts(
        session_store,
        _matching_tuning_sessions(
            session_store,
            baseline_run_id=baseline_run_id,
            candidate_run_ids=candidate_run_ids,
        ),
    )


def _export_tuning_session_artifacts(
    session_store: InteractiveTuningSessionStore,
    sessions: list[InteractiveTuningSession],
) -> list[ArtifactRef]:
    return [session_store.export_session(session.session_id, output_format="markdown").artifact for session in sessions]


def _validate_feedback_target(manifest: dict[str, Any], *, image_index: int, variant_index: int) -> None:
    summary = manifest.get("summary", {})
    input_count = int(summary.get("input_count", len(manifest.get("inputs", []))))
    variants_per_image = int(summary.get("variants_per_image", 1))
    if image_index < 0 or image_index >= input_count:
        msg = f"image_index must be between 0 and {max(input_count - 1, 0)}"
        raise ValueError(msg)
    if variant_index < 0 or variant_index >= variants_per_image:
        msg = f"variant_index must be between 0 and {max(variants_per_image - 1, 0)}"
        raise ValueError(msg)
