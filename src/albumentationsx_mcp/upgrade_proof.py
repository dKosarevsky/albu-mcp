"""Pure compatibility evidence for published AlbumentationsX MCP upgrades."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass
from datetime import date
from typing import Final, Literal, TypeAlias, TypedDict, TypeGuard, TypeVar, cast

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
_PUBLIC_RELEASE_VERSION: Final = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
_ISO_DATE: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_LOWER_SHA256: Final = re.compile(r"[0-9a-f]{64}\Z")
_MAX_SURFACE_COUNT: Final = 4096
_MAX_FAILURES: Final = 64
_MAX_FAILURE_SCOPE_LENGTH: Final = 128
_MAX_REMEDIATION_LENGTH: Final = 512
_EMPTY_SURFACE_SHA256: Final = hashlib.sha256(b"[]").hexdigest()
_ValidatedT = TypeVar("_ValidatedT")

ReportStatus: TypeAlias = Literal["pass", "fail"]
MatrixRole: TypeAlias = Literal["from_legacy", "to_legacy", "to_modern"]
SurfaceCategory: TypeAlias = Literal["tools", "resources", "resource_templates", "prompts"]
FailureCode: TypeAlias = Literal[
    "advertised_server_version_invalid",
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
_MATRIX_ROLES: Final[tuple[MatrixRole, ...]] = ("from_legacy", "to_legacy", "to_modern")
_SURFACE_CATEGORIES: Final[tuple[SurfaceCategory, ...]] = (
    "tools",
    "resources",
    "resource_templates",
    "prompts",
)
_FAILURE_CODES: Final = frozenset(
    {
        "advertised_server_version_invalid",
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
    }
)


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
    advertised_server_version: str | None
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


_REPORT_KEYS: Final = frozenset(UpgradeProofReport.__annotations__)
_PROTOCOL_KEYS: Final = frozenset(ProtocolSummary.__annotations__)
_SURFACE_SUMMARY_KEYS: Final = frozenset(SurfaceSummary.__annotations__)
_COMPATIBILITY_KEYS: Final = frozenset(CompatibilitySummary.__annotations__)
_CATEGORY_COMPATIBILITY_KEYS: Final = frozenset(CategoryCompatibility.__annotations__)
_ARTIFACT_KEYS: Final = frozenset(ArtifactContinuitySummary.__annotations__)
_FAILURE_KEYS: Final = frozenset(FailureReport.__annotations__)
_ARTIFACT_FLAG_FIELDS: Final = (
    "manifest_readable",
    "manifest_run_id_matches",
    "contact_sheet_readable",
    "content_unchanged",
)


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
    advertised_server_version: str
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


@dataclass(frozen=True)
class _ProtocolEvidence:
    server_version: str | None
    observed_server_version: str | None
    advertised_server_version: str | None
    client_mode: str | None
    expected_protocol: str | None
    negotiated_protocol: str | None
    surface: SurfaceSummaryByCategory


@dataclass(frozen=True)
class _ArtifactEvidence:
    manifest_readable: bool
    manifest_run_id_matches: bool
    contact_sheet_readable: bool
    content_unchanged: bool
    contact_sheet_sha256: str | None


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


class _PublicationReportInvalid(ValueError):  # noqa: N818 - concise private validation sentinel.
    pass


def validate_upgrade_proof_report(
    report: object,
    *,
    expected_package: str,
    expected_from_version: str,
    expected_to_version: str,
    expected_observed_on: str,
) -> UpgradeProofReport:
    """Return a detached canonical report only when all publication invariants hold."""
    try:
        return _validate_upgrade_proof_report(
            report,
            expected_package=expected_package,
            expected_from_version=expected_from_version,
            expected_to_version=expected_to_version,
            expected_observed_on=expected_observed_on,
        )
    except _PublicationReportInvalid:
        message = "published upgrade proof report is invalid"
        raise ValueError(message) from None


def _validate_upgrade_proof_report(
    report: object,
    *,
    expected_package: str,
    expected_from_version: str,
    expected_to_version: str,
    expected_observed_on: str,
) -> UpgradeProofReport:
    parsed_from = _parse_public_release(expected_from_version)
    parsed_to = _parse_public_release(expected_to_version)
    if (
        not _is_exact_string(expected_package)
        or not _is_exact_string(expected_from_version)
        or not _is_exact_string(expected_to_version)
        or not _is_exact_string(expected_observed_on)
        or expected_package != _PACKAGE_NAME
        or parsed_from is None
        or parsed_to is None
        or parsed_to <= parsed_from
        or not _is_iso_calendar_date(expected_observed_on)
    ):
        raise _PublicationReportInvalid

    data = _exact_dict(report, _REPORT_KEYS)
    expected_metadata = {
        "schema_version": _SCHEMA_VERSION,
        "package": expected_package,
        "from_version": expected_from_version,
        "to_version": expected_to_version,
        "observed_on": expected_observed_on,
    }
    for field, expected in expected_metadata.items():
        _require_exact_string(data[field], expected)
    status = cast("ReportStatus", _require_string_choice(data["status"], {"pass", "fail"}))

    raw_matrix = data["matrix"]
    if type(raw_matrix) is not list or len(raw_matrix) != len(_MATRIX_ROLES):
        raise _PublicationReportInvalid
    matrix: list[ProtocolSummary] = []
    expected_failures: list[FailureReport] = []
    for role, raw_row in zip(_MATRIX_ROLES, raw_matrix, strict=True):
        expected_version = expected_from_version if role == "from_legacy" else expected_to_version
        row, row_failures = _validate_protocol_report_row(
            raw_row,
            expected_role=role,
            expected_version=expected_version,
        )
        matrix.append(row)
        expected_failures.extend(row_failures)

    compatibility, compatibility_failures = _validate_compatibility_report(data["compatibility"], matrix)
    expected_failures.extend(compatibility_failures)
    artifact, artifact_failures = _validate_artifact_report(data["artifact_continuity"])
    expected_failures.extend(artifact_failures)
    failures = _validate_failure_reports(data["failures"])

    expected_status: ReportStatus = "pass" if not expected_failures else "fail"
    if status != expected_status or failures != expected_failures:
        raise _PublicationReportInvalid

    return {
        "schema_version": _SCHEMA_VERSION,
        "package": expected_package,
        "from_version": expected_from_version,
        "to_version": expected_to_version,
        "observed_on": expected_observed_on,
        "status": expected_status,
        "matrix": matrix,
        "compatibility": compatibility,
        "artifact_continuity": artifact,
        "failures": failures,
    }


def _validate_protocol_report_row(
    value: object,
    *,
    expected_role: MatrixRole,
    expected_version: str,
) -> tuple[ProtocolSummary, list[FailureReport]]:
    data = _exact_dict(value, _PROTOCOL_KEYS)
    if type(data["role"]) is not str or data["role"] != expected_role:
        raise _PublicationReportInvalid
    evidence = _ProtocolEvidence(
        server_version=_nullable_public_release(data["server_version"]),
        observed_server_version=_nullable_public_release(data["observed_server_version"]),
        advertised_server_version=_nullable_public_release(data["advertised_server_version"]),
        client_mode=_nullable_supported_mode(data["client_mode"]),
        expected_protocol=_nullable_supported_protocol(data["expected_protocol"]),
        negotiated_protocol=_nullable_supported_protocol(data["negotiated_protocol"]),
        surface=_validate_surface_summaries(data["surface"]),
    )
    summary, failures = _derive_protocol_summary(
        role=expected_role,
        evidence=evidence,
        expected_report_version=expected_version,
    )
    if any(_strict_bool(data[field]) is not summary[field] for field in ("server_version_ok", "protocol_ok", "ok")):
        raise _PublicationReportInvalid
    return summary, failures


def _validate_compatibility_report(
    value: object,
    matrix: list[ProtocolSummary],
) -> tuple[CompatibilitySummary, list[FailureReport]]:
    data = _exact_dict(value, _COMPATIBILITY_KEYS)
    raw_categories = _exact_dict(data["categories"], frozenset(_SURFACE_CATEGORIES))
    old_surface = matrix[0]["surface"]
    new_surface = matrix[1]["surface"]
    modern_surface = matrix[2]["surface"]
    parsed_categories: dict[str, CategoryCompatibility] = {}
    for category in _SURFACE_CATEGORIES:
        parsed_categories[category] = _validate_category_compatibility(
            raw_categories[category],
            expected_old=old_surface[category],
            expected_new=new_surface[category],
        )
    categories = cast("CompatibilityCategories", parsed_categories)
    summary, failures = _derive_compatibility_summary(
        categories,
        new_modes_equal=all(new_surface[category] == modern_surface[category] for category in _SURFACE_CATEGORIES),
    )
    if (
        _strict_bool(data["old_surface_is_subset"]) is not summary["old_surface_is_subset"]
        or _strict_bool(data["new_modes_equal"]) is not summary["new_modes_equal"]
    ):
        raise _PublicationReportInvalid
    return summary, failures


def _validate_category_compatibility(
    value: object,
    *,
    expected_old: SurfaceSummary,
    expected_new: SurfaceSummary,
) -> CategoryCompatibility:
    data = _exact_dict(value, _CATEGORY_COMPATIBILITY_KEYS)
    old = _validate_surface_summary(data["old"])
    new = _validate_surface_summary(data["new"])
    missing_count = _bounded_count(data["missing_count"])
    missing_sha256 = _lower_sha256(data["missing_sha256"])
    ok = _strict_bool(data["ok"])
    expected_ok = missing_count == 0
    if old != expected_old or new != expected_new or ok is not expected_ok:
        raise _PublicationReportInvalid
    if missing_count == 0:
        if missing_sha256 != _EMPTY_SURFACE_SHA256:
            raise _PublicationReportInvalid
    elif (
        missing_count > old["count"]
        or old["count"] - missing_count > new["count"]
        or missing_sha256 == _EMPTY_SURFACE_SHA256
    ):
        raise _PublicationReportInvalid

    return {
        "ok": ok,
        "old": old,
        "new": new,
        "missing_count": missing_count,
        "missing_sha256": missing_sha256,
    }


def _validate_artifact_report(value: object) -> tuple[ArtifactContinuitySummary, list[FailureReport]]:
    data = _exact_dict(value, _ARTIFACT_KEYS)
    evidence = _ArtifactEvidence(
        manifest_readable=_strict_bool(data["manifest_readable"]),
        manifest_run_id_matches=_strict_bool(data["manifest_run_id_matches"]),
        contact_sheet_readable=_strict_bool(data["contact_sheet_readable"]),
        content_unchanged=_strict_bool(data["content_unchanged"]),
        contact_sheet_sha256=_nullable_lower_sha256(data["contact_sheet_sha256"]),
    )
    summary, failures = _derive_artifact_summary(evidence)
    if _strict_bool(data["ok"]) is not summary["ok"]:
        raise _PublicationReportInvalid
    return summary, failures


def _validate_failure_reports(value: object) -> list[FailureReport]:
    if type(value) is not list or len(value) > _MAX_FAILURES:
        raise _PublicationReportInvalid
    failures: list[FailureReport] = []
    for raw_failure in value:
        data = _exact_dict(raw_failure, _FAILURE_KEYS)
        failures.append(
            {
                "code": cast("FailureCode", _require_string_choice(data["code"], _FAILURE_CODES)),
                "scope": _bounded_safe_string(data["scope"], maximum=_MAX_FAILURE_SCOPE_LENGTH),
                "missing_count": _nullable_bounded_count(data["missing_count"]),
                "missing_sha256": _nullable_lower_sha256(data["missing_sha256"]),
                "remediation": _bounded_safe_string(
                    data["remediation"],
                    maximum=_MAX_REMEDIATION_LENGTH,
                ),
            }
        )
    return failures


def _validate_surface_summaries(value: object) -> SurfaceSummaryByCategory:
    data = _exact_dict(value, frozenset(_SURFACE_CATEGORIES))
    return cast(
        "SurfaceSummaryByCategory",
        {category: _validate_surface_summary(data[category]) for category in _SURFACE_CATEGORIES},
    )


def _validate_surface_summary(value: object) -> SurfaceSummary:
    data = _exact_dict(value, _SURFACE_SUMMARY_KEYS)
    count = _bounded_count(data["count"])
    sha256 = _lower_sha256(data["sha256"])
    if (count == 0) is not (sha256 == _EMPTY_SURFACE_SHA256):
        raise _PublicationReportInvalid
    return {"count": count, "sha256": sha256}


def _exact_dict(value: object, keys: frozenset[str]) -> dict[str, object]:
    if type(value) is not dict or len(value) != len(keys) or set(value) != keys:
        raise _PublicationReportInvalid
    return cast("dict[str, object]", value)


def _strict_bool(value: object) -> bool:
    if type(value) is not bool:
        raise _PublicationReportInvalid
    return value


def _is_exact_string(value: object) -> TypeGuard[str]:
    return type(value) is str


def _require_exact_string(value: object, expected: str) -> str:
    if not _is_exact_string(value) or value != expected:
        raise _PublicationReportInvalid
    return value


def _require_string_choice(value: object, choices: Collection[str]) -> str:
    if not _is_exact_string(value) or value not in choices:
        raise _PublicationReportInvalid
    return value


def _bounded_safe_string(value: object, *, maximum: int) -> str:
    if not _is_exact_string(value) or not 1 <= len(value) <= maximum or _has_control_character(value):
        raise _PublicationReportInvalid
    return value


def _bounded_count(value: object) -> int:
    if type(value) is not int or not 0 <= value <= _MAX_SURFACE_COUNT:
        raise _PublicationReportInvalid
    return value


def _nullable_bounded_count(value: object) -> int | None:
    return _nullable_validated(value, _bounded_count)


def _nullable_validated(value: object, validator: Callable[[object], _ValidatedT]) -> _ValidatedT | None:
    return None if value is None else validator(value)


def _validated_string(value: object, predicate: Callable[[str], bool]) -> str:
    if not _is_exact_string(value) or not predicate(value):
        raise _PublicationReportInvalid
    return value


def _lower_sha256(value: object) -> str:
    return _validated_string(value, _is_lower_sha256)


def _nullable_lower_sha256(value: object) -> str | None:
    return _nullable_validated(value, _lower_sha256)


def _nullable_public_release(value: object) -> str | None:
    return _nullable_validated(
        value,
        lambda candidate: _validated_string(candidate, lambda release: _parse_public_release(release) is not None),
    )


def _nullable_supported_mode(value: object) -> str | None:
    return _nullable_validated(value, lambda candidate: _validated_string(candidate, _is_supported_mode))


def _nullable_supported_protocol(value: object) -> str | None:
    return _nullable_validated(value, lambda candidate: _validated_string(candidate, _is_supported_protocol))


def _protocol_summary(
    *,
    role: MatrixRole,
    row: ProtocolObservation,
    expected_report_version: str | None,
) -> tuple[ProtocolSummary, list[FailureReport]]:
    evidence = _ProtocolEvidence(
        server_version=row.server_version if _parse_public_release(row.server_version) is not None else None,
        observed_server_version=(
            row.observed_server_version if _parse_public_release(row.observed_server_version) is not None else None
        ),
        advertised_server_version=(
            row.advertised_server_version if _parse_public_release(row.advertised_server_version) is not None else None
        ),
        client_mode=row.client_mode if _is_supported_mode(row.client_mode) else None,
        expected_protocol=row.expected_protocol if _is_supported_protocol(row.expected_protocol) else None,
        negotiated_protocol=row.negotiated_protocol if _is_supported_protocol(row.negotiated_protocol) else None,
        surface=_surface_summaries(row.surface),
    )
    return _derive_protocol_summary(
        role=role,
        evidence=evidence,
        expected_report_version=expected_report_version,
    )


def _derive_protocol_summary(
    *,
    role: MatrixRole,
    evidence: _ProtocolEvidence,
    expected_report_version: str | None,
) -> tuple[ProtocolSummary, list[FailureReport]]:
    failures: list[FailureReport] = []
    observations = (
        (
            "server_version",
            evidence.server_version,
            "Use an exact three-part public release version such as 1.21.0.",
        ),
        (
            "observed_server_version",
            evidence.observed_server_version,
            "Use an exact three-part public release version such as 1.21.0.",
        ),
        (
            "client_mode",
            evidence.client_mode,
            "Use the recognized legacy or modern HTTP conformance client mode.",
        ),
        (
            "expected_protocol",
            evidence.expected_protocol,
            "Use a supported ISO-date MCP protocol version.",
        ),
        (
            "negotiated_protocol",
            evidence.negotiated_protocol,
            "Use a supported ISO-date MCP protocol version.",
        ),
    )
    for field, observation, remediation in observations:
        if observation is None:
            failures.append(
                _failure(
                    code="observation_invalid",
                    scope=f"{role}.{field}",
                    remediation=remediation,
                )
            )

    if evidence.advertised_server_version is None:
        failures.append(
            _failure(
                code="advertised_server_version_invalid",
                scope=role,
                remediation="Require advertised MCP server metadata to use an exact three-part public release version.",
            )
        )

    mode_role_ok = evidence.client_mode is not None and evidence.client_mode == _expected_mode(role)
    if evidence.client_mode is not None and not mode_role_ok:
        failures.append(
            _failure(
                code="row_mode_mismatch",
                scope=role,
                remediation="Use legacy mode for legacy rows and the current modern mode for the modern row.",
            )
        )

    role_version_ok = (
        evidence.server_version is not None
        and expected_report_version is not None
        and evidence.server_version == expected_report_version
    )
    if evidence.server_version is not None and expected_report_version is not None and not role_version_ok:
        failures.append(
            _failure(
                code="row_version_mismatch",
                scope=role,
                remediation="Match each matrix row server version to its from_version or to_version role.",
            )
        )

    observed_server_version_ok = (
        evidence.server_version is not None
        and evidence.observed_server_version is not None
        and evidence.server_version == evidence.observed_server_version
    )
    if (
        evidence.server_version is not None
        and evidence.observed_server_version is not None
        and not observed_server_version_ok
    ):
        failures.append(
            _failure(
                code="server_version_mismatch",
                scope=role,
                remediation="Verify the uvx package pin and the published distribution metadata.",
            )
        )
    server_version_ok = role_version_ok and observed_server_version_ok

    protocol_role_ok = (
        evidence.expected_protocol is not None
        and evidence.negotiated_protocol is not None
        and evidence.expected_protocol == _expected_protocol(role)
        and evidence.negotiated_protocol == _expected_protocol(role)
    )
    if evidence.expected_protocol is not None and evidence.negotiated_protocol is not None and not protocol_role_ok:
        failures.append(
            _failure(
                code="row_protocol_mismatch",
                scope=role,
                remediation="Use the legacy protocol for legacy rows and the current protocol for the modern row.",
            )
        )

    protocol_agreement_ok = (
        evidence.expected_protocol is not None
        and evidence.negotiated_protocol is not None
        and evidence.expected_protocol == evidence.negotiated_protocol
    )
    if (
        evidence.expected_protocol is not None
        and evidence.negotiated_protocol is not None
        and not protocol_agreement_ok
    ):
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
        "server_version": evidence.server_version,
        "observed_server_version": evidence.observed_server_version,
        "advertised_server_version": evidence.advertised_server_version,
        "client_mode": evidence.client_mode,
        "expected_protocol": evidence.expected_protocol,
        "negotiated_protocol": evidence.negotiated_protocol,
        "server_version_ok": server_version_ok,
        "protocol_ok": protocol_ok,
        "ok": mode_role_ok and server_version_ok and evidence.advertised_server_version is not None and protocol_ok,
        "surface": evidence.surface,
    }
    return summary, failures


def _compatibility_summary(
    *,
    old: PublicSurface,
    new: PublicSurface,
    modern: PublicSurface,
) -> tuple[CompatibilitySummary, list[FailureReport]]:
    identifier_pairs = {
        "tools": (old.tools, new.tools),
        "resources": (old.resources, new.resources),
        "resource_templates": (old.resource_templates, new.resource_templates),
        "prompts": (old.prompts, new.prompts),
    }
    categories = cast(
        "CompatibilityCategories",
        {category: _category_compatibility(*identifier_pairs[category]) for category in _SURFACE_CATEGORIES},
    )
    return _derive_compatibility_summary(categories, new_modes_equal=new == modern)


def _derive_compatibility_summary(
    categories: CompatibilityCategories,
    *,
    new_modes_equal: bool,
) -> tuple[CompatibilitySummary, list[FailureReport]]:
    failures = [
        _failure(
            code="surface_removed",
            scope=category,
            missing_count=categories[category]["missing_count"],
            missing_sha256=categories[category]["missing_sha256"],
            remediation="Restore the published identifier or document and version a breaking change.",
        )
        for category in _SURFACE_CATEGORIES
        if not categories[category]["ok"]
    ]
    if not new_modes_equal:
        failures.append(
            _failure(
                code="new_mode_surface_mismatch",
                scope="to_version",
                remediation="Register the same capability profile for legacy and modern protocol modes.",
            )
        )

    return {
        "old_surface_is_subset": all(categories[category]["ok"] for category in _SURFACE_CATEGORIES),
        "new_modes_equal": new_modes_equal,
        "categories": categories,
    }, failures


def _category_compatibility(
    old_identifiers: tuple[str, ...],
    new_identifiers: tuple[str, ...],
) -> CategoryCompatibility:
    missing = tuple(sorted(set(old_identifiers) - set(new_identifiers)))
    missing_summary = _surface_summary(missing)
    return {
        "ok": not missing,
        "old": _surface_summary(old_identifiers),
        "new": _surface_summary(new_identifiers),
        "missing_count": missing_summary["count"],
        "missing_sha256": missing_summary["sha256"],
    }


def _artifact_summary(
    artifact: ArtifactContinuity,
) -> tuple[ArtifactContinuitySummary, list[FailureReport]]:
    return _derive_artifact_summary(
        _ArtifactEvidence(
            manifest_readable=artifact.manifest_readable is True,
            manifest_run_id_matches=artifact.manifest_run_id_matches is True,
            contact_sheet_readable=artifact.contact_sheet_readable is True,
            content_unchanged=artifact.content_unchanged is True,
            contact_sheet_sha256=(
                artifact.contact_sheet_sha256 if _is_lower_sha256(artifact.contact_sheet_sha256) else None
            ),
        )
    )


def _derive_artifact_summary(
    evidence: _ArtifactEvidence,
) -> tuple[ArtifactContinuitySummary, list[FailureReport]]:
    checks = (
        ("manifest_readable", evidence.manifest_readable),
        ("manifest_run_id_matches", evidence.manifest_run_id_matches),
        ("contact_sheet_readable", evidence.contact_sheet_readable),
        ("content_unchanged", evidence.content_unchanged),
    )
    failures = [
        _failure(
            code="artifact_continuity_failed",
            scope=field,
            remediation="Inspect manifest and artifact resource compatibility before releasing an upgrade.",
        )
        for field, ok in checks
        if not ok
    ]
    if evidence.contact_sheet_sha256 is None:
        failures.append(
            _failure(
                code="artifact_sha256_invalid",
                scope="contact_sheet_sha256",
                remediation="Provide the lowercase SHA-256 digest of the verified contact sheet.",
            )
        )

    summary: ArtifactContinuitySummary = {
        "ok": all(ok for _, ok in checks) and evidence.contact_sheet_sha256 is not None,
        "manifest_readable": evidence.manifest_readable,
        "manifest_run_id_matches": evidence.manifest_run_id_matches,
        "contact_sheet_readable": evidence.contact_sheet_readable,
        "content_unchanged": evidence.content_unchanged,
        "contact_sheet_sha256": evidence.contact_sheet_sha256,
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


def _parse_public_release(value: object) -> tuple[int, int, int] | None:
    if not isinstance(value, str) or len(value) > _MAX_RELEASE_LENGTH:
        return None
    match = _PUBLIC_RELEASE_VERSION.fullmatch(value)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


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
