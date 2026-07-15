"""FastMCP catalog and discovery registration."""

from __future__ import annotations

import json
from collections.abc import Collection
from typing import TYPE_CHECKING, Any

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface, ProfileSurface
from albumentationsx_mcp.advisor import list_feedback_tags
from albumentationsx_mcp.capabilities import CORE_PROFILE_MEMBERSHIP
from albumentationsx_mcp.models import ComposeSpec
from albumentationsx_mcp.presets import Intensity
from albumentationsx_mcp.quality import list_quality_profiles
from albumentationsx_mcp.recipes import list_recipe_catalog, recommend_recipe

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from albumentationsx_mcp.catalog import TransformCatalog

_TOOLS = (
    "search_transforms",
    "get_transform_schema",
    "list_feedback_tags",
    "list_quality_profiles",
    "recommend_recipe",
)
_RESOURCES = (
    "albumentationsx://transforms/catalog",
    "albumentationsx://schemas/pipeline",
    "albumentationsx://feedback-tags",
    "albumentationsx://quality-profiles",
    "albumentationsx://recipes/catalog",
)
_RESOURCE_TEMPLATES = ("albumentationsx://transforms/{name}",)
SURFACE = AdapterSurface(
    adapter="catalog",
    tools=_TOOLS,
    resources=_RESOURCES,
    resource_templates=_RESOURCE_TEMPLATES,
    profile_surfaces=(
        ProfileSurface(
            profiles=CORE_PROFILE_MEMBERSHIP,
            tools=_TOOLS,
            resources=_RESOURCES,
            resource_templates=_RESOURCE_TEMPLATES,
        ),
    ),
)


def register_catalog_adapter(
    mcp: FastMCP,
    *,
    catalog: TransformCatalog,
    available_tools: Collection[str] | None = None,
) -> None:
    """Register transform, schema, feedback, quality, and recipe discovery."""

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
        data = [recipe.model_dump(mode="json") for recipe in list_recipe_catalog(available_tools=available_tools)]
        return json.dumps(data, sort_keys=True)

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
        return recommend_recipe(
            task=task,
            intensity=intensity,
            targets=targets,
            available_tools=available_tools,
        ).model_dump(
            mode="json",
            exclude_none=True,
        )
