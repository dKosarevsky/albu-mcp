"""Canonical provenance for one public published-upgrade workflow artifact."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from typing import Final, Literal, TypedDict, cast

SCHEMA_VERSION: Final = "albumentationsx-mcp/published-upgrade-provenance/v1"
MAX_PUBLISHED_UPGRADE_PROVENANCE_BYTES: Final = 16_384
_INVALID_PROVENANCE: Final = "published upgrade provenance is invalid"
_EVIDENCE_CLASSIFICATION: Final = "public_workflow_machine_proof"
_STATUS: Final = "verified"
_VERIFICATION_METHODS: Final = frozenset({"downloaded_artifact", "workflow_output"})
_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_WORKFLOW_PATH = re.compile(r"\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml\Z")
_ARTIFACT_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_MAX_RUN_ID: Final = 99_999_999_999_999_999_999
_MAX_ARTIFACT_RETENTION_DAYS: Final = 90


class PublishedUpgradeProvenance(TypedDict):
    """Strict public-run binding for one published-upgrade evidence file."""

    artifact_file: str
    artifact_name: str
    artifact_retention_days: int
    evidence_classification: Literal["public_workflow_machine_proof"]
    evidence_sha256: str
    repository: str
    run_head_sha: str
    run_id: int
    run_url: str
    schema_version: Literal["albumentationsx-mcp/published-upgrade-provenance/v1"]
    status: Literal["verified"]
    verification_method: Literal["downloaded_artifact", "workflow_output"]
    verified_on: str
    workflow_path: str
    workflow_ref: str


_PROVENANCE_KEYS: Final = frozenset(PublishedUpgradeProvenance.__annotations__)


def build_published_upgrade_provenance(  # noqa: PLR0913
    *,
    evidence: bytes,
    repository: str,
    workflow_path: str,
    workflow_ref: str,
    run_id: int,
    run_head_sha: str,
    artifact_name: str,
    artifact_file: str,
    artifact_retention_days: int,
    verified_on: str,
    verification_method: str,
) -> PublishedUpgradeProvenance:
    """Build and validate one canonical public workflow provenance record."""
    provenance = cast(
        "PublishedUpgradeProvenance",
        {
            "artifact_file": artifact_file,
            "artifact_name": artifact_name,
            "artifact_retention_days": artifact_retention_days,
            "evidence_classification": _EVIDENCE_CLASSIFICATION,
            "evidence_sha256": hashlib.sha256(evidence).hexdigest(),
            "repository": repository,
            "run_head_sha": run_head_sha,
            "run_id": run_id,
            "run_url": _run_url(repository, run_id),
            "schema_version": SCHEMA_VERSION,
            "status": _STATUS,
            "verification_method": verification_method,
            "verified_on": verified_on,
            "workflow_path": workflow_path,
            "workflow_ref": workflow_ref,
        },
    )
    _validate_provenance(provenance)
    return provenance


def serialize_published_upgrade_provenance(provenance: PublishedUpgradeProvenance) -> str:
    """Serialize a validated provenance record in canonical JSON form."""
    try:
        _validate_provenance(provenance)
        return _serialize(provenance)
    except (OverflowError, TypeError, ValueError):
        raise ValueError(_INVALID_PROVENANCE) from None


def parse_published_upgrade_provenance(  # noqa: PLR0913
    content: bytes | str,
    *,
    expected_repository: str,
    expected_workflow_path: str,
    expected_artifact_name: str,
    expected_artifact_file: str,
    expected_evidence_sha256: str,
) -> PublishedUpgradeProvenance:
    """Parse canonical provenance and bind it to the expected public context."""
    try:
        return _parse_published_upgrade_provenance(
            content,
            expected_repository=expected_repository,
            expected_workflow_path=expected_workflow_path,
            expected_artifact_name=expected_artifact_name,
            expected_artifact_file=expected_artifact_file,
            expected_evidence_sha256=expected_evidence_sha256,
        )
    except (AttributeError, OverflowError, TypeError, UnicodeError, ValueError, json.JSONDecodeError):
        raise ValueError(_INVALID_PROVENANCE) from None


def _parse_published_upgrade_provenance(  # noqa: PLR0913
    content: bytes | str,
    *,
    expected_repository: str,
    expected_workflow_path: str,
    expected_artifact_name: str,
    expected_artifact_file: str,
    expected_evidence_sha256: str,
) -> PublishedUpgradeProvenance:
    raw = content.encode("utf-8") if isinstance(content, str) else content
    if not isinstance(raw, bytes) or len(raw) > MAX_PUBLISHED_UPGRADE_PROVENANCE_BYTES:
        raise ValueError
    text = raw.decode("utf-8")
    payload = json.loads(text)
    if not isinstance(payload, dict) or frozenset(payload) != _PROVENANCE_KEYS:
        raise ValueError
    provenance = cast("PublishedUpgradeProvenance", payload)
    _validate_provenance(provenance)
    if text != _serialize(provenance):
        raise ValueError
    if (
        provenance["repository"] != expected_repository
        or provenance["workflow_path"] != expected_workflow_path
        or provenance["artifact_name"] != expected_artifact_name
        or provenance["artifact_file"] != expected_artifact_file
        or provenance["evidence_sha256"] != expected_evidence_sha256
    ):
        raise ValueError
    return provenance


def _validate_provenance(provenance: PublishedUpgradeProvenance) -> None:
    if frozenset(provenance) != _PROVENANCE_KEYS:
        raise ValueError
    if provenance["schema_version"] != SCHEMA_VERSION:
        raise ValueError
    if provenance["status"] != _STATUS or provenance["evidence_classification"] != _EVIDENCE_CLASSIFICATION:
        raise ValueError

    _validate_run_fields(provenance)
    _validate_artifact_fields(provenance)
    _validate_verification_fields(provenance)


def _validate_run_fields(provenance: PublishedUpgradeProvenance) -> None:

    repository = provenance["repository"]
    workflow_path = provenance["workflow_path"]
    run_id = provenance["run_id"]
    if type(repository) is not str or _REPOSITORY.fullmatch(repository) is None:
        raise ValueError
    if type(workflow_path) is not str or _WORKFLOW_PATH.fullmatch(workflow_path) is None:
        raise ValueError
    if type(run_id) is not int or not 1 <= run_id <= _MAX_RUN_ID:
        raise ValueError
    if provenance["run_url"] != _run_url(repository, run_id):
        raise ValueError
    if type(provenance["run_head_sha"]) is not str or _SHA1.fullmatch(provenance["run_head_sha"]) is None:
        raise ValueError
    if provenance["workflow_ref"] != f"{repository}/{workflow_path}@refs/heads/main":
        raise ValueError


def _validate_artifact_fields(provenance: PublishedUpgradeProvenance) -> None:
    artifact_name = provenance["artifact_name"]
    artifact_file = provenance["artifact_file"]
    if type(artifact_name) is not str or _ARTIFACT_COMPONENT.fullmatch(artifact_name) is None:
        raise ValueError
    if (
        type(artifact_file) is not str
        or _ARTIFACT_COMPONENT.fullmatch(artifact_file) is None
        or not artifact_file.endswith(".json")
    ):
        raise ValueError
    retention_days = provenance["artifact_retention_days"]
    if type(retention_days) is not int or not 1 <= retention_days <= _MAX_ARTIFACT_RETENTION_DAYS:
        raise ValueError


def _validate_verification_fields(provenance: PublishedUpgradeProvenance) -> None:
    if type(provenance["evidence_sha256"]) is not str or _SHA256.fullmatch(provenance["evidence_sha256"]) is None:
        raise ValueError
    if provenance["verification_method"] not in _VERIFICATION_METHODS:
        raise ValueError
    verified_on = provenance["verified_on"]
    if type(verified_on) is not str or date.fromisoformat(verified_on).isoformat() != verified_on:
        raise ValueError


def _run_url(repository: str, run_id: int) -> str:
    return f"https://github.com/{repository}/actions/runs/{run_id}"


def _serialize(provenance: PublishedUpgradeProvenance) -> str:
    return json.dumps(provenance, allow_nan=False, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
