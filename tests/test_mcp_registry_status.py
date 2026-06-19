import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_mcp_registry_status import validate_mcp_registry_status

_DESCRIPTION = "AlbumentationsX MCP for batch previews, compare preview runs, feedback, scoring, and reports."
_ICON_SRC = "https://avatars.githubusercontent.com/u/57894582?s=200&v=4"


def test_mcp_registry_status_accepts_active_latest_entry(tmp_path: Path) -> None:
    server_json_path = _write_server_json(tmp_path)
    response_path = _write_registry_response(tmp_path)

    report = validate_mcp_registry_status(
        server_json_path=server_json_path,
        registry_response_path=response_path,
    )

    assert report.name == "io.github.dKosarevsky/albu-mcp"
    assert report.version == "1.10.0"
    assert report.package == "albumentationsx-mcp"
    assert report.status == "active"
    assert report.is_latest is True


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("stale_latest", "isLatest=true"),
        ("pending_status", "status"),
        ("wrong_package", "package identifier"),
        ("wrong_package_version", "package version"),
        ("wrong_icon", "icons"),
    ],
)
def test_mcp_registry_status_rejects_stale_or_mismatched_registry_payloads(
    tmp_path: Path,
    case: str,
    message: str,
) -> None:
    server_json_path = _write_server_json(tmp_path)
    response_path = _write_registry_response(tmp_path, payload=_registry_payload_for_case(case))

    with pytest.raises(ValueError, match=message):
        validate_mcp_registry_status(
            server_json_path=server_json_path,
            registry_response_path=response_path,
        )


def test_mcp_registry_status_cli_accepts_registry_response_fixture(tmp_path: Path) -> None:
    server_json_path = _write_server_json(tmp_path)
    response_path = _write_registry_response(tmp_path)

    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/check_mcp_registry_status.py",
            "--server-json",
            str(server_json_path),
            "--registry-response",
            str(response_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "MCP Registry latest is active" in result.stdout
    assert "1.10.0" in result.stdout


def _write_server_json(tmp_path: Path) -> Path:
    server_json_path = tmp_path / "server.json"
    server_json_path.write_text(
        json.dumps(
            {
                "name": "io.github.dKosarevsky/albu-mcp",
                "title": "AlbumentationsX MCP",
                "description": _DESCRIPTION,
                "version": "1.10.0",
                "websiteUrl": "https://github.com/dKosarevsky/albu-mcp#readme",
                "icons": [
                    {
                        "src": _ICON_SRC,
                        "mimeType": "image/png",
                        "sizes": ["200x200"],
                    }
                ],
                "repository": {
                    "url": "https://github.com/dKosarevsky/albu-mcp",
                    "source": "github",
                    "id": "1268159067",
                },
                "packages": [
                    {
                        "registryType": "pypi",
                        "identifier": "albumentationsx-mcp",
                        "version": "1.10.0",
                        "transport": {"type": "stdio"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return server_json_path


def _write_registry_response(tmp_path: Path, *, payload: dict[str, object] | None = None) -> Path:
    response_path = tmp_path / "registry-response.json"
    response_path.write_text(
        json.dumps(payload or {"servers": [_registry_entry()], "metadata": {"count": 1}}),
        encoding="utf-8",
    )
    return response_path


def _registry_payload_for_case(case: str) -> dict[str, object]:
    if case == "stale_latest":
        return {
            "servers": [
                _registry_entry(version="1.9.0", is_latest=True),
                _registry_entry(version="1.10.0", is_latest=False),
            ]
        }
    if case == "pending_status":
        return {"servers": [_registry_entry(status="pending")]}
    if case == "wrong_package":
        return {"servers": [_registry_entry(package_identifier="wrong-package")]}
    if case == "wrong_package_version":
        return {"servers": [_registry_entry(package_version="1.9.0")]}
    if case == "wrong_icon":
        return {"servers": [_registry_entry(icon_src="https://example.com/wrong.png")]}
    raise AssertionError(case)


def _registry_entry(**overrides: object) -> dict[str, object]:
    version = str(overrides.get("version", "1.10.0"))
    package_version = overrides.get("package_version") or version
    return {
        "server": {
            "name": "io.github.dKosarevsky/albu-mcp",
            "title": "AlbumentationsX MCP",
            "description": _DESCRIPTION,
            "version": version,
            "websiteUrl": "https://github.com/dKosarevsky/albu-mcp#readme",
            "icons": [
                {"src": str(overrides.get("icon_src", _ICON_SRC)), "mimeType": "image/png", "sizes": ["200x200"]}
            ],
            "repository": {
                "url": "https://github.com/dKosarevsky/albu-mcp",
                "source": "github",
                "id": "1268159067",
            },
            "packages": [
                {
                    "registryType": "pypi",
                    "identifier": str(overrides.get("package_identifier", "albumentationsx-mcp")),
                    "version": str(package_version),
                    "transport": {"type": "stdio"},
                }
            ],
        },
        "_meta": {
            "io.modelcontextprotocol.registry/official": {
                "status": str(overrides.get("status", "active")),
                "isLatest": bool(overrides.get("is_latest", True)),
            }
        },
    }
