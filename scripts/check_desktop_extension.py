"""Validate the repository's Claude Desktop MCP Bundle."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomli

_EXPECTED_MANIFEST_VERSION = "0.4"
_EXPECTED_NAME = "albumentationsx-mcp"
_EXPECTED_ENTRY_POINT = "src/server.py"
_EXPECTED_CONFIG_KEYS = ["allowed_directory", "artifact_directory", "max_preview_runs"]
_EXPECTED_ARGS = [
    "run",
    "--directory",
    "${__dirname}",
    _EXPECTED_ENTRY_POINT,
    "--allowed-root",
    "${user_config.allowed_directory}",
    "--artifact-root",
    "${user_config.artifact_directory}",
]
_EXPECTED_ENV = {"ALBU_MCP_MAX_PREVIEW_RUNS": "${user_config.max_preview_runs}"}
_MIN_PREVIEW_RUNS = 1
_MAX_PREVIEW_RUNS = 500
_EXPECTED_WRAPPER = (
    '"""Run the published AlbumentationsX MCP package inside a UV MCP Bundle."""\n\n'
    "from albumentationsx_mcp.cli import main\n\n"
    'if __name__ == "__main__":\n'
    "    main()\n"
)
_FORBIDDEN_FILENAMES = {".env", "id_rsa", "id_ed25519"}
_FORBIDDEN_SUFFIXES = {".key", ".p12", ".pem"}


@dataclass(frozen=True)
class DesktopExtensionReport:
    """Validated identity and least-privilege settings for the MCP bundle."""

    version: str
    name: str
    package_pin: str
    allowed_directory_configured: bool
    artifact_directory_configured: bool


def validate_desktop_extension(
    *,
    extension_root: Path = Path("desktop-extension"),
    pyproject_path: Path = Path("pyproject.toml"),
) -> DesktopExtensionReport:
    """Return the bundle contract after validating runtime, scope, and package pinning."""
    project = _read_toml_object(pyproject_path)
    project_version = _require_string(
        _require_object(project, "project", source=str(pyproject_path)),
        "version",
        source=str(pyproject_path),
    )
    manifest_path = extension_root / "manifest.json"
    manifest = _read_json_object(manifest_path)
    bundle_project_path = extension_root / "pyproject.toml"
    bundle_project = _require_object(
        _read_toml_object(bundle_project_path),
        "project",
        source=str(bundle_project_path),
    )

    _validate_identity(manifest, project_version=project_version)
    package_pin = _validate_package_pin(bundle_project, project_version=project_version)
    allowed_directory, artifact_directory = _validate_user_config(manifest)
    _validate_server(manifest)
    _validate_source(extension_root)

    return DesktopExtensionReport(
        version=project_version,
        name=_EXPECTED_NAME,
        package_pin=package_pin,
        allowed_directory_configured=allowed_directory,
        artifact_directory_configured=artifact_directory,
    )


def _validate_identity(manifest: dict[str, Any], *, project_version: str) -> None:
    """Validate schema generation, package identity, and release version."""
    if manifest.get("manifest_version") != _EXPECTED_MANIFEST_VERSION:
        msg = f"MCPB manifest_version must be {_EXPECTED_MANIFEST_VERSION!r}"
        raise ValueError(msg)
    if manifest.get("name") != _EXPECTED_NAME:
        msg = f"MCPB name must be {_EXPECTED_NAME!r}"
        raise ValueError(msg)
    manifest_version = _require_string(manifest, "version", source="MCPB manifest")
    if manifest_version != project_version:
        msg = f"manifest version {manifest_version!r} does not match project version {project_version!r}"
        raise ValueError(msg)
    if manifest.get("tools_generated") is not True:
        msg = "MCPB tools must be generated from the server at runtime"
        raise ValueError(msg)


def _validate_package_pin(bundle_project: dict[str, Any], *, project_version: str) -> str:
    """Require the desktop wrapper to use the matching published package exactly."""
    bundle_version = _require_string(bundle_project, "version", source="desktop-extension/pyproject.toml")
    if bundle_version != project_version:
        msg = f"bundle version {bundle_version!r} does not match project version {project_version!r}"
        raise ValueError(msg)
    expected_pin = f"albumentationsx-mcp=={project_version}"
    dependencies = bundle_project.get("dependencies")
    if dependencies != [expected_pin]:
        msg = f"bundle dependency must be pinned to {expected_pin}"
        raise ValueError(msg)
    return expected_pin


def _validate_user_config(manifest: dict[str, Any]) -> tuple[bool, bool]:
    """Require explicit dataset/output roots and bounded local retention."""
    user_config = _require_object(manifest, "user_config", source="MCPB manifest")
    if list(user_config) != _EXPECTED_CONFIG_KEYS:
        msg = f"user_config must define exactly {_EXPECTED_CONFIG_KEYS}"
        raise ValueError(msg)

    for key in _EXPECTED_CONFIG_KEYS[:2]:
        config = _require_object(user_config, key, source="MCPB user_config")
        if config.get("type") != "directory":
            msg = f"{key} must use the directory picker"
            raise ValueError(msg)
        if config.get("required") is not True:
            msg = f"{key} must be required"
            raise ValueError(msg)
        if "default" in config:
            msg = f"{key} must not define a default"
            raise ValueError(msg)

    retention = _require_object(user_config, "max_preview_runs", source="MCPB user_config")
    if retention.get("type") != "number" or retention.get("required") is not True:
        msg = "max_preview_runs must be a required number"
        raise ValueError(msg)
    if retention.get("min") != _MIN_PREVIEW_RUNS or retention.get("max") != _MAX_PREVIEW_RUNS:
        msg = "max_preview_runs bounds must be 1..500"
        raise ValueError(msg)
    default = retention.get("default")
    if (
        not isinstance(default, int)
        or isinstance(default, bool)
        or not _MIN_PREVIEW_RUNS <= default <= _MAX_PREVIEW_RUNS
    ):
        msg = "max_preview_runs default must be an integer within 1..500"
        raise ValueError(msg)
    return True, True


def _validate_server(manifest: dict[str, Any]) -> None:
    """Validate the UV launch command and explicit root forwarding."""
    server = _require_object(manifest, "server", source="MCPB manifest")
    if server.get("type") != "uv":
        msg = "MCPB server type must be 'uv'"
        raise ValueError(msg)
    if server.get("entry_point") != _EXPECTED_ENTRY_POINT:
        msg = f"MCPB entry point must be {_EXPECTED_ENTRY_POINT!r}"
        raise ValueError(msg)
    mcp_config = _require_object(server, "mcp_config", source="MCPB server")
    if mcp_config.get("command") != "uv":
        msg = "MCPB launch command must be 'uv'"
        raise ValueError(msg)
    if mcp_config.get("args") != _EXPECTED_ARGS:
        msg = "MCPB launch args must match the bounded directory contract"
        raise ValueError(msg)
    if mcp_config.get("env") != _EXPECTED_ENV:
        msg = "MCPB environment must define only bounded preview retention"
        raise ValueError(msg)


def _validate_source(extension_root: Path) -> None:
    """Reject embedded secrets and ensure the wrapper stays a thin adapter."""
    icon_path = extension_root / "icon.png"
    if not icon_path.is_file():
        msg = "MCPB icon is missing"
        raise ValueError(msg)
    wrapper_path = extension_root / _EXPECTED_ENTRY_POINT
    if wrapper_path.read_text(encoding="utf-8") != _EXPECTED_WRAPPER:
        msg = "MCPB wrapper must delegate directly to albumentationsx_mcp.cli.main"
        raise ValueError(msg)

    for path in extension_root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in _FORBIDDEN_FILENAMES or path.name.startswith(".env.") or path.suffix in _FORBIDDEN_SUFFIXES:
            msg = f"MCPB source contains forbidden file: {path.relative_to(extension_root)}"
            raise ValueError(msg)


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"{path} must contain a JSON object"
        raise TypeError(msg)
    return payload


def _read_toml_object(path: Path) -> dict[str, Any]:
    payload = tomli.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"{path} must contain a TOML table"
        raise TypeError(msg)
    return payload


def _require_object(payload: dict[str, Any], key: str, *, source: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        msg = f"{source} field {key!r} must be an object"
        raise TypeError(msg)
    return value


def _require_string(payload: dict[str, Any], key: str, *, source: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        msg = f"{source} field {key!r} must be a non-empty string"
        raise ValueError(msg)
    return value


def main() -> None:
    """CLI entrypoint for local and CI desktop extension validation."""
    try:
        report = validate_desktop_extension()
    except (OSError, TypeError, ValueError) as exc:
        sys.stderr.write(f"Claude Desktop MCP bundle validation failed: {exc}\n")
        raise SystemExit(1) from exc
    sys.stdout.write(f"Claude Desktop MCP bundle is valid: version {report.version}, dependency {report.package_pin}\n")


if __name__ == "__main__":
    main()
