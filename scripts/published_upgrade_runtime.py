"""Runtime adapter for published AlbumentationsX MCP upgrade probes."""

from __future__ import annotations

import base64
import hashlib
import os
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import BlobResourceContents
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION
from PIL import Image

from albumentationsx_mcp.upgrade_proof import (
    ArtifactContinuity,
    ProtocolObservation,
    PublicSurface,
    build_upgrade_proof_report,
)

PACKAGE = "albumentationsx-mcp"


@dataclass(frozen=True)
class PublishedUpgradeConfig:
    """Inputs shared across the three published-server observations."""

    from_version: str
    to_version: str
    observed_on: str
    allowed_root: Path
    artifact_root: Path
    read_timeout_seconds: float


@dataclass(frozen=True)
class ServerClientRequest:
    """Connection details for one isolated published server process."""

    version: str
    mode: str
    allowed_root: Path
    artifact_root: Path
    read_timeout_seconds: float


class ClientFactory(Protocol):
    """Create connected clients for injectable upgrade orchestration."""

    def __call__(self, request: ServerClientRequest) -> AbstractAsyncContextManager[Client]:
        """Return an async context manager yielding a connected MCP client."""
        raise NotImplementedError


@dataclass(frozen=True)
class _ArtifactSeed:
    run_id: str
    contact_sheet_uri: str
    contact_sheet_sha256: str


def build_uvx_server_command(version: str) -> list[str]:
    """Build an exact-version uvx server command."""
    return [
        "uvx",
        "--from",
        f"{PACKAGE}=={version}",
        "--refresh-package",
        PACKAGE,
        PACKAGE,
    ]


