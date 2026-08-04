"""Independent release, host-evidence, and adoption lifecycle status."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from typing_extensions import Self

from albumentationsx_mcp.upgrade_proof import (
    MAX_UPGRADE_PROOF_REPORT_BYTES,
    UpgradeProofReport,
    parse_upgrade_proof_report,
)

_EXPERIMENT_STATUSES = {"planned", "measuring", "complete", "stopped"}
_READY_RELEASE_STATUSES = {"passed", "published", "listed", "merged", "ready"}
_UNOBSERVED_RELEASE_STATUSES = {"not_observed", "unknown"}
_EMPTY_VERSION_ERROR = "version must not be empty"
_EMPTY_RELEASE_CHANNELS_ERROR = "release_channels must not be empty"
_DUPLICATE_RELEASE_CHANNELS_ERROR = "release channel ids must be unique"
_INVALID_EXPERIMENT_DATES_ERROR = "measurement_due must not precede baseline_date"
_PROTOCOL_COMPATIBILITY_ERROR = "protocol compatibility evidence is invalid"
_PROTOCOL_SCHEMA_VERSION = 1
_MAX_PROTOCOL_PATH_LENGTH = 512
_PROTOCOL_PACKAGE = "albumentationsx-mcp"
_PROTOCOL_STATUS_BASIS = "Published upgrade probe result only; this does not assert provenance."
_PROTOCOL_PROVENANCE = (
    "Local operator-run snapshot. No immutable public run or attestation is available; this evidence is not "
    "independently attested or provenance-verifiable."
)
_PROTOCOL_SCOPE = (
    "Streamable HTTP conformance and published-package artifact continuity. This is not real-host UI evidence."
)
_SAFE_LINK_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_MARKDOWN_INLINE_SPECIAL = re.compile(r"([\\`*_{}\[\]<>#!|])")


@dataclass(frozen=True, slots=True)
class _EvidenceFileIdentity:
    device: int
    inode: int
    size: int
    modified_ns: int
    changed_ns: int


@dataclass(frozen=True, slots=True)
class PublishedUpgradeExpectation:
    """Expected immutable report context for one published upgrade probe."""

    from_version: str
    to_version: str
    observed_on: str


@dataclass(frozen=True, slots=True)
class _EvidencePathContext:
    trusted_root: Path
    document_path: Path
    evidence_path: Path
    evidence_href: str


@dataclass(frozen=True, slots=True)
class _EvidenceBinding:
    path_context: _EvidencePathContext
    observed_on: str
    file_identity: _EvidenceFileIdentity


@dataclass(frozen=True, slots=True, init=False)
class ProtocolCompatibilityEvidence:
    """Immutable lifecycle claim derived from one canonical local evidence file."""

    schema_version: Literal[1]
    status: Literal["passed"]
    status_basis: str
    from_version: str
    to_version: str
    evidence_href: str
    evidence_sha256: str
    provenance: str
    scope: str
    binding: _EvidenceBinding = field(repr=False)

    def __new__(cls) -> Self:
        message = "protocol compatibility evidence must be loaded from a report"
        raise TypeError(message)


class _ProtocolCompatibilityError(ValueError):
    pass


def load_protocol_compatibility_evidence(
    *,
    evidence_path: Path,
    trusted_root: Path,
    document_path: Path,
    expectation: PublishedUpgradeExpectation,
) -> ProtocolCompatibilityEvidence:
    """Load one canonical passing report and bind it to its local document context."""
    try:
        context = _resolve_evidence_path_context(
            evidence_path=evidence_path,
            trusted_root=trusted_root,
            document_path=document_path,
        )
        raw_content, identity = _read_stable_evidence(context.evidence_path)
        if (
            _resolve_evidence_path_context(
                evidence_path=context.evidence_path,
                trusted_root=context.trusted_root,
                document_path=context.document_path,
            )
            != context
        ):
            raise _ProtocolCompatibilityError
        report = parse_upgrade_proof_report(
            raw_content,
            expected_package=_PROTOCOL_PACKAGE,
            expected_from_version=expectation.from_version,
            expected_to_version=expectation.to_version,
            expected_observed_on=expectation.observed_on,
        )
        if report["status"] != "pass":
            raise _ProtocolCompatibilityError
        return _new_protocol_compatibility_evidence(
            context=context,
            identity=identity,
            report=report,
            digest=hashlib.sha256(raw_content).hexdigest(),
        )
    except (AttributeError, OSError, OverflowError, RecursionError, RuntimeError, TypeError, ValueError):
        raise ValueError(_PROTOCOL_COMPATIBILITY_ERROR) from None


def _new_protocol_compatibility_evidence(
    *,
    context: _EvidencePathContext,
    identity: _EvidenceFileIdentity,
    report: UpgradeProofReport,
    digest: str,
) -> ProtocolCompatibilityEvidence:
    evidence = object.__new__(ProtocolCompatibilityEvidence)
    values: tuple[tuple[str, object], ...] = (
        ("schema_version", _PROTOCOL_SCHEMA_VERSION),
        ("status", "passed"),
        ("status_basis", _PROTOCOL_STATUS_BASIS),
        ("from_version", report["from_version"]),
        ("to_version", report["to_version"]),
        ("evidence_href", context.evidence_href),
        ("evidence_sha256", digest),
        ("provenance", _PROTOCOL_PROVENANCE),
        ("scope", _PROTOCOL_SCOPE),
        (
            "binding",
            _EvidenceBinding(
                path_context=context,
                observed_on=cast("str", report["observed_on"]),
                file_identity=identity,
            ),
        ),
    )
    for attribute, value in values:
        object.__setattr__(evidence, attribute, value)
    return evidence


def build_lifecycle_status(
    *,
    version: str,
    release_channels: Sequence[Mapping[str, str]],
    host_blockers: Sequence[Mapping[str, str]],
    experiment: Mapping[str, Any],
    protocol_compatibility: ProtocolCompatibilityEvidence | None = None,
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
        report["protocol_compatibility"] = _validate_protocol_compatibility_evidence(
            protocol_compatibility,
            release_version=version,
        )
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
    validated_protocol = (
        None
        if protocol is None
        else _validate_protocol_compatibility_evidence(protocol, release_version=release["version"])
    )
    protocol_section = "" if validated_protocol is None else _render_protocol_compatibility_markdown(validated_protocol)
    rendered = (
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
    if validated_protocol is not None:
        _validate_protocol_compatibility_evidence(validated_protocol, release_version=release["version"])
    return rendered


def _render_protocol_compatibility_markdown(
    protocol: ProtocolCompatibilityEvidence,
) -> str:
    upgrade = f"{protocol.from_version} -> {protocol.to_version}"
    return (
        "## Protocol Compatibility Evidence\n\n"
        f"Status: {_markdown_code_span(protocol.status)}\n\n"
        f"Status basis: {_escape_markdown_inline(protocol.status_basis)}\n\n"
        f"Published upgrade: {_markdown_code_span(upgrade)}\n\n"
        f"Evidence: [privacy-safe machine report]({protocol.evidence_href})\n\n"
        f"Evidence SHA-256: {_markdown_code_span(protocol.evidence_sha256)}\n\n"
        f"Provenance: {_escape_markdown_inline(protocol.provenance)}\n\n"
        f"Scope: {_escape_markdown_inline(protocol.scope)}\n\n"
    )


def _validate_protocol_compatibility_evidence(
    value: object,
    *,
    release_version: object,
) -> ProtocolCompatibilityEvidence:
    try:
        return _validated_protocol_compatibility_evidence(value, release_version=release_version)
    except (AttributeError, OSError, OverflowError, RecursionError, RuntimeError, TypeError, ValueError):
        raise ValueError(_PROTOCOL_COMPATIBILITY_ERROR) from None


def _validated_protocol_compatibility_evidence(
    value: object,
    *,
    release_version: object,
) -> ProtocolCompatibilityEvidence:
    if type(value) is not ProtocolCompatibilityEvidence:
        raise _ProtocolCompatibilityError
    evidence = value
    if evidence.schema_version != _PROTOCOL_SCHEMA_VERSION or evidence.status != "passed":
        raise _ProtocolCompatibilityError
    if evidence.status_basis != _PROTOCOL_STATUS_BASIS:
        raise _ProtocolCompatibilityError
    if evidence.provenance != _PROTOCOL_PROVENANCE or evidence.scope != _PROTOCOL_SCOPE:
        raise _ProtocolCompatibilityError
    if type(release_version) is not str or evidence.to_version != release_version:
        raise _ProtocolCompatibilityError
    bound_context = evidence.binding.path_context
    context = _resolve_evidence_path_context(
        evidence_path=bound_context.evidence_path,
        trusted_root=bound_context.trusted_root,
        document_path=bound_context.document_path,
    )
    if context != bound_context or context.evidence_href != evidence.evidence_href:
        raise _ProtocolCompatibilityError
    raw_content, identity = _read_stable_evidence(context.evidence_path)
    if identity != evidence.binding.file_identity:
        raise _ProtocolCompatibilityError
    if (
        _resolve_evidence_path_context(
            evidence_path=context.evidence_path,
            trusted_root=context.trusted_root,
            document_path=context.document_path,
        )
        != context
    ):
        raise _ProtocolCompatibilityError
    report = parse_upgrade_proof_report(
        raw_content,
        expected_package=_PROTOCOL_PACKAGE,
        expected_from_version=evidence.from_version,
        expected_to_version=evidence.to_version,
        expected_observed_on=evidence.binding.observed_on,
    )
    if report["status"] != "pass":
        raise _ProtocolCompatibilityError
    if (
        report["from_version"] != evidence.from_version
        or report["to_version"] != evidence.to_version
        or hashlib.sha256(raw_content).hexdigest() != evidence.evidence_sha256
    ):
        raise _ProtocolCompatibilityError
    return evidence


def _resolve_evidence_path_context(
    *,
    evidence_path: Path,
    trusted_root: Path,
    document_path: Path,
) -> _EvidencePathContext:
    root = trusted_root.resolve(strict=True)
    if not root.is_dir():
        raise _ProtocolCompatibilityError
    evidence = evidence_path.resolve(strict=True)
    evidence.relative_to(root)
    if not evidence.is_file():
        raise _ProtocolCompatibilityError

    document_parent = document_path.parent.resolve(strict=True)
    document_parent.relative_to(root)
    if not document_parent.is_dir():
        raise _ProtocolCompatibilityError
    document = document_parent / document_path.name
    try:
        document_metadata = document.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(document_metadata.st_mode) or not stat.S_ISREG(document_metadata.st_mode):
            raise _ProtocolCompatibilityError
        document = document.resolve(strict=True)
    document.relative_to(root)
    if document == evidence:
        raise _ProtocolCompatibilityError

    relative_href = os.path.relpath(evidence, start=document.parent).replace(os.sep, "/")
    return _EvidencePathContext(
        trusted_root=root,
        document_path=document,
        evidence_path=evidence,
        evidence_href=_validated_derived_evidence_href(relative_href),
    )


def _validated_derived_evidence_href(value: str) -> str:
    if not 1 <= len(value) <= _MAX_PROTOCOL_PATH_LENGTH:
        raise _ProtocolCompatibilityError
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise _ProtocolCompatibilityError
    parts = path.parts
    first_name = next((index for index, part in enumerate(parts) if part != ".."), len(parts))
    if first_name == len(parts) or any(part == ".." for part in parts[first_name:]):
        raise _ProtocolCompatibilityError
    if any(_SAFE_LINK_COMPONENT.fullmatch(part) is None for part in parts[first_name:]):
        raise _ProtocolCompatibilityError
    if not parts[-1].endswith(".json"):
        raise _ProtocolCompatibilityError
    return value


def _read_stable_evidence(path: Path) -> tuple[bytes, _EvidenceFileIdentity]:
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_UPGRADE_PROOF_REPORT_BYTES:
        raise _ProtocolCompatibilityError
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or not _same_evidence_file(before, opened):
            raise _ProtocolCompatibilityError
        chunks: list[bytes] = []
        remaining = MAX_UPGRADE_PROOF_REPORT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw_content = b"".join(chunks)
        after_read = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = path.lstat()
    if (
        len(raw_content) > MAX_UPGRADE_PROOF_REPORT_BYTES
        or not _same_evidence_file(opened, after_read)
        or not _same_evidence_file(after_read, after_path)
    ):
        raise _ProtocolCompatibilityError
    identity = _EvidenceFileIdentity(
        device=after_read.st_dev,
        inode=after_read.st_ino,
        size=after_read.st_size,
        modified_ns=after_read.st_mtime_ns,
        changed_ns=after_read.st_ctime_ns,
    )
    return raw_content, identity


def _same_evidence_file(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        stat.S_ISREG(left.st_mode)
        and stat.S_ISREG(right.st_mode)
        and left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
        and left.st_ctime_ns == right.st_ctime_ns
    )


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
    for required_field in ("campaign_id", "success_signal"):
        if not str(normalized.get(required_field, "")).strip():
            raise ValueError(f"{required_field} must not be empty")
    normalized["baseline_date"] = baseline.isoformat()
    normalized["measurement_due"] = measurement_due.isoformat()
    normalized.setdefault("post_url", None)
    return normalized
