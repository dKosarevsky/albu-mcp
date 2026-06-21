"""Smoke-test the published PyPI package through uvx."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

_PROJECT_FIELD_PATTERN = re.compile(r'(?m)^(name|version)\s*=\s*"([^"]+)"')


def main() -> None:
    """Run or print the published-package smoke command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(), help="Repository root. Defaults to cwd.")
    parser.add_argument("--package", help="PyPI package name. Defaults to server.json package identifier.")
    parser.add_argument("--version", help="Package version. Defaults to pyproject.toml version.")
    parser.add_argument("--retries", type=int, default=6, help="Attempts before failing.")
    parser.add_argument("--delay", type=float, default=10.0, help="Seconds between retry attempts.")
    parser.add_argument("--timeout", type=float, default=20.0, help="PyPI version endpoint timeout in seconds.")
    parser.add_argument(
        "--skip-pypi-version-check",
        action="store_true",
        help="Skip direct PyPI /version/json verification before uvx smoke.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the uvx command without running it.")
    args = parser.parse_args()

    metadata = _read_release_metadata(args.root)
    package = args.package or metadata.package
    version = args.version or metadata.version
    command = build_smoke_command(package=package, version=version)
    if args.dry_run:
        sys.stdout.write(shlex.join(command) + "\n")
        return
    run_smoke(
        SmokeConfig(
            command=command,
            package=package,
            version=version,
            retries=args.retries,
            delay_seconds=args.delay,
            timeout_seconds=args.timeout,
            check_pypi_version=not args.skip_pypi_version_check,
        )
    )


@dataclass(frozen=True)
class ReleaseMetadata:
    """Package metadata needed for published-package smoke checks."""

    package: str
    version: str


@dataclass(frozen=True)
class SmokeConfig:
    """Inputs for one published-package smoke run."""

    command: list[str]
    package: str
    version: str
    retries: int = 6
    delay_seconds: float = 10.0
    timeout_seconds: float = 20.0
    check_pypi_version: bool = True


def build_smoke_command(*, package: str, version: str) -> list[str]:
    """Build the uvx command used by release and host-acceptance checks."""
    return [
        "uvx",
        "--from",
        f"{package}=={version}",
        "--refresh-package",
        package,
        package,
        "--help",
    ]


def build_pypi_version_url(*, package: str, version: str) -> str:
    """Return the direct PyPI JSON endpoint for one package release version."""
    return f"https://pypi.org/pypi/{package}/{version}/json"


def run_smoke(config: SmokeConfig) -> None:
    """Run the smoke command with retries for package-index propagation delays."""
    attempts = max(1, config.retries)
    for attempt in range(1, attempts + 1):
        if config.check_pypi_version:
            pypi_error = _check_pypi_version(
                package=config.package,
                version=config.version,
                timeout_seconds=config.timeout_seconds,
            )
            if pypi_error is not None:
                if attempt == attempts:
                    sys.stderr.write(pypi_error)
                    raise SystemExit(1)
                sys.stderr.write(f"{pypi_error.rstrip()}, retrying smoke attempt {attempt}/{attempts}\n")
                time.sleep(max(0.0, config.delay_seconds))
                continue
        completed = subprocess.run(config.command, check=False, text=True, capture_output=True)  # noqa: S603
        if completed.returncode == 0:
            sys.stdout.write(completed.stdout)
            return
        if attempt == attempts:
            sys.stderr.write(completed.stderr)
            raise SystemExit(completed.returncode)
        sys.stderr.write(f"published package is not visible yet, retrying smoke attempt {attempt}/{attempts}\n")
        time.sleep(max(0.0, config.delay_seconds))


def _check_pypi_version(*, package: str, version: str, timeout_seconds: float) -> str | None:
    url = build_pypi_version_url(package=package, version=version)
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310 - fixed HTTPS PyPI URL.
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return f"PyPI version endpoint is not visible yet: {url} ({exc})"
    published_version = payload.get("info", {}).get("version")
    if published_version != version:
        return f"PyPI version endpoint returned {published_version!r}, expected {version!r}: {url}"
    return None


def _read_release_metadata(root: Path) -> ReleaseMetadata:
    root = root.resolve()
    project = _read_project_fields(root / "pyproject.toml")
    server = json.loads((root / "server.json").read_text(encoding="utf-8"))
    return ReleaseMetadata(package=_first_pypi_package(server), version=project["version"])


def _read_project_fields(path: Path) -> dict[str, str]:
    project_block = path.read_text(encoding="utf-8").split("[project]", maxsplit=1)[1].split("[", maxsplit=1)[0]
    fields = {match.group(1): match.group(2) for match in _PROJECT_FIELD_PATTERN.finditer(project_block)}
    if "version" not in fields:
        msg = f"Could not read project version from {path}"
        raise ValueError(msg)
    return fields


def _first_pypi_package(server: dict[str, object]) -> str:
    packages = server.get("packages", [])
    if isinstance(packages, list):
        for package in packages:
            if isinstance(package, dict) and package.get("registryType") == "pypi":
                identifier = package.get("identifier")
                if isinstance(identifier, str) and identifier:
                    return identifier
    msg = "server.json does not contain a PyPI package entry"
    raise ValueError(msg)


if __name__ == "__main__":
    main()
