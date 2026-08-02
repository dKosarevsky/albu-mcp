"""Official MCP Apps extension and legacy-compatible fallback registration."""

from __future__ import annotations

from collections.abc import Collection
from typing import TYPE_CHECKING, Any

from mcp.server.apps import Apps, ResourceCsp

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface, ProfileSurface
from albumentationsx_mcp.capabilities import REVIEW_DATASET_PROFILE_MEMBERSHIP, REVIEW_PROFILE_MEMBERSHIP
from albumentationsx_mcp.mcp_app import (
    PREVIEW_REVIEW_APP_MIME_TYPE,
    PREVIEW_REVIEW_APP_URI,
    load_preview_review_html,
    preview_review_resource_meta,
    preview_review_tool_meta,
)
from albumentationsx_mcp.models import PreviewRequest

if TYPE_CHECKING:
    from albumentationsx_mcp.adapters.mcp.registrar import McpRegistrar
    from albumentationsx_mcp.preview import PreviewService

_TOOLS = ("render_preview", "render_preview_batch")
_RESOURCES = (PREVIEW_REVIEW_APP_URI,)
SURFACE = AdapterSurface(
    adapter="preview_app",
    tools=_TOOLS,
    resources=_RESOURCES,
    profile_surfaces=(
        ProfileSurface(profiles=REVIEW_PROFILE_MEMBERSHIP, tools=("render_preview",)),
        ProfileSurface(
            profiles=REVIEW_DATASET_PROFILE_MEMBERSHIP,
            tools=("render_preview_batch",),
            resources=_RESOURCES,
        ),
    ),
)


def build_preview_review_apps(
    preview_service: PreviewService,
    *,
    available_tools: Collection[str],
) -> Apps | None:
    """Build the official Apps extension for the active capability profile."""
    selected_tools = set(_TOOLS) & set(available_tools)
    if not selected_tools:
        return None

    apps = Apps()
    if "render_preview" in selected_tools:

        @apps.tool(
            name="render_preview",
            resource_uri=PREVIEW_REVIEW_APP_URI,
            visibility=["model", "app"],
        )
        def render_preview(request: dict[str, Any]) -> dict[str, Any]:
            """Render deterministic preview artifacts for local input images."""
            return _render_preview(preview_service, request)

    if "render_preview_batch" in selected_tools:

        @apps.tool(
            name="render_preview_batch",
            resource_uri=PREVIEW_REVIEW_APP_URI,
            visibility=["model", "app"],
        )
        def render_preview_batch(request: dict[str, Any]) -> dict[str, Any]:
            """Render deterministic batch preview artifacts and contact sheets for local input images."""
            return _render_preview(preview_service, request)

    apps.add_html_resource(
        PREVIEW_REVIEW_APP_URI,
        load_preview_review_html(),
        name="AlbumentationsX Preview Review",
        description="Interactive review surface for rendered AlbumentationsX preview batches.",
        csp=ResourceCsp(
            connect_domains=[],
            resource_domains=[],
            frame_domains=[],
            base_uri_domains=[],
        ),
        prefers_border=True,
    )
    return apps


def register_preview_app_fallback(mcp: McpRegistrar, *, preview_service: PreviewService) -> None:
    """Register the same Apps surface when no extension was composed externally."""

    @mcp.resource(
        PREVIEW_REVIEW_APP_URI,
        name="AlbumentationsX Preview Review",
        description="Interactive review surface for rendered AlbumentationsX preview batches.",
        mime_type=PREVIEW_REVIEW_APP_MIME_TYPE,
        meta=preview_review_resource_meta(),
    )
    def preview_review_app() -> str:
        """Return the self-contained preview review MCP App."""
        return load_preview_review_html()

    @mcp.tool(name="render_preview", meta=preview_review_tool_meta())
    def render_preview(request: dict[str, Any]) -> dict[str, Any]:
        """Render deterministic preview artifacts for local input images."""
        return _render_preview(preview_service, request)

    @mcp.tool(name="render_preview_batch", meta=preview_review_tool_meta())
    def render_preview_batch(request: dict[str, Any]) -> dict[str, Any]:
        """Render deterministic batch preview artifacts and contact sheets for local input images."""
        return _render_preview(preview_service, request)


def _render_preview(preview_service: PreviewService, request: dict[str, Any]) -> dict[str, Any]:
    preview_request = PreviewRequest.model_validate(request)
    return preview_service.render_preview(preview_request).model_dump(mode="json")
