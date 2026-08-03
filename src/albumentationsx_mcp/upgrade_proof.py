"""Pure compatibility evidence for published AlbumentationsX MCP upgrades."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

_SCHEMA_VERSION = "albumentationsx-mcp/published-upgrade-proof/v1"


@dataclass(frozen=True)
class PublicSurface:
    """Canonical public MCP identifiers observed from one server process."""

    tools: tuple[str, ...]
    resources: tuple[str, ...]
    resource_templates: tuple[str, ...]
    prompts: tuple[str, ...]

    @classmethod
    def build(
        cls,
        *,
        tools: Iterable[str],
        resources: Iterable[str],
        resource_templates: Iterable[str],
        prompts: Iterable[str],
    ) -> PublicSurface:
        return cls(
            tools=_canonical(tools),
            resources=_canonical(resources),
            resource_templates=_canonical(resource_templates),
            prompts=_canonical(prompts),
        )

    def categories(self) -> dict[str, tuple[str, ...]]:
        return {
            "tools": self.tools,
            "resources": self.resources,
            "resource_templates": self.resource_templates,
            "prompts": self.prompts,
        }


@dataclass(frozen=True)
class ProtocolObservation:
    """One published server and current-client protocol observation."""

    server_version: str
    observed_server_version: str
    client_mode: str
    expected_protocol: str
    negotiated_protocol: str
    surface: PublicSurface


@dataclass(frozen=True)
class ArtifactContinuity:
    """Bounded result of reading an old preview through the new server."""

    manifest_readable: bool
    manifest_run_id_matches: bool
    contact_sheet_readable: bool
    content_unchanged: bool
    contact_sheet_sha256: str


def build_upgrade_proof_report(  # noqa: PLR0913
    *,
    package: str,
    from_version: str,
    to_version: str,
    observed_on: str,
    from_legacy: ProtocolObservation,
    to_legacy: ProtocolObservation,
    to_modern: ProtocolObservation,
    artifact: ArtifactContinuity,
) -> dict[str, Any]:
    """Build a deterministic privacy-safe upgrade report."""
    rows = (from_legacy, to_legacy, to_modern)
    failures: list[dict[str, object]] = []
    for row in rows:
        if row.observed_server_version != row.server_version:
            failures.append(
                {
                    "code": "server_version_mismatch",
                    "scope": f"{row.server_version}:{row.client_mode}",
                    "remediation": "Verify the uvx package pin and the published distribution metadata.",
                }
            )
        if row.negotiated_protocol != row.expected_protocol:
            failures.append(
                {
                    "code": "protocol_negotiation_failed",
                    "scope": f"{row.server_version}:{row.client_mode}",
                    "remediation": "Verify the selected client mode and published server SDK compatibility.",
                }
            )

    categories: dict[str, Any] = {}
    old_surface_is_subset = True
    for name, old_identifiers in from_legacy.surface.categories().items():
        new_identifiers = to_legacy.surface.categories()[name]
        missing = sorted(set(old_identifiers) - set(new_identifiers))
        categories[name] = {
            "ok": not missing,
            "old": _surface_summary(old_identifiers),
            "new": _surface_summary(new_identifiers),
            "missing": missing,
        }
        if missing:
            old_surface_is_subset = False
            failures.append(
                {
                    "code": "surface_removed",
                    "scope": name,
                    "missing": missing,
                    "remediation": "Restore the published identifier or document and version a breaking change.",
                }
            )

    new_modes_equal = to_legacy.surface == to_modern.surface
    if not new_modes_equal:
        failures.append(
            {
                "code": "new_mode_surface_mismatch",
                "scope": to_version,
                "remediation": "Register the same capability profile for legacy and modern protocol modes.",
            }
        )

    artifact_ok = all(
        (
            artifact.manifest_readable,
            artifact.manifest_run_id_matches,
            artifact.contact_sheet_readable,
            artifact.content_unchanged,
        )
    )
    if not artifact_ok:
        failures.append(
            {
                "code": "artifact_continuity_failed",
                "scope": f"{from_version}->{to_version}",
                "remediation": "Inspect manifest and artifact resource compatibility before releasing an upgrade.",
            }
        )

    return {
        "schema_version": _SCHEMA_VERSION,
        "package": package,
        "from_version": from_version,
        "to_version": to_version,
        "observed_on": observed_on,
        "status": "pass" if not failures else "fail",
        "matrix": [_protocol_summary(row) for row in rows],
        "compatibility": {
            "old_surface_is_subset": old_surface_is_subset,
            "new_modes_equal": new_modes_equal,
            "categories": categories,
        },
        "artifact_continuity": {
            "ok": artifact_ok,
            "manifest_readable": artifact.manifest_readable,
            "manifest_run_id_matches": artifact.manifest_run_id_matches,
            "contact_sheet_readable": artifact.contact_sheet_readable,
            "content_unchanged": artifact.content_unchanged,
            "contact_sheet_sha256": artifact.contact_sheet_sha256,
        },
        "failures": failures,
    }


def _protocol_summary(row: ProtocolObservation) -> dict[str, object]:
    return {
        "server_version": row.server_version,
        "observed_server_version": row.observed_server_version,
        "client_mode": row.client_mode,
        "expected_protocol": row.expected_protocol,
        "negotiated_protocol": row.negotiated_protocol,
        "ok": row.expected_protocol == row.negotiated_protocol,
        "surface": {name: _surface_summary(values) for name, values in row.surface.categories().items()},
    }


def _surface_summary(identifiers: Iterable[str]) -> dict[str, object]:
    canonical = _canonical(identifiers)
    return {"count": len(canonical), "sha256": _digest(canonical)}


def _canonical(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _digest(values: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()
