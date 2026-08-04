"""Independent release, host-evidence, and adoption lifecycle status."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Literal, TypedDict, cast

_EXPERIMENT_STATUSES = {"planned", "measuring", "complete", "stopped"}
_READY_RELEASE_STATUSES = {"passed", "published", "listed", "merged", "ready"}
_UNOBSERVED_RELEASE_STATUSES = {"not_observed", "unknown"}
_EMPTY_VERSION_ERROR = "version must not be empty"
_EMPTY_RELEASE_CHANNELS_ERROR = "release_channels must not be empty"
_DUPLICATE_RELEASE_CHANNELS_ERROR = "release channel ids must be unique"
_INVALID_EXPERIMENT_DATES_ERROR = "measurement_due must not precede baseline_date"
_PROTOCOL_COMPATIBILITY_ERROR = "protocol compatibility evidence is invalid"
_PROTOCOL_SCHEMA_VERSION = 1
_MAX_PROTOCOL_VERSION_LENGTH = 128
_MAX_PROTOCOL_PATH_LENGTH = 512
_MAX_PROTOCOL_PROSE_LENGTH = 512
_PUBLIC_RELEASE_VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_JSON_PATH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*\.json\Z")
_MARKDOWN_INLINE_SPECIAL = re.compile(r"([\\`*_{}\[\]<>#!|])")


class ProtocolCompatibility(TypedDict):
    """Exact lifecycle schema for one approved protocol-compatibility report."""

    schema_version: Literal[1]
    status: Literal["passed"]
    status_basis: str
    from_version: str
    to_version: str
    evidence_path: str
    evidence_sha256: str
    provenance: str
    scope: str


_PROTOCOL_COMPATIBILITY_KEYS = frozenset(ProtocolCompatibility.__annotations__)


class _ProtocolCompatibilityError(ValueError):
    pass


def build_lifecycle_status(
    *,
    version: str,
    release_channels: Sequence[Mapping[str, str]],
    host_blockers: Sequence[Mapping[str, str]],
    experiment: Mapping[str, Any],
    protocol_compatibility: ProtocolCompatibility | None = None,
) -> dict[str, Any]:
    """Build independent status dimensions from committed public metadata."""
    if not version.strip():
        raise ValueError(_EMPTY_VERSION_ERROR)
    channels = [dict(channel) for channel in release_channels]
    if not channels:
        raise ValueError(_EMPTY_RELEASE_CHANNELS_ERROR)
    if len({channel["id"] for channel in channels}) != len(channels):
        raise ValueError(_DUPLICATE_RELEASE_CHANNELS_ERROR)

    normalized_experiment = _validate_experiment(experiment)
    blockers = [dict(blocker) for blocker in host_blockers]
    report: dict[str, Any] = {
        "schema_version": 1,
        "release_health": {
            "status": _release_health_status(channels),
            "version": version,
            "channels": channels,
        },
        "host_evidence": {
            "status": "complete" if not blockers else "partial",
            "unresolved_count": len(blockers),
            "blockers": blockers,
        },
        "adoption_experiment": normalized_experiment,
    }
    if protocol_compatibility is not None:
        report["protocol_compatibility"] = _validate_protocol_compatibility(protocol_compatibility)
    return report


def _release_health_status(channels: list[dict[str, str]]) -> str:
    statuses = {channel["status"] for channel in channels}
    if statuses <= _READY_RELEASE_STATUSES:
        return "published"
    if statuses - _READY_RELEASE_STATUSES - _UNOBSERVED_RELEASE_STATUSES:
        return "attention_required"
    if statuses & _UNOBSERVED_RELEASE_STATUSES:
        return "unknown"
    return "attention_required"


def render_lifecycle_status_markdown(
    report: Mapping[str, Any],
    *,
    docs_root: Path = Path("docs"),
    document_path: Path = Path("docs/STATUS.md"),
) -> str:
    """Render lifecycle dimensions without turning host gaps into release blockers."""
    release = report["release_health"]
    host = report["host_evidence"]
    experiment = report["adoption_experiment"]
    protocol = report.get("protocol_compatibility")
    channel_lines = "\n".join(
        f"| {channel['id']} | `{channel['status']}` | {channel['url']} |" for channel in release["channels"]
    )
    blocker_lines = (
        "\n".join(f"- `{blocker['code']}`: {blocker['summary']}" for blocker in host["blockers"]) or "- None"
    )
    protocol_section = (
        ""
        if protocol is None
        else _render_protocol_compatibility_markdown(
            _validate_protocol_compatibility(protocol),
            docs_root=docs_root,
            document_path=document_path,
        )
    )
    return (
        "# Project Lifecycle Status\n\n"
        "Release publication, host evidence, and adoption measurement are independent dimensions.\n\n"
        "## Release Health\n\n"
        f"Status: `{release['status']}`\n\nVersion: `{release['version']}`\n\n"
        "| Channel | Status | URL |\n| --- | --- | --- |\n"
        f"{channel_lines}\n\n"
        f"{protocol_section}"
        "## Host Evidence\n\n"
        f"Status: `{host['status']}`\n\nUnresolved observations: `{host['unresolved_count']}`\n\n"
        f"{blocker_lines}\n\n"
        "## Adoption Experiment\n\n"
        f"Campaign: `{experiment['campaign_id']}`\n\nStatus: `{experiment['status']}`\n\n"
        f"Baseline: `{experiment['baseline_date']}`\n\nMeasurement due: `{experiment['measurement_due']}`\n\n"
        f"Post URL: `{experiment['post_url'] or 'not_recorded'}`\n\n"
        f"Success signal: {experiment['success_signal']}\n"
    )


def _render_protocol_compatibility_markdown(
    protocol: ProtocolCompatibility,
    *,
    docs_root: Path,
    document_path: Path,
) -> str:
    evidence_path = _validated_evidence_link_context(
        protocol["evidence_path"],
        docs_root=docs_root,
        document_path=document_path,
    )
    upgrade = f"{protocol['from_version']} -> {protocol['to_version']}"
    return (
        "## Protocol Compatibility Evidence\n\n"
        f"Status: {_markdown_code_span(protocol['status'])}\n\n"
        f"Status basis: {_escape_markdown_inline(protocol['status_basis'])}\n\n"
        f"Published upgrade: {_markdown_code_span(upgrade)}\n\n"
        f"Evidence: [privacy-safe machine report]({evidence_path})\n\n"
        f"Evidence SHA-256: {_markdown_code_span(protocol['evidence_sha256'])}\n\n"
        f"Provenance: {_escape_markdown_inline(protocol['provenance'])}\n\n"
        f"Scope: {_escape_markdown_inline(protocol['scope'])}\n\n"
    )


def _validate_protocol_compatibility(value: object) -> ProtocolCompatibility:
    try:
        return _validated_protocol_compatibility(value)
    except _ProtocolCompatibilityError:
        raise ValueError(_PROTOCOL_COMPATIBILITY_ERROR) from None


def _validated_protocol_compatibility(value: object) -> ProtocolCompatibility:
    if type(value) is not dict or set(value) != _PROTOCOL_COMPATIBILITY_KEYS:
        raise _ProtocolCompatibilityError
    data = cast("dict[str, object]", value)
    if type(data["schema_version"]) is not int or data["schema_version"] != _PROTOCOL_SCHEMA_VERSION:
        raise _ProtocolCompatibilityError
    if type(data["status"]) is not str or data["status"] != "passed":
        raise _ProtocolCompatibilityError
    from_version = _validated_public_release(data["from_version"])
    to_version = _validated_public_release(data["to_version"])
    if to_version[1] <= from_version[1]:
        raise _ProtocolCompatibilityError
    digest = data["evidence_sha256"]
    if type(digest) is not str or _LOWER_SHA256.fullmatch(digest) is None:
        raise _ProtocolCompatibilityError
    evidence_path = _validated_json_path(data["evidence_path"])
    return {
        "schema_version": 1,
        "status": "passed",
        "status_basis": _validated_protocol_prose(data["status_basis"]),
        "from_version": from_version[0],
        "to_version": to_version[0],
        "evidence_path": evidence_path,
        "evidence_sha256": digest,
        "provenance": _validated_protocol_prose(data["provenance"]),
        "scope": _validated_protocol_prose(data["scope"]),
    }


def _validated_public_release(value: object) -> tuple[str, tuple[int, int, int]]:
    if type(value) is not str or len(value) > _MAX_PROTOCOL_VERSION_LENGTH:
        raise _ProtocolCompatibilityError
    match = _PUBLIC_RELEASE_VERSION.fullmatch(value)
    if match is None:
        raise _ProtocolCompatibilityError
    major, minor, patch = match.groups()
    return value, (int(major), int(minor), int(patch))


def _validated_json_path(value: object) -> str:
    if (
        type(value) is not str
        or not 1 <= len(value) <= _MAX_PROTOCOL_PATH_LENGTH
        or _SAFE_JSON_PATH.fullmatch(value) is None
        or PurePosixPath(value).as_posix() != value
    ):
        raise _ProtocolCompatibilityError
    return value


def _validated_protocol_prose(value: object) -> str:
    if (
        type(value) is not str
        or not 1 <= len(value) <= _MAX_PROTOCOL_PROSE_LENGTH
        or value.strip() != value
        or any(
            character in "\r\n\u2028\u2029" or unicodedata.category(character).startswith("C") for character in value
        )
    ):
        raise _ProtocolCompatibilityError
    return value


def _validated_evidence_link_context(
    evidence_path: str,
    *,
    docs_root: Path,
    document_path: Path,
) -> str:
    try:
        root = docs_root.resolve(strict=False)
        document = document_path.resolve(strict=False)
        document.relative_to(root)
        target = document.parent.joinpath(*PurePosixPath(evidence_path).parts).resolve(strict=False)
        target.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        raise ValueError(_PROTOCOL_COMPATIBILITY_ERROR) from None
    return evidence_path


def _escape_markdown_inline(value: str) -> str:
    return _MARKDOWN_INLINE_SPECIAL.sub(r"\\\1", value)


def _markdown_code_span(value: str) -> str:
    return f"`{value.replace('&', '&amp;').replace('`', '&#96;')}`"


def _validate_experiment(experiment: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(experiment)
    status = normalized.get("status")
    if status not in _EXPERIMENT_STATUSES:
        raise ValueError(f"unsupported adoption experiment status: {status}")
    baseline = date.fromisoformat(str(normalized["baseline_date"]))
    measurement_due = date.fromisoformat(str(normalized["measurement_due"]))
    if measurement_due < baseline:
        raise ValueError(_INVALID_EXPERIMENT_DATES_ERROR)
    for field in ("campaign_id", "success_signal"):
        if not str(normalized.get(field, "")).strip():
            raise ValueError(f"{field} must not be empty")
    normalized["baseline_date"] = baseline.isoformat()
    normalized["measurement_due"] = measurement_due.isoformat()
    normalized.setdefault("post_url", None)
    return normalized
