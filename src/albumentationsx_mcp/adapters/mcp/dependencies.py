"""Constructed dependencies required by the MCP registration adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from albumentationsx_mcp.catalog import TransformCatalog
    from albumentationsx_mcp.diagnostics import DiagnosticsService
    from albumentationsx_mcp.pipeline import PipelineService
    from albumentationsx_mcp.preview import ArtifactStore, PathPolicy, PreviewService
    from albumentationsx_mcp.preview_validation import PreviewRequestValidator
    from albumentationsx_mcp.reports import PreviewReportService
    from albumentationsx_mcp.review import PreviewFeedbackStore
    from albumentationsx_mcp.sessions import InteractiveTuningSessionStore
    from albumentationsx_mcp.tuning import TuningDecisionStore


@dataclass(frozen=True, slots=True)
class McpDependencies:
    """Already-constructed application services consumed by MCP adapters."""

    catalog: TransformCatalog
    pipeline_service: PipelineService
    path_policy: PathPolicy
    artifact_store: ArtifactStore
    preview_service: PreviewService
    preview_validator: PreviewRequestValidator
    tuning_store: TuningDecisionStore
    session_store: InteractiveTuningSessionStore
    feedback_store: PreviewFeedbackStore
    report_service: PreviewReportService
    diagnostics_service: DiagnosticsService
