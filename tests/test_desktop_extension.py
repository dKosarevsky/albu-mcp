from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import tomli

ROOT = Path(__file__).resolve().parents[1]
EXTENSION_ROOT = ROOT / "desktop-extension"
VALIDATOR_PATH = ROOT / "scripts" / "check_desktop_extension.py"
PROJECT = tomli.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
PROJECT_VERSION = PROJECT["version"]
EXPECTED_PACKAGE_PIN = f"albumentationsx-mcp=={PROJECT_VERSION}"
EXPECTED_ARGS = [
    "run",
    "--directory",
    "${__dirname}",
    "src/server.py",
    "--allowed-root",
    "${user_config.allowed_directory}",
    "--artifact-root",
    "${user_config.artifact_directory}",
]


def test_desktop_extension_exposes_bounded_uv_bundle() -> None:
    manifest_path = EXTENSION_ROOT / "manifest.json"
    bundle_project_path = EXTENSION_ROOT / "pyproject.toml"
    wrapper_path = EXTENSION_ROOT / "src" / "server.py"

    assert manifest_path.is_file()
    assert bundle_project_path.is_file()
    assert wrapper_path.is_file()
    assert (EXTENSION_ROOT / "icon.png").is_file()
    assert (EXTENSION_ROOT / ".mcpbignore").is_file()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bundle_project = tomli.loads(bundle_project_path.read_text(encoding="utf-8"))["project"]

    assert manifest["$schema"].endswith("mcpb-manifest-v0.4.schema.json")
    assert manifest["manifest_version"] == "0.4"
    assert manifest["name"] == "albumentationsx-mcp"
    assert manifest["display_name"] == "AlbumentationsX MCP"
    assert manifest["version"] == PROJECT_VERSION
    assert manifest["server"]["type"] == "uv"
    assert manifest["server"]["entry_point"] == "src/server.py"
    assert manifest["server"]["mcp_config"] == {
        "command": "uv",
        "args": EXPECTED_ARGS,
        "env": {"ALBU_MCP_MAX_PREVIEW_RUNS": "${user_config.max_preview_runs}"},
    }
    assert manifest["tools_generated"] is True

    user_config = manifest["user_config"]
    assert list(user_config) == ["allowed_directory", "artifact_directory", "max_preview_runs"]
    for key in ["allowed_directory", "artifact_directory"]:
        assert user_config[key]["type"] == "directory"
        assert user_config[key]["required"] is True
        assert "default" not in user_config[key]
    assert user_config["max_preview_runs"] == {
        "type": "number",
        "title": "Maximum preview runs",
        "description": "Maximum number of indexed preview runs retained by the local server.",
        "default": 100,
        "min": 1,
        "max": 500,
        "required": True,
    }

    assert bundle_project["version"] == PROJECT_VERSION
    assert bundle_project["dependencies"] == [EXPECTED_PACKAGE_PIN]
    assert wrapper_path.read_text(encoding="utf-8") == (
        '"""Run the published AlbumentationsX MCP package inside a UV MCP Bundle."""\n\n'
        "from albumentationsx_mcp.cli import main\n\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


def test_desktop_extension_validator_cli_accepts_repository_bundle() -> None:
    assert VALIDATOR_PATH.is_file()

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        f"Claude Desktop MCP bundle is valid: version {PROJECT_VERSION}, dependency {EXPECTED_PACKAGE_PIN}\n"
    )


