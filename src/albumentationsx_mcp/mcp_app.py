"""MCP Apps resources for interactive preview review."""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from albumentationsx_mcp.preview import ArtifactStore

PREVIEW_REVIEW_APP_URI = "ui://albumentationsx/preview-review.html"
PREVIEW_REVIEW_APP_MIME_TYPE = "text/html;profile=mcp-app"
PREVIEW_ARTIFACT_URI_TEMPLATE = "artifact://{run_id}/{filename}"


class ResourceRegistrar(Protocol):
    """Resource decorator port used by the packaged preview application."""

    resource: Any


def preview_review_tool_meta() -> dict[str, Any]:
    """Return modern MCP Apps metadata for preview rendering tools."""
    return {
        "ui": {
            "resourceUri": PREVIEW_REVIEW_APP_URI,
            "visibility": ["model", "app"],
        }
    }


def preview_review_resource_meta() -> dict[str, Any]:
    """Return network-denying metadata for the packaged preview application."""
    return {
        "ui": {
            "csp": {
                "connectDomains": [],
                "resourceDomains": [],
                "frameDomains": [],
                "baseUriDomains": [],
            },
            "prefersBorder": True,
        }
    }


def register_preview_artifact_resource(mcp: ResourceRegistrar, artifact_store: ArtifactStore) -> None:
    """Register the verified image resource template used by the preview application."""

    @mcp.resource(
        PREVIEW_ARTIFACT_URI_TEMPLATE,
        name="Verified preview image",
        description="Read one manifest-recorded PNG from a bounded preview run.",
        mime_type="image/png",
    )
    def preview_image_artifact(run_id: str, filename: str) -> bytes:
        """Return one integrity-checked preview image."""
        return artifact_store.read_image_artifact(run_id, filename)


def load_preview_review_html() -> str:
    """Load the packaged single-file MCP App HTML."""
    return files("albumentationsx_mcp").joinpath("ui").joinpath("preview-review.html").read_text(encoding="utf-8")
