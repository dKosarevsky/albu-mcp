"""Export current release, host-evidence, and adoption lifecycle status."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from albumentationsx_mcp.lifecycle import (
    ProtocolCompatibility,
    build_lifecycle_status,
    render_lifecycle_status_markdown,
)
from albumentationsx_mcp.upgrade_proof import parse_upgrade_proof_report
from scripts.export_adoption_packet import build_adoption_packet
from scripts.export_v1_launch_report import build_v1_launch_report

_DEFAULT_EXPERIMENT_PATH = Path("docs/ADOPTION_EXPERIMENT.json")
_DEFAULT_RELEASE_HEALTH_PATH = Path("docs/RELEASE_HEALTH.json")
_DEFAULT_MANUAL_RUNS_PATH = Path("docs/HOST_MANUAL_RUNS.json")
_DEFAULT_PYPROJECT_PATH = Path("pyproject.toml")
_DEFAULT_SERVER_JSON_PATH = Path("server.json")
_DEFAULT_HOST_PROOF_STATUS_PATH = Path("docs/HOST_PROOF_STATUS.md")
_DEFAULT_PUBLISHED_UPGRADE_PATH = Path("docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-04.json")
_DEFAULT_DOCS_ROOT = Path("docs")
_DEFAULT_STATUS_DOCUMENT_PATH = Path("docs/STATUS.md")
_RELEASE_CHANNEL_IDS = ("pypi", "github_release", "ci", "official_registry")
_PUBLISHED_UPGRADE_FROM_VERSION = "1.20.0"
_PUBLISHED_UPGRADE_TO_VERSION = "1.21.0"
_PUBLISHED_UPGRADE_OBSERVED_ON = "2026-08-04"
_PUBLISHED_UPGRADE_STATUS_BASIS = "Published upgrade probe result only; this does not assert provenance."
_PUBLISHED_UPGRADE_PROVENANCE = (
    "Local operator-run snapshot. No immutable public run or attestation is available; this evidence is not "
    "independently attested or provenance-verifiable."
)
_PUBLISHED_UPGRADE_SCOPE = (
    "Streamable HTTP conformance and published-package artifact continuity. This is not real-host UI evidence."
)
_PUBLISHED_UPGRADE_EVIDENCE_ERROR = "published upgrade evidence is invalid"


def build_committed_lifecycle_status(  # noqa: PLR0913
    *,
    experiment_path: Path = _DEFAULT_EXPERIMENT_PATH,
    release_health_path: Path = _DEFAULT_RELEASE_HEALTH_PATH,
    manual_runs_path: Path = _DEFAULT_MANUAL_RUNS_PATH,
    pyproject_path: Path = _DEFAULT_PYPROJECT_PATH,
    server_json_path: Path = _DEFAULT_SERVER_JSON_PATH,
    host_proof_status_path: Path = _DEFAULT_HOST_PROOF_STATUS_PATH,
    published_upgrade_path: Path = _DEFAULT_PUBLISHED_UPGRADE_PATH,
    docs_root: Path = _DEFAULT_DOCS_ROOT,
    document_path: Path = _DEFAULT_STATUS_DOCUMENT_PATH,
) -> dict[str, Any]:
    """Build current lifecycle status from committed project metadata."""
    adoption = build_adoption_packet(server_json_path=server_json_path, pyproject_path=pyproject_path)
    launch_report = build_v1_launch_report(
        manual_runs_path=manual_runs_path,
        pyproject_path=pyproject_path,
        server_json_path=server_json_path,
        host_proof_status_path=host_proof_status_path,
    )
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    repository = adoption["repository"]
    version = adoption["version"]
    return build_lifecycle_status(
        version=version,
        release_channels=_load_release_channels(
            release_health_path,
            version=version,
            repository=repository,
            pypi_url=adoption["pypi_url"],
            registry_url=adoption["registry_url"],
        ),
        host_blockers=launch_report["blockers"],
        experiment=experiment,
        protocol_compatibility=_load_protocol_compatibility(
            published_upgrade_path,
            docs_root=docs_root,
            document_path=document_path,
        ),
    )


def _load_protocol_compatibility(
    path: Path,
    *,
    docs_root: Path,
    document_path: Path,
) -> ProtocolCompatibility:
    try:
        evidence_path = _relative_evidence_link(
            path,
            docs_root=docs_root,
            document_path=document_path,
        )
        raw_content = path.read_bytes()
        report = parse_upgrade_proof_report(
            raw_content,
            expected_package="albumentationsx-mcp",
            expected_from_version=_PUBLISHED_UPGRADE_FROM_VERSION,
            expected_to_version=_PUBLISHED_UPGRADE_TO_VERSION,
            expected_observed_on=_PUBLISHED_UPGRADE_OBSERVED_ON,
        )
        _require_passing_upgrade_report(report["status"])
    except (OSError, RuntimeError, ValueError):
        raise ValueError(_PUBLISHED_UPGRADE_EVIDENCE_ERROR) from None
    return {
        "schema_version": 1,
        "status": "passed",
        "status_basis": _PUBLISHED_UPGRADE_STATUS_BASIS,
        "from_version": _PUBLISHED_UPGRADE_FROM_VERSION,
        "to_version": _PUBLISHED_UPGRADE_TO_VERSION,
        "evidence_path": evidence_path,
        "evidence_sha256": hashlib.sha256(raw_content).hexdigest(),
        "provenance": _PUBLISHED_UPGRADE_PROVENANCE,
        "scope": _PUBLISHED_UPGRADE_SCOPE,
    }


def _require_passing_upgrade_report(status: str) -> None:
    if status != "pass":
        raise ValueError(_PUBLISHED_UPGRADE_EVIDENCE_ERROR)


def _relative_evidence_link(
    evidence_path: Path,
    *,
    docs_root: Path,
    document_path: Path,
) -> str:
    root = docs_root.resolve(strict=True)
    evidence = evidence_path.resolve(strict=True)
    document = document_path.resolve(strict=False)
    if not root.is_dir() or not evidence.is_file():
        raise ValueError(_PUBLISHED_UPGRADE_EVIDENCE_ERROR)
    evidence.relative_to(root)
    document.relative_to(root)
    return evidence.relative_to(document.parent).as_posix()


def _load_release_channels(
    path: Path,
    *,
    version: str,
    repository: str,
    pypi_url: str,
    registry_url: str,
) -> list[dict[str, str]]:
    defaults = _unknown_release_channels(
        version=version,
        repository=repository,
        pypi_url=pypi_url,
        registry_url=registry_url,
    )
    if not path.exists():
        return defaults
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != version:
        return defaults
    if payload.get("schema_version") != 1:
        msg = "release health schema_version must be 1"
        raise ValueError(msg)
    observed_at = str(payload.get("observed_at", "not_observed"))
    raw_channels = payload.get("channels")
    if not isinstance(raw_channels, list):
        msg = "release health channels must be a list"
        raise TypeError(msg)
    channels_by_id = {
        str(channel.get("id")): channel
        for channel in raw_channels
        if isinstance(channel, dict) and str(channel.get("id")) in _RELEASE_CHANNEL_IDS
    }
    channels: list[dict[str, str]] = []
    for default in defaults:
        raw = channels_by_id.get(default["id"])
        if raw is None:
            channels.append(default)
            continue
        channel = {key: str(value) for key, value in raw.items()}
        channel.setdefault("observed_at", observed_at)
        channels.append(channel)
    return channels


def _unknown_release_channels(
    *,
    version: str,
    repository: str,
    pypi_url: str,
    registry_url: str,
) -> list[dict[str, str]]:
    return [
        {"id": "pypi", "status": "unknown", "url": f"{pypi_url}{version}/", "observed_at": "not_observed"},
        {
            "id": "github_release",
            "status": "unknown",
            "url": f"{repository}/releases/tag/v{version}",
            "observed_at": "not_observed",
        },
        {
            "id": "ci",
            "status": "not_observed",
            "url": f"{repository}/actions/workflows/ci.yml",
            "observed_at": "not_observed",
        },
        {
            "id": "official_registry",
            "status": "unknown",
            "url": registry_url,
            "observed_at": "not_observed",
        },
    ]


def main() -> None:
    """CLI entrypoint for lifecycle status exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    document_path = args.output or _DEFAULT_STATUS_DOCUMENT_PATH
    try:
        report = build_committed_lifecycle_status(document_path=document_path)
        content = render_lifecycle_status_markdown(
            report,
            docs_root=_DEFAULT_DOCS_ROOT,
            document_path=document_path,
        )
    except ValueError as exc:
        sys.stderr.write(f"lifecycle status export error: {exc}\n")
        raise SystemExit(2) from None
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
