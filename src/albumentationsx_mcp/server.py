"""FastMCP server registration for AlbumentationsX."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from albumentationsx_mcp.catalog import TransformCatalog
from albumentationsx_mcp.models import ComposeSpec, PreviewRequest, TargetSpec
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.presets import Intensity, adjust_pipeline, recommend_pipeline
from albumentationsx_mcp.preview import ArtifactStore, PathPolicy, PreviewService


class ServerSettings(BaseModel):
    """Runtime settings for local preview and artifact access."""

    allowed_roots: list[Path] = Field(default_factory=lambda: [Path.cwd()])
    artifact_root: Path = Field(default_factory=lambda: Path.cwd() / "artifacts")


def settings_from_environment() -> ServerSettings:
    """Create settings from environment variables."""
    allowed = os.getenv("ALBU_MCP_ALLOWED_ROOTS")
    artifact_root = os.getenv("ALBU_MCP_ARTIFACT_ROOT")
    return ServerSettings(
        allowed_roots=[Path(item) for item in allowed.split(os.pathsep)] if allowed else [Path.cwd()],
        artifact_root=Path(artifact_root) if artifact_root else Path.cwd() / "artifacts",
    )


OutputFormat = Literal["python", "json", "yaml"]


def create_mcp_server(settings: ServerSettings | None = None) -> FastMCP:
    """Create and register the AlbumentationsX FastMCP server."""
    settings = settings or settings_from_environment()
    catalog = TransformCatalog()
    pipeline_service = PipelineService(catalog)
    preview_service = PreviewService(
        pipeline_service,
        PathPolicy(settings.allowed_roots),
        ArtifactStore(settings.artifact_root),
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

    @mcp.prompt()
    def build_robustness_augmentation_session(task: str, targets: str = "image") -> str:
        """Guide an assistant through preview-driven augmentation tuning."""
        return (
            "Use AlbumentationsX MCP to recommend a conservative pipeline for "
            f"{task} with targets {targets}. Validate it, render a small preview set, "
            "ask the user for structured feedback tags, then adjust and re-render. "
            "Keep the exported pipeline and manifest reproducible."
        )

    return mcp
