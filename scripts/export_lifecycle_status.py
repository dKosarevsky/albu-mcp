"""Export current release, host-evidence, and adoption lifecycle status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from albumentationsx_mcp.lifecycle import (
    ProtocolCompatibilityEvidence,
    PublishedUpgradeExpectation,
    build_lifecycle_status,
    load_protocol_compatibility_evidence,
    render_lifecycle_status_markdown,
)
from scripts.check_published_upgrade import write_atomic_text
from scripts.export_adoption_packet import build_adoption_packet
from scripts.export_v1_launch_report import build_v1_launch_report

_DEFAULT_EXPERIMENT_PATH = Path("docs/ADOPTION_EXPERIMENT.json")
_DEFAULT_RELEASE_HEALTH_PATH = Path("docs/RELEASE_HEALTH.json")
_DEFAULT_MANUAL_RUNS_PATH = Path("docs/HOST_MANUAL_RUNS.json")
_DEFAULT_PYPROJECT_PATH = Path("pyproject.toml")
_DEFAULT_SERVER_JSON_PATH = Path("server.json")
_DEFAULT_HOST_PROOF_STATUS_PATH = Path("docs/HOST_PROOF_STATUS.md")
_DEFAULT_PUBLISHED_UPGRADE_PATH = Path("docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-05.json")
_DEFAULT_PUBLISHED_UPGRADE_PROVENANCE_PATH = Path(
    "docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-05.provenance.json"
)
_DEFAULT_DOCS_ROOT = Path("docs")
_DEFAULT_STATUS_DOCUMENT_PATH = Path("docs/STATUS.md")
_RELEASE_CHANNEL_IDS = ("pypi", "github_release", "ci", "official_registry")
_PUBLISHED_UPGRADE_FROM_VERSION = "1.20.0"
_PUBLISHED_UPGRADE_OBSERVED_ON = "2026-08-05"
_PUBLISHED_UPGRADE_EVIDENCE_ERROR = "published upgrade evidence is invalid"
_EXPORT_ERROR = "lifecycle status export failed"


def build_committed_lifecycle_status(  # noqa: PLR0913
    *,
    experiment_path: Path = _DEFAULT_EXPERIMENT_PATH,
    release_health_path: Path = _DEFAULT_RELEASE_HEALTH_PATH,
    manual_runs_path: Path = _DEFAULT_MANUAL_RUNS_PATH,
    pyproject_path: Path = _DEFAULT_PYPROJECT_PATH,
    server_json_path: Path = _DEFAULT_SERVER_JSON_PATH,
    host_proof_status_path: Path = _DEFAULT_HOST_PROOF_STATUS_PATH,
    published_upgrade_path: Path = _DEFAULT_PUBLISHED_UPGRADE_PATH,
    published_upgrade_provenance_path: Path | None = None,
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
            provenance_path=(
                _DEFAULT_PUBLISHED_UPGRADE_PROVENANCE_PATH
                if published_upgrade_provenance_path is None
                and published_upgrade_path == _DEFAULT_PUBLISHED_UPGRADE_PATH
                else published_upgrade_provenance_path
            ),
            docs_root=docs_root,
            document_path=document_path,
            expected_to_version=version,
        ),
    )


def _load_protocol_compatibility(
    path: Path,
    *,
    provenance_path: Path | None,
    docs_root: Path,
    document_path: Path,
    expected_to_version: str,
) -> ProtocolCompatibilityEvidence:
    try:
        return load_protocol_compatibility_evidence(
            evidence_path=path,
            provenance_path=provenance_path,
            trusted_root=docs_root,
            document_path=document_path,
            expectation=PublishedUpgradeExpectation(
                from_version=_PUBLISHED_UPGRADE_FROM_VERSION,
                to_version=expected_to_version,
                observed_on=_PUBLISHED_UPGRADE_OBSERVED_ON,
            ),
        )
    except (OSError, RuntimeError, ValueError):
        raise ValueError(_PUBLISHED_UPGRADE_EVIDENCE_ERROR) from None


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
        content = render_lifecycle_status_markdown(report)
        if args.output is not None:
            write_atomic_text(args.output, content)
    except (OSError, TypeError, ValueError):
        sys.stderr.write(f"{_EXPORT_ERROR}\n")
        raise SystemExit(2) from None
    if args.output is None:
        sys.stdout.write(content)


if __name__ == "__main__":
    main()