def test_desktop_extension_validator_accepts_matching_safe_bundle(tmp_path: Path) -> None:
    validator = _load_validator()
    extension_root, pyproject_path = _write_bundle(tmp_path)

    report = validator.validate_desktop_extension(
        extension_root=extension_root,
        pyproject_path=pyproject_path,
    )

    assert report.version == PROJECT_VERSION
    assert report.name == "albumentationsx-mcp"
    assert report.package_pin == EXPECTED_PACKAGE_PIN
    assert report.allowed_directory_configured is True
    assert report.artifact_directory_configured is True


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("manifest_version", "manifest version '0.0.0' does not match project version"),
        ("dependency_pin", "bundle dependency must be pinned to"),
        ("server_type", "MCPB server type must be 'uv'"),
        ("entry_point_escape", "MCPB entry point must be 'src/server.py'"),
        ("missing_allowed_directory", "user_config must define exactly"),
        ("optional_artifact_directory", "artifact_directory must be required"),
        ("broad_directory_default", "allowed_directory must not define a default"),
        ("unbounded_retention", "max_preview_runs bounds must be 1..500"),
        ("implicit_root_arg", "MCPB launch args must match the bounded directory contract"),
        ("fixed_secret", "MCPB source contains forbidden file"),
        ("wrapper_drift", "MCPB wrapper must delegate directly"),
        ("missing_icon", "MCPB icon is missing"),
    ],
)
def test_desktop_extension_validator_rejects_unsafe_or_drifted_bundle(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    validator = _load_validator()
    extension_root, pyproject_path = _write_bundle(tmp_path, mutation=mutation)

    with pytest.raises(ValueError, match=message):
        validator.validate_desktop_extension(
            extension_root=extension_root,
            pyproject_path=pyproject_path,
        )


def _load_validator() -> ModuleType:
    assert VALIDATOR_PATH.is_file(), f"missing validator: {VALIDATOR_PATH}"
    spec = importlib.util.spec_from_file_location("check_desktop_extension", VALIDATOR_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_bundle(tmp_path: Path, *, mutation: str | None = None) -> tuple[Path, Path]:
    extension_root = tmp_path / "desktop-extension"
    source_root = extension_root / "src"
    source_root.mkdir(parents=True)
    manifest = _safe_manifest()
    bundle_project: dict[str, Any] = {
        "name": "albumentationsx-mcp-desktop-extension",
        "version": PROJECT_VERSION,
        "requires-python": ">=3.10",
        "dependencies": [EXPECTED_PACKAGE_PIN],
    }
    wrapper = (
        '"""Run the published AlbumentationsX MCP package inside a UV MCP Bundle."""\n\n'
        "from albumentationsx_mcp.cli import main\n\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )

    if mutation == "manifest_version":
        manifest["version"] = "0.0.0"
    elif mutation == "dependency_pin":
        bundle_project["dependencies"] = ["albumentationsx-mcp>=1"]
    elif mutation == "server_type":
        manifest["server"]["type"] = "python"
    elif mutation == "entry_point_escape":
        manifest["server"]["entry_point"] = "../server.py"
    elif mutation == "missing_allowed_directory":
        del manifest["user_config"]["allowed_directory"]
    elif mutation == "optional_artifact_directory":
        manifest["user_config"]["artifact_directory"]["required"] = False
    elif mutation == "broad_directory_default":
        manifest["user_config"]["allowed_directory"]["default"] = "${HOME}"
    elif mutation == "unbounded_retention":
        manifest["user_config"]["max_preview_runs"]["max"] = 10000
    elif mutation == "implicit_root_arg":
        manifest["server"]["mcp_config"]["args"].extend(["--allowed-root", "${HOME}"])
    elif mutation == "fixed_secret":
        (extension_root / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    elif mutation == "wrapper_drift":
        wrapper = "print('not an MCP server')\n"

    (extension_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (extension_root / "pyproject.toml").write_text(_render_bundle_project(bundle_project), encoding="utf-8")
    (source_root / "server.py").write_text(wrapper, encoding="utf-8")
    (extension_root / ".mcpbignore").write_text(".venv/\n__pycache__/\n", encoding="utf-8")
    if mutation != "missing_icon":
        (extension_root / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")

    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(f'[project]\nversion = "{PROJECT_VERSION}"\n', encoding="utf-8")
    return extension_root, pyproject_path


def _safe_manifest() -> dict[str, Any]:
    return {
        "$schema": "https://raw.githubusercontent.com/modelcontextprotocol/mcpb/main/schemas/mcpb-manifest-v0.4.schema.json",
        "manifest_version": "0.4",
        "name": "albumentationsx-mcp",
        "display_name": "AlbumentationsX MCP",
        "version": PROJECT_VERSION,
        "description": "Preview and tune local computer-vision augmentations.",
        "author": {"name": "dKosarevsky"},
        "icon": "icon.png",
        "server": {
            "type": "uv",
            "entry_point": "src/server.py",
            "mcp_config": {
                "command": "uv",
                "args": EXPECTED_ARGS.copy(),
                "env": {"ALBU_MCP_MAX_PREVIEW_RUNS": "${user_config.max_preview_runs}"},
            },
        },
        "tools_generated": True,
        "user_config": {
            "allowed_directory": {
                "type": "directory",
                "title": "Allowed image directory",
                "description": "Only local root from which images and annotations may be read.",
                "required": True,
            },
            "artifact_directory": {
                "type": "directory",
                "title": "Preview artifact directory",
                "description": "Local root where generated previews and exports may be written.",
                "required": True,
            },
            "max_preview_runs": {
                "type": "number",
                "title": "Maximum preview runs",
                "description": "Maximum number of indexed preview runs retained by the local server.",
                "default": 100,
                "min": 1,
                "max": 500,
                "required": True,
            },
        },
    }


def _render_bundle_project(project: dict[str, Any]) -> str:
    dependencies = ", ".join(f'"{item}"' for item in project["dependencies"])
    return (
        "[project]\n"
        f'name = "{project["name"]}"\n'
        f'version = "{project["version"]}"\n'
        f'requires-python = "{project["requires-python"]}"\n'
        f"dependencies = [{dependencies}]\n"
    )
