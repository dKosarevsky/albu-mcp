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
_DEFAULT_MANUAL_RUNS_PATH = Path("docs/HOST_MANUAL_RUNS.json")
_DEFAULT_PYPROJECT_PATH = Path("pyproject.toml")
_DEFAULT_SERVER_JSON_PATH = Path("server.json")
_DEFAULT_HOST_PROOF_STATUS_PATH = Path("docs/HOST_PROOF_STATUS.md")


def build_committed_lifecycle_status(
    *,
    experiment_path: Path = _DEFAULT_EXPERIMENT_PATH,
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
        release_channels=[
            {"id": "pypi", "status": "published", "url": adoption["pypi_url"]},
            {
                "id": "github_release",
                "status": "published",
                "url": f"{repository}/releases/tag/v{version}",
            },
            {"id": "official_registry", "status": "listed", "url": adoption["registry_url"]},
        ],
        host_blockers=launch_report["blockers"],
        experiment=experiment,
    )


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
