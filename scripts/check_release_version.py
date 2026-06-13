"""Validate that release tags match package and MCP Registry metadata versions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_PROJECT_VERSION_PATTERN = re.compile(r'(?m)^version\s*=\s*"([^"]+)"\s*$')


@dataclass(frozen=True)
class ReleaseVersionReport:
    """Version values that must agree before a release is published."""

    version: str
    pyproject_version: str
    server_version: str
    package_version: str


def validate_release_versions(
    tag: str,
    *,
    pyproject_path: Path = Path("pyproject.toml"),
    server_json_path: Path = Path("server.json"),
) -> ReleaseVersionReport:
    """Return matching release versions or raise ValueError with the first mismatch."""
    version = _version_from_tag(tag)
    pyproject_version = _read_pyproject_version(pyproject_path)
    server_version, package_version = _read_server_versions(server_json_path)

    if pyproject_version != version:
        msg = f"pyproject.toml version {pyproject_version!r} does not match tag version {version!r}"
        raise ValueError(msg)
    if server_version != version:
        msg = f"server.json version {server_version!r} does not match tag version {version!r}"
        raise ValueError(msg)
    if package_version != version:
        msg = f"server.json package version {package_version!r} does not match tag version {version!r}"
        raise ValueError(msg)

    return ReleaseVersionReport(
        version=version,
        pyproject_version=pyproject_version,
        server_version=server_version,
        package_version=package_version,
    )


def _version_from_tag(tag: str) -> str:
    if not tag.startswith("v"):
        msg = "release tag must start with 'v'"
        raise ValueError(msg)
    version = tag[1:]
    if not version:
        msg = "release tag version is empty"
        raise ValueError(msg)
    return version


def _read_pyproject_version(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    match = _PROJECT_VERSION_PATTERN.search(content)
    if match is None:
        msg = f"Could not find project version in {path}"
        raise ValueError(msg)
    return match.group(1)


def _read_server_versions(path: Path) -> tuple[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    server_version = str(payload["version"])
    package = next(
        item
        for item in payload["packages"]
        if item.get("registryType") == "pypi" and item.get("identifier") == "albumentationsx-mcp"
    )
    return server_version, str(package["version"])


def main() -> None:
    """CLI entrypoint for GitHub Actions release checks."""
    parser = argparse.ArgumentParser(description="Validate release tag and package metadata versions.")
    parser.add_argument("tag", help="Git ref name, for example v0.1.0")
    args = parser.parse_args()
    report = validate_release_versions(args.tag)
    sys.stdout.write(f"release version {report.version} is consistent\n")


if __name__ == "__main__":
    main()
