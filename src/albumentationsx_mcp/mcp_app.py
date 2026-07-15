"""MCP Apps resources for interactive preview review."""

from __future__ import annotations

from collections.abc import Callable
from importlib.resources import files
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from albumentationsx_mcp.preview import ArtifactStore

PREVIEW_REVIEW_APP_URI = "ui://albumentationsx/preview-review.html"
PREVIEW_REVIEW_APP_MIME_TYPE = "text/html;profile=mcp-app"
PREVIEW_ARTIFACT_URI_TEMPLATE = "artifact://{run_id}/{filename}"

ResourceHandler = Callable[..., Any]


class ResourceRegistrar(Protocol):
    """Transport port required to register MCP App resources."""

    def resource(
        self,
        uri: str,
        *,
        name: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Callable[[ResourceHandler], ResourceHandler]: ...


def preview_review_tool_meta() -> dict[str, Any]:
    """Return modern MCP Apps metadata for preview rendering tools."""
    return {
        "ui": {
            "resourceUri": PREVIEW_REVIEW_APP_URI,
            "visibility": ["model", "app"],
        }
    }


def register_preview_review_resources(mcp: ResourceRegistrar, artifact_store: ArtifactStore) -> None:
    """Register the packaged review app and its verified image resource template."""

    @mcp.resource(
        PREVIEW_REVIEW_APP_URI,
        name="AlbumentationsX Preview Review",
        description="Interactive review surface for rendered AlbumentationsX preview batches.",
        mime_type=PREVIEW_REVIEW_APP_MIME_TYPE,
        meta={
            "ui": {
                "csp": {
                    "connectDomains": [],
                    "resourceDomains": [],
                    "frameDomains": [],
                    "baseUriDomains": [],
                },
                "prefersBorder": True,
            }
        },
    )
    def preview_review_app() -> str:
        """Return the self-contained preview review MCP App."""
        return load_preview_review_html()

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
