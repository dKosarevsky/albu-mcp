"""Validate the repository's native Codex plugin bundle."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PROJECT_VERSION_PATTERN = re.compile(r'(?m)^version\s*=\s*"([^"]+)"\s*$')
_EXPECTED_PLUGIN_NAME = "albumentationsx-mcp"
_EXPECTED_SKILLS_PATH = "./skills/"
_EXPECTED_MCP_PATH = "./.mcp.json"
_EXPECTED_SERVER_NAME = "albumentationsx"
_EXPECTED_ENV_VARS = [
    "ALBU_MCP_ALLOWED_ROOTS",
    "ALBU_MCP_ARTIFACT_ROOT",
    "ALBU_MCP_MAX_PREVIEW_RUNS",
]
_ROOT_ARGS = {"--allowed-root", "--artifact-root"}
_EXPECTED_TOOL_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class CodexPluginReport:
    """Validated Codex plugin identity and runtime selection."""

    version: str
    plugin_version: str
    package_version: str
    server_name: str


def validate_codex_plugin(
    *,
    plugin_manifest_path: Path = Path(".codex-plugin/plugin.json"),
    mcp_manifest_path: Path = Path(".mcp.json"),
    pyproject_path: Path = Path("pyproject.toml"),
) -> CodexPluginReport:
    """Return the plugin runtime identity after validating its repository contract."""
    plugin = _read_json_object(plugin_manifest_path)
    mcp = _read_json_object(mcp_manifest_path)
    project_version = _read_project_version(pyproject_path)
    plugin_version = _validate_plugin_manifest(
        plugin,
        manifest_path=plugin_manifest_path,
        project_version=project_version,
    )
    package_version, server_name = _validate_mcp_manifest(mcp, project_version=project_version)

    return CodexPluginReport(
        version=project_version,
        plugin_version=plugin_version,
        package_version=package_version,
        server_name=server_name,
    )


def _validate_plugin_manifest(
    plugin: dict[str, Any],
    *,
    manifest_path: Path,
    project_version: str,
) -> str:
    """Validate component paths and version metadata from plugin.json."""
    if plugin.get("name") != _EXPECTED_PLUGIN_NAME:
        msg = f"plugin name must be {_EXPECTED_PLUGIN_NAME!r}"
        raise ValueError(msg)
    if plugin.get("skills") != _EXPECTED_SKILLS_PATH:
        msg = f"plugin skills path must be {_EXPECTED_SKILLS_PATH!r}"
        raise ValueError(msg)
    if plugin.get("mcpServers") != _EXPECTED_MCP_PATH:
        msg = f"plugin MCP path must be {_EXPECTED_MCP_PATH!r}"
        raise ValueError(msg)

    plugin_version = _require_string(plugin, "version", source=str(manifest_path))
    if plugin_version != project_version:
        msg = f"plugin version {plugin_version!r} does not match project version {project_version!r}"
        raise ValueError(msg)

    plugin_root = manifest_path.parent.parent
    canonical_skill = plugin_root / "skills" / _EXPECTED_PLUGIN_NAME / "SKILL.md"
    if not canonical_skill.is_file():
        msg = f"canonical plugin skill is missing: {canonical_skill}"
        raise ValueError(msg)
    return plugin_version


def _validate_mcp_manifest(mcp: dict[str, Any], *, project_version: str) -> tuple[str, str]:
    """Validate the pinned, least-privilege stdio server contract."""
    if set(mcp) != {"mcpServers"}:
        msg = ".mcp.json must contain only the mcpServers object"
        raise ValueError(msg)
    servers = _require_object(mcp, "mcpServers", source=".mcp.json")
    if list(servers) != [_EXPECTED_SERVER_NAME]:
        msg = f"MCP config must define exactly one server named {_EXPECTED_SERVER_NAME!r}"
        raise ValueError(msg)
    server = _require_object(servers, _EXPECTED_SERVER_NAME, source=".mcp.json mcpServers")

    if "env" in server:
        msg = "MCP server must not define fixed environment values"
        raise ValueError(msg)
    args = _require_string_list(server, "args", source="AlbumentationsX MCP server")
    if any(arg in _ROOT_ARGS for arg in args):
        msg = "MCP args must not grant implicit user dataset roots"
        raise ValueError(msg)

    expected_package = f"albumentationsx-mcp=={project_version}"
    expected_args = ["--from", expected_package, "albumentationsx-mcp"]
    if args != expected_args:
        msg = f"MCP package must be pinned to {expected_package}"
        raise ValueError(msg)
    if server.get("command") != "uvx":
        msg = "MCP server command must be 'uvx'"
        raise ValueError(msg)
    if server.get("cwd") != ".":
        msg = "MCP server cwd must stay inside the plugin root"
        raise ValueError(msg)
    if server.get("env_vars") != _EXPECTED_ENV_VARS:
        msg = "MCP env_vars must match the documented allowlist"
        raise ValueError(msg)
    if server.get("tool_timeout_sec") != _EXPECTED_TOOL_TIMEOUT_SECONDS:
        msg = f"MCP tool timeout must be {_EXPECTED_TOOL_TIMEOUT_SECONDS} seconds"
        raise ValueError(msg)
    return project_version, _EXPECTED_SERVER_NAME


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"{path} must contain a JSON object"
        raise TypeError(msg)
    return payload


def _read_project_version(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    match = _PROJECT_VERSION_PATTERN.search(content)
    if match is None:
        msg = f"project version is missing from {path}"
        raise ValueError(msg)
    return match.group(1)


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


def _require_string_list(payload: dict[str, Any], key: str, *, source: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        msg = f"{source} field {key!r} must be a string list"
        raise ValueError(msg)
    return value


def main() -> None:
    """CLI entrypoint for local and CI plugin validation."""
    try:
        report = validate_codex_plugin()
    except (OSError, TypeError, ValueError) as exc:
        sys.stderr.write(f"Codex plugin validation failed: {exc}\n")
        raise SystemExit(1) from exc
    sys.stdout.write(f"Codex plugin bundle is valid: version {report.version}, server {report.server_name}\n")


if __name__ == "__main__":
    main()
