"""Export current release, host-evidence, and adoption lifecycle status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from albumentationsx_mcp.lifecycle import build_lifecycle_status, render_lifecycle_status_markdown
from scripts.export_adoption_packet import build_adoption_packet
from scripts.export_v1_launch_report import build_v1_launch_report

_DEFAULT_EXPERIMENT_PATH = Path("docs/ADOPTION_EXPERIMENT.json")
_DEFAULT_RELEASE_HEALTH_PATH = Path("docs/RELEASE_HEALTH.json")
_DEFAULT_MANUAL_RUNS_PATH = Path("docs/HOST_MANUAL_RUNS.json")
_DEFAULT_PYPROJECT_PATH = Path("pyproject.toml")
_DEFAULT_SERVER_JSON_PATH = Path("server.json")
_DEFAULT_HOST_PROOF_STATUS_PATH = Path("docs/HOST_PROOF_STATUS.md")
_RELEASE_CHANNEL_IDS = ("pypi", "github_release", "ci", "official_registry")


def build_committed_lifecycle_status(  # noqa: PLR0913
    *,
    experiment_path: Path = _DEFAULT_EXPERIMENT_PATH,
    release_health_path: Path = _DEFAULT_RELEASE_HEALTH_PATH,
    manual_runs_path: Path = _DEFAULT_MANUAL_RUNS_PATH,
    pyproject_path: Path = _DEFAULT_PYPROJECT_PATH,
    server_json_path: Path = _DEFAULT_SERVER_JSON_PATH,
    host_proof_status_path: Path = _DEFAULT_HOST_PROOF_STATUS_PATH,
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
    )


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

    content = render_lifecycle_status_markdown(build_committed_lifecycle_status())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
