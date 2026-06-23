"""Export public adoption copy for AlbumentationsX MCP."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_DEFAULT_SERVER_JSON_PATH = Path("server.json")
_DEFAULT_PYPROJECT_PATH = Path("pyproject.toml")
_VERSION_PATTERN = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)


def build_adoption_packet(
    *,
    server_json_path: Path = _DEFAULT_SERVER_JSON_PATH,
    pyproject_path: Path = _DEFAULT_PYPROJECT_PATH,
) -> dict[str, Any]:
    """Build a deterministic public adoption packet from committed metadata."""
    server = json.loads(server_json_path.read_text(encoding="utf-8"))
    package = server["packages"][0]
    version = _read_pyproject_version(pyproject_path)
    return {
        "title": server["title"],
        "mcp_name": server["name"],
        "description": server["description"],
        "package": package["identifier"],
        "version": version,
        "repository": server["repository"]["url"],
        "website": server["websiteUrl"],
        "registry_url": "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp",
        "pypi_url": f"https://pypi.org/project/{package['identifier']}/",
        "upstream_pr_url": "https://github.com/albumentations-team/AlbumentationsX/pull/289",
        "launch_kit_path": "docs/LAUNCH_KIT.md",
        "install_command": f"uvx --from {package['identifier']} albumentationsx-mcp",
        "preview_command": (
            f"uvx --from {package['identifier']} albumentationsx-mcp "
            "--allowed-root /absolute/path/to/images --artifact-root /absolute/path/to/albu-artifacts"
        ),
        "host_names": ["Claude Desktop", "Claude Code", "Cursor", "Codex"],
        "workflow_tools": [
            "run_host_smoke_check",
            "inspect_dataset_quality",
            "build_review_packet",
            "validate_preview_request",
            "render_preview_batch",
            "compare_preview_runs",
            "export_preview_report",
            "export_pipeline",
        ],
    }


def render_adoption_packet_markdown(packet: dict[str, Any]) -> str:
    """Render the public adoption packet as Markdown."""
    lines = [
        "# AlbumentationsX MCP Adoption Packet",
        "",
        f"{packet['description']}",
        "",
        "## Install",
        "",
        "```bash",
        packet["install_command"],
        "```",
        "",
        "For local previews:",
        "",
        "```bash",
        packet["preview_command"],
        "```",
        "",
        "## Public Links",
        "",
        f"- Repository: {packet['repository']}",
        f"- PyPI: {packet['pypi_url']}",
        f"- MCP Registry: {packet['registry_url']}",
        f"- Upstream docs PR: AlbumentationsX#289 ({packet['upstream_pr_url']})",
        f"- Launch Kit: {packet['launch_kit_path']}",
        "",
        "## Host Coverage",
        "",
        *[f"- {host}" for host in packet["host_names"]],
        "",
        "## First Dataset Workflow",
        "",
        *[f"1. `{tool}`" for tool in packet["workflow_tools"]],
        "",
        "## Short Launch Copy",
        "",
        (
            "AlbumentationsX MCP lets MCP hosts inspect a local computer-vision dataset, build a safe first-preview "
            "request, render contact sheets, capture concrete feedback, and export reproducible AlbumentationsX "
            "pipelines without giving the host arbitrary Python execution."
        ),
        "",
        "## Privacy Note",
        "",
        "Keep private datasets local. Use `--allowed-root` to scope image access and share only redacted artifacts.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for adoption packet exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_adoption_packet_markdown(build_adoption_packet())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _read_pyproject_version(path: Path) -> str:
    match = _VERSION_PATTERN.search(path.read_text(encoding="utf-8"))
    if match is None:
        msg = f"{path}: project version not found"
        raise ValueError(msg)
    return match.group(1)


if __name__ == "__main__":
    main()
