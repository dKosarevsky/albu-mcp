"""FastMCP composition root for AlbumentationsX."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from albumentationsx_mcp.adapters.mcp.dependencies import McpDependencies
from albumentationsx_mcp.adapters.mcp.preview import (
    export_matching_tuning_session_artifacts as _export_session_artifacts,
)
from albumentationsx_mcp.adapters.mcp.registration import (
    PUBLIC_PROMPTS,
    PUBLIC_TOOLS,
    PUBLIC_WORKFLOW_RESOURCES,
    register_mcp_adapters,
)
from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.diagnostics import DiagnosticsService, PublicSurface
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.preview import ArtifactStore, PathPolicy, PreviewService
from albumentationsx_mcp.preview_validation import PreviewRequestValidator
from albumentationsx_mcp.reports import PreviewReportService
from albumentationsx_mcp.review import PreviewFeedbackStore
from albumentationsx_mcp.sessions import InteractiveTuningSessionStore
from albumentationsx_mcp.tuning import TuningDecisionStore

if TYPE_CHECKING:
    from albumentationsx_mcp.models import ArtifactRef


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


def create_mcp_server(settings: ServerSettings | None = None) -> FastMCP:
    """Construct application services and register the public MCP surface."""
    settings = settings or settings_from_environment()
    catalog = TransformCatalog()
    pipeline_service = PipelineService(catalog)
    path_policy = PathPolicy(settings.allowed_roots)
    artifact_store = ArtifactStore(settings.artifact_root, max_runs=settings.max_preview_runs)
    preview_service = PreviewService(pipeline_service, path_policy, artifact_store)
    preview_validator = PreviewRequestValidator(
        pipeline_service=pipeline_service,
        path_policy=path_policy,
    )
    tuning_store = TuningDecisionStore(settings.artifact_root)
    session_store = InteractiveTuningSessionStore(settings.artifact_root)
    feedback_store = PreviewFeedbackStore(settings.artifact_root)
    report_service = PreviewReportService(settings.artifact_root)
    diagnostics_service = DiagnosticsService(
        allowed_roots=settings.allowed_roots,
        artifact_root=settings.artifact_root,
        max_preview_runs=settings.max_preview_runs,
        public_surface=PublicSurface(
            tools=list(PUBLIC_TOOLS),
            prompts=list(PUBLIC_PROMPTS),
            workflow_resources=list(PUBLIC_WORKFLOW_RESOURCES),
        ),
    )
    dependencies = McpDependencies(
        catalog=catalog,
        pipeline_service=pipeline_service,
        path_policy=path_policy,
        artifact_store=artifact_store,
        preview_service=preview_service,
        preview_validator=preview_validator,
        tuning_store=tuning_store,
        session_store=session_store,
        feedback_store=feedback_store,
        report_service=report_service,
        diagnostics_service=diagnostics_service,
    )
    mcp = FastMCP("AlbumentationsX MCP")
    register_mcp_adapters(mcp, dependencies)
    return mcp


def _export_matching_tuning_session_artifacts(
    session_store: InteractiveTuningSessionStore,
    *,
    baseline_run_id: str,
    candidate_run_ids: set[str],
) -> list[ArtifactRef]:
    return _export_session_artifacts(
        session_store,
        baseline_run_id=baseline_run_id,
        candidate_run_ids=candidate_run_ids,
    )
