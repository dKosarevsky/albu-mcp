from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_codex_plugin import validate_codex_plugin

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST_PATH = ROOT / ".codex-plugin" / "plugin.json"
MCP_MANIFEST_PATH = ROOT / ".mcp.json"


def test_codex_plugin_bundle_exposes_canonical_skill_and_pinned_server() -> None:
    assert PLUGIN_MANIFEST_PATH.is_file()
    assert MCP_MANIFEST_PATH.is_file()

    plugin = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
    mcp = json.loads(MCP_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert plugin["name"] == "albumentationsx-mcp"
    assert plugin["version"] == "1.15.0"
    assert plugin["skills"] == "./skills/"
    assert plugin["mcpServers"] == "./.mcp.json"
    assert plugin["interface"]["displayName"] == "AlbumentationsX MCP"
    assert plugin["interface"]["category"] == "Developer Tools"
    assert len(plugin["interface"]["defaultPrompt"]) <= 3
    assert all(len(prompt) <= 128 for prompt in plugin["interface"]["defaultPrompt"])

    assert list(mcp) == ["mcpServers"]
    assert list(mcp["mcpServers"]) == ["albumentationsx"]
    server = mcp["mcpServers"]["albumentationsx"]
    assert server["command"] == "uvx"
    assert server["args"] == [
        "--from",
        "albumentationsx-mcp==1.15.0",
        "albumentationsx-mcp",
    ]
    assert server["env_vars"] == [
        "ALBU_MCP_ALLOWED_ROOTS",
        "ALBU_MCP_ARTIFACT_ROOT",
        "ALBU_MCP_MAX_PREVIEW_RUNS",
    ]
    assert "--allowed-root" not in server["args"]
    assert "--artifact-root" not in server["args"]
    assert "env" not in server


def test_codex_plugin_validator_cli_accepts_repository_bundle() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_codex_plugin.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "Codex plugin bundle is valid: version 1.15.0, server albumentationsx\n"


def test_codex_plugin_validator_accepts_matching_safe_bundle(tmp_path: Path) -> None:
    plugin_path, mcp_path, pyproject_path = _write_bundle(tmp_path)

    report = validate_codex_plugin(
        plugin_manifest_path=plugin_path,
        mcp_manifest_path=mcp_path,
        pyproject_path=pyproject_path,
    )

    assert report.version == "1.15.0"
    assert report.plugin_version == "1.15.0"
    assert report.package_version == "1.15.0"
    assert report.server_name == "albumentationsx"


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("plugin_version", "plugin version '1.14.0' does not match project version '1.15.0'"),
        ("skill_path", "plugin skills path must be './skills/'"),
        ("mcp_path", "plugin MCP path must be './.mcp.json'"),
        ("unpinned_package", "MCP package must be pinned to albumentationsx-mcp==1.15.0"),
        ("extra_env_var", "MCP env_vars must match the documented allowlist"),
        ("implicit_root_arg", "MCP args must not grant implicit filesystem roots"),
        ("fixed_env", "MCP server must not define fixed environment values"),
    ],
)
def test_codex_plugin_validator_rejects_unsafe_or_drifted_bundle(
    tmp_path: Path,
    case: str,
    message: str,
) -> None:
    plugin_path, mcp_path, pyproject_path = _write_bundle(tmp_path, mutation=case)

    with pytest.raises(ValueError, match=message):
        validate_codex_plugin(
            plugin_manifest_path=plugin_path,
            mcp_manifest_path=mcp_path,
            pyproject_path=pyproject_path,
        )


def _write_bundle(tmp_path: Path, *, mutation: str | None = None) -> tuple[Path, Path, Path]:
    plugin = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
    mcp = json.loads(MCP_MANIFEST_PATH.read_text(encoding="utf-8"))
    server = mcp["mcpServers"]["albumentationsx"]

    if mutation == "plugin_version":
        plugin["version"] = "1.14.0"
    elif mutation == "skill_path":
        plugin["skills"] = "./other-skills/"
    elif mutation == "mcp_path":
        plugin["mcpServers"] = "./other-mcp.json"
    elif mutation == "unpinned_package":
        server["args"] = ["--from", "albumentationsx-mcp", "albumentationsx-mcp"]
    elif mutation == "extra_env_var":
        server["env_vars"].append("UNREVIEWED_ROOT")
    elif mutation == "implicit_root_arg":
        server["args"].extend(["--allowed-root", "/example/images"])
    elif mutation == "fixed_env":
        server["env"] = {"ALBU_MCP_ALLOWED_ROOTS": "/example/images"}

    plugin_path = tmp_path / ".codex-plugin" / "plugin.json"
    plugin_path.parent.mkdir()
    plugin_path.write_text(json.dumps(plugin), encoding="utf-8")
    mcp_path = tmp_path / ".mcp.json"
    mcp_path.write_text(json.dumps(mcp), encoding="utf-8")
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text('[project]\nversion = "1.15.0"\n', encoding="utf-8")
    skill_path = tmp_path / "skills" / "albumentationsx-mcp" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("---\nname: albumentationsx-mcp\n---\n", encoding="utf-8")
    return plugin_path, mcp_path, pyproject_path