def clean_subprocess_environment(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    """Remove local server overrides from a subprocess environment."""
    source = os.environ if environment is None else environment
    return {name: value for name, value in source.items() if not name.startswith("ALBU_MCP_")}


@asynccontextmanager
async def open_published_client(request: ServerClientRequest) -> AsyncIterator[Client]:
    """Start one pinned published server and yield its connected client."""
    command = build_uvx_server_command(request.version)
    params = StdioServerParameters(
        command=command[0],
        args=[
            *command[1:],
            "--allowed-root",
            str(request.allowed_root),
            "--artifact-root",
            str(request.artifact_root),
            "--capability-profile",
            "full",
        ],
        cwd=str(request.allowed_root),
        env=clean_subprocess_environment(),
    )
    with Path(os.devnull).open("w", encoding="utf-8") as errlog:  # noqa: ASYNC230 - os.devnull opens immediately.
        async with Client(
            stdio_client(params, errlog=errlog),
            mode=request.mode,
            read_timeout_seconds=request.read_timeout_seconds,
        ) as client:
            yield client


async def run_published_upgrade(
    config: PublishedUpgradeConfig,
    *,
    client_factory: ClientFactory = open_published_client,
) -> dict[str, Any]:
    """Probe the legacy-to-modern upgrade matrix and artifact continuity."""
    fixture_path = config.allowed_root / "generated-upgrade-fixture.png"
    Image.new("RGB", (24, 24), (96, 128, 160)).save(fixture_path)

    from_request = _client_request(config, version=config.from_version, mode="legacy")
    async with client_factory(from_request) as client:
        from_surface = await _snapshot_surface(client)
        from_legacy = _observation(
            client,
            from_request,
            evidence_mode="legacy",
            expected_protocol=LATEST_HANDSHAKE_VERSION,
            surface=from_surface,
        )
        seed = await _render_seed(client, fixture_path)

    to_legacy_request = _client_request(config, version=config.to_version, mode="legacy")
    async with client_factory(to_legacy_request) as client:
        to_legacy_surface = await _snapshot_surface(client)
        to_legacy = _observation(
            client,
            to_legacy_request,
            evidence_mode="legacy",
            expected_protocol=LATEST_HANDSHAKE_VERSION,
            surface=to_legacy_surface,
        )

    to_modern_request = _client_request(config, version=config.to_version, mode="auto")
    async with client_factory(to_modern_request) as client:
        to_modern_surface = await _snapshot_surface(client)
        to_modern = _observation(
            client,
            to_modern_request,
            evidence_mode=LATEST_MODERN_VERSION,
            expected_protocol=LATEST_MODERN_VERSION,
            surface=to_modern_surface,
        )
        artifact = await _read_old_artifact(client, seed)

    return dict(
        build_upgrade_proof_report(
            package=PACKAGE,
            from_version=config.from_version,
            to_version=config.to_version,
            observed_on=config.observed_on,
            from_legacy=from_legacy,
            to_legacy=to_legacy,
            to_modern=to_modern,
            artifact=artifact,
        )
    )


def _client_request(config: PublishedUpgradeConfig, *, version: str, mode: str) -> ServerClientRequest:
    return ServerClientRequest(
        version=version,
        mode=mode,
        allowed_root=config.allowed_root,
        artifact_root=config.artifact_root,
        read_timeout_seconds=config.read_timeout_seconds,
    )


def _observation(
    client: Client,
    request: ServerClientRequest,
    *,
    evidence_mode: str,
    expected_protocol: str,
    surface: PublicSurface,
) -> ProtocolObservation:
    server_info = client.server_info
    return ProtocolObservation(
        server_version=request.version,
        observed_server_version=server_info.version if server_info is not None else "<missing>",
        client_mode=evidence_mode,
        expected_protocol=expected_protocol,
        negotiated_protocol=str(client.protocol_version),
        surface=surface,
    )


async def _snapshot_surface(client: Client) -> PublicSurface:
    return PublicSurface.build(
        tools=await _collect_identifiers(client.list_tools, "tools", "name"),
        resources=await _collect_identifiers(client.list_resources, "resources", "uri"),
        resource_templates=await _collect_identifiers(
            client.list_resource_templates,
            "resource_templates",
            "uri_template",
        ),
        prompts=await _collect_identifiers(client.list_prompts, "prompts", "name"),
    )


async def _collect_identifiers(
    fetch: Callable[..., Awaitable[Any]],
    collection_name: str,
    identifier_name: str,
) -> list[str]:
    identifiers: list[str] = []
    cursor: str | None = None
    while True:
        page = await fetch(cursor=cursor, cache_mode="refresh")
        identifiers.extend(str(getattr(item, identifier_name)) for item in getattr(page, collection_name))
        cursor = page.next_cursor
        if cursor is None:
            return identifiers


async def _render_seed(client: Client, fixture_path: Path) -> _ArtifactSeed:
    result = await client.call_tool(
        "render_preview_batch",
        {
            "request": {
                "input_paths": [str(fixture_path)],
                "pipeline": {"transforms": [{"name": "HorizontalFlip", "params": {}, "p": 1.0}]},
                "variants_per_image": 1,
                "seed": 17,
            }
        },
    )
    content = result.structured_content
    if result.is_error or not isinstance(content, Mapping):
        message = "published old server could not render the generated fixture"
        raise RuntimeError(message)

    run_id = content.get("run_id")
    artifact = _contact_sheet_artifact(content)
    contact_sheet_uri = artifact.get("uri")
    manifest_digest = artifact.get("sha256")
    if not isinstance(run_id, str) or not isinstance(contact_sheet_uri, str) or not isinstance(manifest_digest, str):
        message = "published old server returned incomplete contact sheet evidence"
        raise TypeError(message)

    payload = await _read_png_resource(client, contact_sheet_uri)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != manifest_digest:
        message = "published old server contact sheet did not match its manifest digest"
        raise RuntimeError(message)
    return _ArtifactSeed(
        run_id=run_id,
        contact_sheet_uri=contact_sheet_uri,
        contact_sheet_sha256=digest,
    )


async def _read_old_artifact(client: Client, seed: _ArtifactSeed) -> ArtifactContinuity:
    manifest = await client.call_tool("get_preview_manifest", {"run_id": seed.run_id})
    manifest_content = manifest.structured_content
    manifest_readable = not manifest.is_error and isinstance(manifest_content, Mapping)
    manifest_run_id_matches = bool(manifest_readable and manifest_content.get("run_id") == seed.run_id)

    payload = await _read_png_resource(client, seed.contact_sheet_uri)
    digest = hashlib.sha256(payload).hexdigest()
    manifest_digest_matches = False
    if manifest_readable:
        artifact = _contact_sheet_artifact(manifest_content)
        manifest_digest_matches = artifact.get("sha256") == digest

    return ArtifactContinuity(
        manifest_readable=manifest_readable,
        manifest_run_id_matches=manifest_run_id_matches,
        contact_sheet_readable=True,
        content_unchanged=digest == seed.contact_sheet_sha256 and manifest_digest_matches,
        contact_sheet_sha256=digest,
    )


def _contact_sheet_artifact(content: Mapping[str, Any]) -> Mapping[str, Any]:
    artifacts = content.get("artifacts")
    if not isinstance(artifacts, list):
        message = "published server returned no preview artifact list"
        raise TypeError(message)
    for artifact in artifacts:
        if isinstance(artifact, Mapping) and artifact.get("kind") == "contact_sheet":
            return artifact
    message = "published server returned no contact sheet artifact"
    raise RuntimeError(message)


async def _read_png_resource(client: Client, uri: str) -> bytes:
    result = await client.read_resource(uri)
    if not result.contents:
        message = "preview artifact resource returned no content"
        raise RuntimeError(message)
    content = result.contents[0]
    if not isinstance(content, BlobResourceContents) or content.mime_type != "image/png":
        message = "preview artifact resource did not return binary PNG content"
        raise TypeError(message)
    try:
        payload = base64.b64decode(content.blob, validate=True)
    except ValueError as exc:
        message = "preview artifact resource did not return valid base64"
        raise RuntimeError(message) from exc
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        message = "preview artifact resource did not return a valid PNG"
        raise RuntimeError(message)
    try:
        with Image.open(BytesIO(payload)) as decoded:
            is_png = decoded.format == "PNG"
            decoded.verify()
    except (Image.DecompressionBombError, OSError, SyntaxError, ValueError) as exc:
        message = "preview artifact resource did not return a valid PNG"
        raise RuntimeError(message) from exc
    if not is_png:
        message = "preview artifact resource did not return a valid PNG"
        raise RuntimeError(message)
    return payload
