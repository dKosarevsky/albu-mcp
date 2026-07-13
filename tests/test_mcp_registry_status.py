import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

from scripts import check_mcp_registry_status as registry_status
from scripts.check_mcp_registry_status import (
    McpRegistryCheckOptions,
    McpRegistryStatusReport,
    validate_mcp_registry_status,
)

_DESCRIPTION = "AlbumentationsX MCP for batch previews, compare preview runs, segmentation masks, and exports."
_ICON_SRC = "https://avatars.githubusercontent.com/u/57894582?s=200&v=4"


def test_mcp_registry_status_accepts_active_latest_entry(tmp_path: Path) -> None:
    server_json_path = _write_server_json(tmp_path)
    response_path = _write_registry_response(tmp_path)

    report = validate_mcp_registry_status(
        server_json_path=server_json_path,
        registry_response_path=response_path,
    )

    assert report.name == "io.github.dKosarevsky/albu-mcp"
    assert report.version == "1.14.0"
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
    assert "1.14.0" in result.stdout


def test_mcp_registry_status_wraps_registry_timeouts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server_json_path = _write_server_json(tmp_path)

    def raise_timeout(*_args: object, **_kwargs: object) -> None:
        message = "read operation timed out"
        raise TimeoutError(message)

    monkeypatch.setattr(urllib.request, "urlopen", raise_timeout)

    with pytest.raises(ValueError, match="Could not fetch MCP Registry metadata"):
        validate_mcp_registry_status(server_json_path=server_json_path, timeout=0.01)


def test_mcp_registry_status_reports_retryable_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = McpRegistryStatusReport(
        name="io.github.dKosarevsky/albu-mcp",
        version="1.14.0",
        package="albumentationsx-mcp",
        package_version="1.14.0",
        status="active",
        is_latest=True,
    )
    outcomes: list[McpRegistryStatusReport | ValueError] = [
        ValueError("The read operation timed out"),
        expected,
    ]
    delays: list[float] = []
    monkeypatch.setattr(registry_status, "_validate_once", lambda _options: outcomes.pop(0))
    monkeypatch.setattr(registry_status.time, "sleep", delays.append)

    report = registry_status._validate_with_retries(
        McpRegistryCheckOptions(
            server_json_path=_write_server_json(tmp_path),
            registry_response_path=None,
            registry_url=None,
            timeout=90,
            retries=2,
            retry_delay=15,
        )
    )

    assert report == expected
    assert delays == [15]
    captured = capsys.readouterr()
    assert "attempt 1/2 failed" in captured.err
    assert "The read operation timed out" in captured.err
    assert "retrying in 15 seconds" in captured.err


def test_mcp_registry_status_preserves_final_semantic_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    def fail_with_mismatch(_options: McpRegistryCheckOptions) -> ValueError:
        nonlocal attempts
        attempts += 1
        return ValueError("MCP Registry icons does not match server.json")

    monkeypatch.setattr(registry_status, "_validate_once", fail_with_mismatch)
    monkeypatch.setattr(registry_status.time, "sleep", lambda _delay: None)

    with pytest.raises(ValueError, match="icons does not match"):
        registry_status._validate_with_retries(
            McpRegistryCheckOptions(
                server_json_path=_write_server_json(tmp_path),
                registry_response_path=None,
                registry_url=None,
                timeout=90,
                retries=3,
                retry_delay=0,
            )
        )

    assert attempts == 3


@pytest.mark.parametrize(
    "workflow_path",
    [
        Path(".github/workflows/release.yml"),
        Path(".github/workflows/publish-mcp.yml"),
        Path(".github/workflows/mcp-registry-watchdog.yml"),
    ],
)
def test_mcp_registry_workflows_allow_slow_reads(workflow_path: Path) -> None:
    workflow = workflow_path.read_text(encoding="utf-8")

    assert "check_mcp_registry_status.py --retries 3 --retry-delay 15 --timeout 90" in workflow


def _write_server_json(tmp_path: Path) -> Path:
    server_json_path = tmp_path / "server.json"
    server_json_path.write_text(
        json.dumps(
            {
                "name": "io.github.dKosarevsky/albu-mcp",
                "title": "AlbumentationsX MCP",
                "description": _DESCRIPTION,
                "version": "1.14.0",
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
                        "version": "1.14.0",
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
                _registry_entry(version="1.14.0", is_latest=False),
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
    version = str(overrides.get("version", "1.14.0"))
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
