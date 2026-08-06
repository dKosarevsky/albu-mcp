from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from albumentationsx_mcp.published_provenance import (
    PublishedUpgradeProvenance,
    build_published_upgrade_provenance,
    parse_published_upgrade_provenance,
    serialize_published_upgrade_provenance,
)

_EVIDENCE = b'{"status":"pass"}\n'
_REPOSITORY = "dKosarevsky/albu-mcp"
_WORKFLOW_PATH = ".github/workflows/published-upgrade-proof.yml"
_WORKFLOW_REF = f"{_REPOSITORY}/{_WORKFLOW_PATH}@refs/heads/main"
_RUN_ID = 31_049_485_055
_RUN_HEAD_SHA = "8e185cb32a895a31fe3264b313372058fbfcea49"
_ARTIFACT_NAME = "published-upgrade-proof"
_ARTIFACT_FILE = "published-upgrade-proof.json"


def _provenance(**overrides: Any) -> PublishedUpgradeProvenance:
    values: dict[str, Any] = {
        "evidence": _EVIDENCE,
        "repository": _REPOSITORY,
        "workflow_path": _WORKFLOW_PATH,
        "workflow_ref": _WORKFLOW_REF,
        "run_id": _RUN_ID,
        "run_head_sha": _RUN_HEAD_SHA,
        "artifact_name": _ARTIFACT_NAME,
        "artifact_file": _ARTIFACT_FILE,
        "artifact_retention_days": 30,
        "verified_on": "2026-08-05",
        "verification_method": "downloaded_artifact",
    }
    values.update(overrides)
    return build_published_upgrade_provenance(**values)


def _parse(content: bytes | str, *, expected_sha256: str | None = None) -> PublishedUpgradeProvenance:
    return parse_published_upgrade_provenance(
        content,
        expected_repository=_REPOSITORY,
        expected_workflow_path=_WORKFLOW_PATH,
        expected_artifact_name=_ARTIFACT_NAME,
        expected_artifact_file=_ARTIFACT_FILE,
        expected_evidence_sha256=expected_sha256 or hashlib.sha256(_EVIDENCE).hexdigest(),
    )


def test_published_upgrade_provenance_binds_public_run_and_exact_evidence_bytes() -> None:
    provenance = _provenance()

    assert provenance == {
        "artifact_file": _ARTIFACT_FILE,
        "artifact_name": _ARTIFACT_NAME,
        "artifact_retention_days": 30,
        "evidence_classification": "public_workflow_machine_proof",
        "evidence_sha256": hashlib.sha256(_EVIDENCE).hexdigest(),
        "repository": _REPOSITORY,
        "run_head_sha": _RUN_HEAD_SHA,
        "run_id": _RUN_ID,
        "run_url": f"https://github.com/{_REPOSITORY}/actions/runs/{_RUN_ID}",
        "schema_version": "albumentationsx-mcp/published-upgrade-provenance/v1",
        "status": "verified",
        "verification_method": "downloaded_artifact",
        "verified_on": "2026-08-05",
        "workflow_path": _WORKFLOW_PATH,
        "workflow_ref": _WORKFLOW_REF,
    }


def test_published_upgrade_provenance_round_trips_canonical_json() -> None:
    provenance = _provenance()
    rendered = serialize_published_upgrade_provenance(provenance)

    assert rendered == json.dumps(provenance, allow_nan=False, indent=2, sort_keys=True) + "\n"
    assert _parse(rendered) == provenance


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository", "other/project"),
        ("workflow_path", ".github/workflows/other.yml"),
        ("workflow_ref", f"{_REPOSITORY}/{_WORKFLOW_PATH}@refs/heads/other"),
        ("run_id", 0),
        ("run_id", True),
        ("run_url", "https://example.test/actions/runs/31049485055"),
        ("run_head_sha", "f" * 39),
        ("artifact_name", "other"),
        ("artifact_file", "../proof.json"),
        ("artifact_retention_days", 0),
        ("artifact_retention_days", 91),
        ("verified_on", "not-a-date"),
        ("verification_method", "claimed"),
        ("evidence_sha256", "f" * 64),
    ],
)
def test_published_upgrade_provenance_rejects_untrusted_or_mismatched_fields(field: str, value: object) -> None:
    payload = deepcopy(_provenance())
    payload[field] = value  # ty: ignore[invalid-key] - parameterized runtime-boundary mutation.
    content = json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n"

    with pytest.raises(ValueError, match=r"^published upgrade provenance is invalid$"):
        _parse(content)


@pytest.mark.parametrize("mutation", ["extra", "noncanonical", "oversized"])
def test_published_upgrade_provenance_rejects_noncanonical_publication(mutation: str) -> None:
    provenance = _provenance()
    if mutation == "extra":
        payload = dict(provenance)
        payload["unexpected"] = "value"
        content = json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n"
    elif mutation == "noncanonical":
        content = serialize_published_upgrade_provenance(provenance) + "\n"
    else:
        content = " " * 16_385

    with pytest.raises(ValueError, match=r"^published upgrade provenance is invalid$"):
        _parse(content)


def test_published_upgrade_provenance_cli_writes_verified_sidecar(tmp_path: Path) -> None:
    evidence_path = tmp_path / _ARTIFACT_FILE
    output_path = tmp_path / "provenance.json"
    evidence_path.write_bytes(_EVIDENCE)

    result = subprocess.run(  # noqa: S603 - fixed local script with controlled test inputs.
        [
            sys.executable,
            "scripts/export_published_upgrade_provenance.py",
            "--evidence",
            str(evidence_path),
            "--repository",
            _REPOSITORY,
            "--workflow-ref",
            _WORKFLOW_REF,
            "--run-id",
            str(_RUN_ID),
            "--run-head-sha",
            _RUN_HEAD_SHA,
            "--verified-on",
            "2026-08-05",
            "--verification-method",
            "downloaded_artifact",
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == f"wrote verified provenance to {output_path}\n"
    assert _parse(output_path.read_bytes()) == _provenance()


def test_published_upgrade_provenance_cli_derives_date_from_evidence(tmp_path: Path) -> None:
    evidence = b'{"observed_on":"2026-08-05"}\n'
    evidence_path = tmp_path / _ARTIFACT_FILE
    output_path = tmp_path / "provenance.json"
    evidence_path.write_bytes(evidence)

    result = subprocess.run(  # noqa: S603 - fixed local script with controlled test inputs.
        [
            sys.executable,
            "scripts/export_published_upgrade_provenance.py",
            "--evidence",
            str(evidence_path),
            "--repository",
            _REPOSITORY,
            "--workflow-ref",
            _WORKFLOW_REF,
            "--run-id",
            str(_RUN_ID),
            "--run-head-sha",
            _RUN_HEAD_SHA,
            "--verification-method",
            "workflow_output",
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert _parse(
        output_path.read_bytes(),
        expected_sha256=hashlib.sha256(evidence).hexdigest(),
    ) == _provenance(
        evidence=evidence,
        verification_method="workflow_output",
    )
