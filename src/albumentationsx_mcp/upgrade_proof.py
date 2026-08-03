"""Pure compatibility evidence for published AlbumentationsX MCP upgrades."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Final, Literal, TypeAlias, TypedDict, TypeGuard

from packaging.version import InvalidVersion, Version

_SCHEMA_VERSION: Final = "albumentationsx-mcp/published-upgrade-proof/v1"
_PACKAGE_NAME: Final = "albumentationsx-mcp"
_MAX_RELEASE_LENGTH: Final = 128
_LEGACY_MODE: Final = "legacy"
_MODERN_MODE: Final = "2026-07-28"
_LEGACY_PROTOCOL: Final = "2025-11-25"
_MODERN_PROTOCOL: Final = "2026-07-28"
_SUPPORTED_MODES: Final = frozenset({_LEGACY_MODE, _MODERN_MODE})
_SUPPORTED_PROTOCOLS: Final = frozenset({_LEGACY_PROTOCOL, _MODERN_PROTOCOL})
_NORMALIZED_PACKAGE_NAME: Final = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_PUBLIC_RELEASE_VERSION: Final = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")
_ISO_DATE: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_LOWER_SHA256: Final = re.compile(r"[0-9a-f]{64}\Z")

ReportStatus: TypeAlias = Literal["pass", "fail"]
MatrixRole: TypeAlias = Literal["from_legacy", "to_legacy", "to_modern"]
SurfaceCategory: TypeAlias = Literal["tools", "resources", "resource_templates", "prompts"]
FailureCode: TypeAlias = Literal[
    "artifact_continuity_failed",
    "artifact_sha256_invalid",
    "new_mode_surface_mismatch",
    "observation_invalid",
    "observed_on_invalid",
    "package_invalid",
    "protocol_negotiation_failed",
    "row_mode_mismatch",
    "row_protocol_mismatch",
    "row_version_mismatch",
    "server_version_mismatch",
    "surface_removed",
    "upgrade_version_order_invalid",
    "version_invalid",
]


class SurfaceSummary(TypedDict):
    """Bounded summary of one canonical identifier set."""

    count: int
    sha256: str


class SurfaceSummaryByCategory(TypedDict):
    """Fixed public-surface summary categories."""

    tools: SurfaceSummary
    resources: SurfaceSummary
    resource_templates: SurfaceSummary
    prompts: SurfaceSummary


class ProtocolSummary(TypedDict):
    """Sanitized matrix row emitted by the report."""

    role: MatrixRole
    server_version: str | None
    observed_server_version: str | None
    client_mode: str | None
    expected_protocol: str | None
    negotiated_protocol: str | None
    server_version_ok: bool
    protocol_ok: bool
    ok: bool
    surface: SurfaceSummaryByCategory


class CategoryCompatibility(TypedDict):
    """Compatibility evidence for one public-surface category."""

    ok: bool
    old: SurfaceSummary
    new: SurfaceSummary
    missing_count: int
    missing_sha256: str


class CompatibilityCategories(TypedDict):
    """Fixed compatibility categories in the report schema."""

    tools: CategoryCompatibility
    resources: CategoryCompatibility
    resource_templates: CategoryCompatibility
    prompts: CategoryCompatibility


class CompatibilitySummary(TypedDict):
    """Public-surface compatibility results."""

    old_surface_is_subset: bool
    new_modes_equal: bool
    categories: CompatibilityCategories


class ArtifactContinuitySummary(TypedDict):
    """Sanitized artifact continuity results."""

    ok: bool
    manifest_readable: bool
    manifest_run_id_matches: bool
    contact_sheet_readable: bool
    content_unchanged: bool
    contact_sheet_sha256: str | None


class FailureReport(TypedDict):
    """Fixed-shape bounded failure evidence."""

    code: FailureCode
    scope: str
    missing_count: int | None
    missing_sha256: str | None
    remediation: str


class UpgradeProofReport(TypedDict):
    """Strict serialized schema for published upgrade evidence."""

    schema_version: Literal["albumentationsx-mcp/published-upgrade-proof/v1"]
    package: str | None
    from_version: str | None
    to_version: str | None
    observed_on: str | None
    status: ReportStatus
    matrix: list[ProtocolSummary]
    compatibility: CompatibilitySummary
    artifact_continuity: ArtifactContinuitySummary
    failures: list[FailureReport]


@dataclass(frozen=True)
class PublicSurface:
    """Canonical public MCP identifiers using sorted set semantics.

    Duplicate identifiers are intentionally discarded. Direct construction and
    :meth:`build` both canonicalize every category to a sorted tuple.
    """

    tools: tuple[str, ...]
    resources: tuple[str, ...]
    resource_templates: tuple[str, ...]
    prompts: tuple[str, ...]

    def __post_init__(self) -> None:
        """Canonicalize values supplied through the direct constructor."""
        object.__setattr__(self, "tools", _canonical(self.tools))
        object.__setattr__(self, "resources", _canonical(self.resources))
        object.__setattr__(self, "resource_templates", _canonical(self.resource_templates))
        object.__setattr__(self, "prompts", _canonical(self.prompts))

    @classmethod
    def build(
        cls,
        *,
        tools: Iterable[str],
        resources: Iterable[str],
        resource_templates: Iterable[str],
        prompts: Iterable[str],
    ) -> PublicSurface:
        """Build a canonical surface; each category is treated as a set."""
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
) -> UpgradeProofReport:
    """Build deterministic, privacy-safe evidence without I/O or ambient state."""
    failures: list[FailureReport] = []

    safe_package = package if _is_evidence_package(package) else None
    if safe_package is None:
        failures.append(
            _failure(
                code="package_invalid",
                scope="package",
                remediation="Use the normalized albumentationsx-mcp package name.",
            )
        )

    parsed_from_version = _parse_public_release(from_version)
    safe_from_version = from_version if parsed_from_version is not None else None
    if safe_from_version is None:
        failures.append(
            _failure(
                code="version_invalid",
                scope="from_version",
                remediation="Use an exact three-part public release version such as 1.21.0.",
            )
        )

    parsed_to_version = _parse_public_release(to_version)
    safe_to_version = to_version if parsed_to_version is not None else None
    if safe_to_version is None:
        failures.append(
            _failure(
                code="version_invalid",
                scope="to_version",
                remediation="Use an exact three-part public release version such as 1.21.0.",
            )
        )
    if parsed_from_version is not None and parsed_to_version is not None and parsed_to_version <= parsed_from_version:
        failures.append(
            _failure(
                code="upgrade_version_order_invalid",
                scope="from_version,to_version",
                remediation="Use a to_version that is strictly newer than from_version.",
            )
        )

    safe_observed_on = observed_on if _is_iso_calendar_date(observed_on) else None
    if safe_observed_on is None:
        failures.append(
            _failure(
                code="observed_on_invalid",
                scope="observed_on",
                remediation="Provide observed_on as a valid ISO calendar date in YYYY-MM-DD form.",
            )
        )

    row_specs: tuple[tuple[MatrixRole, ProtocolObservation, str | None], ...] = (
        ("from_legacy", from_legacy, safe_from_version),
        ("to_legacy", to_legacy, safe_to_version),
        ("to_modern", to_modern, safe_to_version),
    )
    matrix: list[ProtocolSummary] = []
    for role, row, expected_report_version in row_specs:
        summary, row_failures = _protocol_summary(
            role=role,
            row=row,
            expected_report_version=expected_report_version,
        )
        matrix.append(summary)
        failures.extend(row_failures)

    compatibility, compatibility_failures = _compatibility_summary(
        old=from_legacy.surface,
        new=to_legacy.surface,
        modern=to_modern.surface,
    )
    failures.extend(compatibility_failures)

    artifact_summary, artifact_failures = _artifact_summary(artifact)
    failures.extend(artifact_failures)

    status: ReportStatus = "pass" if not failures else "fail"
    return {
        "schema_version": _SCHEMA_VERSION,
        "package": safe_package,
        "from_version": safe_from_version,
        "to_version": safe_to_version,
        "observed_on": safe_observed_on,
        "status": status,
        "matrix": matrix,
        "compatibility": compatibility,
        "artifact_continuity": artifact_summary,
        "failures": failures,
    }


def _protocol_summary(
    *,
    role: MatrixRole,
    row: ProtocolObservation,
    expected_report_version: str | None,
) -> tuple[ProtocolSummary, list[FailureReport]]:
    failures: list[FailureReport] = []
    server_version_valid = _parse_public_release(row.server_version) is not None
    observed_server_version_valid = _parse_public_release(row.observed_server_version) is not None
    client_mode_valid = _is_supported_mode(row.client_mode)
    expected_protocol_valid = _is_supported_protocol(row.expected_protocol)
    negotiated_protocol_valid = _is_supported_protocol(row.negotiated_protocol)

    observations = (
        (
            "server_version",
            server_version_valid,
            "Use an exact three-part public release version such as 1.21.0.",
        ),
        (
            "observed_server_version",
            observed_server_version_valid,
            "Use an exact three-part public release version such as 1.21.0.",
        ),
        (
            "client_mode",
            client_mode_valid,
            "Use the recognized legacy or modern HTTP conformance client mode.",
        ),
        (
            "expected_protocol",
            expected_protocol_valid,
            "Use a supported ISO-date MCP protocol version.",
        ),
        (
            "negotiated_protocol",
            negotiated_protocol_valid,
            "Use a supported ISO-date MCP protocol version.",
        ),
    )
    for field, valid, remediation in observations:
        if not valid:
            failures.append(
                _failure(
                    code="observation_invalid",
                    scope=f"{role}.{field}",
                    remediation=remediation,
                )
            )

    mode_role_ok = client_mode_valid and row.client_mode == _expected_mode(role)
    if client_mode_valid and not mode_role_ok:
        failures.append(
            _failure(
                code="row_mode_mismatch",
                scope=role,
                remediation="Use legacy mode for legacy rows and the current modern mode for the modern row.",
            )
        )

    role_version_ok = (
        server_version_valid and expected_report_version is not None and row.server_version == expected_report_version
    )
    if server_version_valid and expected_report_version is not None and not role_version_ok:
        failures.append(
            _failure(
                code="row_version_mismatch",
                scope=role,
                remediation="Match each matrix row server version to its from_version or to_version role.",
            )
        )

    observed_server_version_ok = (
        server_version_valid and observed_server_version_valid and row.server_version == row.observed_server_version
    )
    if server_version_valid and observed_server_version_valid and not observed_server_version_ok:
        failures.append(
            _failure(
                code="server_version_mismatch",
                scope=role,
                remediation="Verify the uvx package pin and the published distribution metadata.",
            )
        )
    server_version_ok = role_version_ok and observed_server_version_ok

    protocol_role_ok = (
        expected_protocol_valid
        and negotiated_protocol_valid
        and row.expected_protocol == _expected_protocol(role)
        and row.negotiated_protocol == _expected_protocol(role)
    )
    if expected_protocol_valid and negotiated_protocol_valid and not protocol_role_ok:
        failures.append(
            _failure(
                code="row_protocol_mismatch",
                scope=role,
                remediation="Use the legacy protocol for legacy rows and the current protocol for the modern row.",
            )
        )

    protocol_agreement_ok = (
        expected_protocol_valid and negotiated_protocol_valid and row.expected_protocol == row.negotiated_protocol
    )
    if expected_protocol_valid and negotiated_protocol_valid and not protocol_agreement_ok:
        failures.append(
            _failure(
                code="protocol_negotiation_failed",
                scope=role,
                remediation="Verify the selected client mode and published server SDK compatibility.",
            )
        )
    protocol_ok = protocol_role_ok and protocol_agreement_ok

    summary: ProtocolSummary = {
        "role": role,
        "server_version": row.server_version if server_version_valid else None,
        "observed_server_version": row.observed_server_version if observed_server_version_valid else None,
        "client_mode": row.client_mode if client_mode_valid else None,
        "expected_protocol": row.expected_protocol if expected_protocol_valid else None,
        "negotiated_protocol": row.negotiated_protocol if negotiated_protocol_valid else None,
        "server_version_ok": server_version_ok,
        "protocol_ok": protocol_ok,
        "ok": mode_role_ok and server_version_ok and protocol_ok,
        "surface": _surface_summaries(row.surface),
    }
    return summary, failures


def _compatibility_summary(
    *,
    old: PublicSurface,
    new: PublicSurface,
    modern: PublicSurface,
) -> tuple[CompatibilitySummary, list[FailureReport]]:
    tools, tools_failure = _category_compatibility("tools", old.tools, new.tools)
    resources, resources_failure = _category_compatibility("resources", old.resources, new.resources)
    resource_templates, resource_templates_failure = _category_compatibility(
        "resource_templates",
        old.resource_templates,
        new.resource_templates,
    )
    prompts, prompts_failure = _category_compatibility("prompts", old.prompts, new.prompts)
    failures = [
        failure
        for failure in (tools_failure, resources_failure, resource_templates_failure, prompts_failure)
        if failure is not None
    ]

    categories: CompatibilityCategories = {
        "tools": tools,
        "resources": resources,
        "resource_templates": resource_templates,
        "prompts": prompts,
    }
    old_surface_is_subset = tools["ok"] and resources["ok"] and resource_templates["ok"] and prompts["ok"]
    new_modes_equal = new == modern
    if not new_modes_equal:
        failures.append(
            _failure(
                code="new_mode_surface_mismatch",
                scope="to_version",
                remediation="Register the same capability profile for legacy and modern protocol modes.",
            )
        )

    return {
        "old_surface_is_subset": old_surface_is_subset,
        "new_modes_equal": new_modes_equal,
        "categories": categories,
    }, failures


def _category_compatibility(
    category: SurfaceCategory,
    old_identifiers: tuple[str, ...],
    new_identifiers: tuple[str, ...],
) -> tuple[CategoryCompatibility, FailureReport | None]:
    missing = tuple(sorted(set(old_identifiers) - set(new_identifiers)))
    missing_summary = _surface_summary(missing)
    report: CategoryCompatibility = {
        "ok": not missing,
        "old": _surface_summary(old_identifiers),
        "new": _surface_summary(new_identifiers),
        "missing_count": missing_summary["count"],
        "missing_sha256": missing_summary["sha256"],
    }
    if not missing:
        return report, None
    return report, _failure(
        code="surface_removed",
        scope=category,
        missing_count=missing_summary["count"],
        missing_sha256=missing_summary["sha256"],
        remediation="Restore the published identifier or document and version a breaking change.",
    )


def _artifact_summary(
    artifact: ArtifactContinuity,
) -> tuple[ArtifactContinuitySummary, list[FailureReport]]:
    checks = (
        ("manifest_readable", artifact.manifest_readable is True),
        ("manifest_run_id_matches", artifact.manifest_run_id_matches is True),
        ("contact_sheet_readable", artifact.contact_sheet_readable is True),
        ("content_unchanged", artifact.content_unchanged is True),
    )
    failures: list[FailureReport] = []
    for field, ok in checks:
        if not ok:
            failures.append(
                _failure(
                    code="artifact_continuity_failed",
                    scope=field,
                    remediation="Inspect manifest and artifact resource compatibility before releasing an upgrade.",
                )
            )

    hash_ok = _is_lower_sha256(artifact.contact_sheet_sha256)
    if not hash_ok:
        failures.append(
            _failure(
                code="artifact_sha256_invalid",
                scope="contact_sheet_sha256",
                remediation="Provide the lowercase SHA-256 digest of the verified contact sheet.",
            )
        )

    summary: ArtifactContinuitySummary = {
        "ok": all(ok for _, ok in checks) and hash_ok,
        "manifest_readable": artifact.manifest_readable is True,
        "manifest_run_id_matches": artifact.manifest_run_id_matches is True,
        "contact_sheet_readable": artifact.contact_sheet_readable is True,
        "content_unchanged": artifact.content_unchanged is True,
        "contact_sheet_sha256": artifact.contact_sheet_sha256 if hash_ok else None,
    }
    return summary, failures


def _surface_summaries(surface: PublicSurface) -> SurfaceSummaryByCategory:
    return {
        "tools": _surface_summary(surface.tools),
        "resources": _surface_summary(surface.resources),
        "resource_templates": _surface_summary(surface.resource_templates),
        "prompts": _surface_summary(surface.prompts),
    }


def _surface_summary(identifiers: Iterable[str]) -> SurfaceSummary:
    canonical = _canonical(identifiers)
    return {"count": len(canonical), "sha256": _digest(canonical)}


def _canonical(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        message = "public identifier iterable must not be a plain string"
        raise TypeError(message)
    try:
        identifiers = tuple(values)
    except TypeError:
        message = "public identifiers must be provided as an iterable"
        raise TypeError(message) from None

    for identifier in identifiers:
        if not isinstance(identifier, str):
            message = "public identifiers must be strings"
            raise TypeError(message)
        if _has_control_character(identifier):
            message = "public identifiers must not contain control characters"
            raise ValueError(message)
        try:
            identifier.encode("utf-8")
        except UnicodeEncodeError:
            message = "public identifiers must be valid UTF-8"
            raise ValueError(message) from None
    return tuple(sorted(set(identifiers)))


def _digest(values: Iterable[str]) -> str:
    canonical = _canonical(values)
    payload = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_evidence_package(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and _NORMALIZED_PACKAGE_NAME.fullmatch(value) is not None and value == _PACKAGE_NAME


def _parse_public_release(value: object) -> Version | None:
    if (
        not isinstance(value, str)
        or len(value) > _MAX_RELEASE_LENGTH
        or _PUBLIC_RELEASE_VERSION.fullmatch(value) is None
    ):
        return None
    try:
        return Version(value)
    except InvalidVersion:
        return None


def _is_supported_mode(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and value in _SUPPORTED_MODES


def _is_supported_protocol(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and _ISO_DATE.fullmatch(value) is not None and value in _SUPPORTED_PROTOCOLS


def _expected_mode(role: MatrixRole) -> str:
    return _MODERN_MODE if role == "to_modern" else _LEGACY_MODE


def _expected_protocol(role: MatrixRole) -> str:
    return _MODERN_PROTOCOL if role == "to_modern" else _LEGACY_PROTOCOL


def _is_iso_calendar_date(value: object) -> TypeGuard[str]:
    if not isinstance(value, str) or _ISO_DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_lower_sha256(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and _LOWER_SHA256.fullmatch(value) is not None


def _has_control_character(value: str) -> bool:
    return any(unicodedata.category(character) == "Cc" for character in value)


def _failure(
    *,
    code: FailureCode,
    scope: str,
    remediation: str,
    missing_count: int | None = None,
    missing_sha256: str | None = None,
) -> FailureReport:
    return {
        "code": code,
        "scope": scope,
        "missing_count": missing_count,
        "missing_sha256": missing_sha256,
        "remediation": remediation,
    }
