import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_directory_presence import (
    DirectoryPresenceConfig,
    check_directory_presence,
    require_directory_sources,
)


def test_directory_presence_reports_official_missing_and_glama_present(tmp_path: Path) -> None:
    server_json = _write_server_json(tmp_path)
    official_response = _write_text(tmp_path / "official.json", json.dumps({"servers": [], "metadata": {"count": 0}}))
    glama_response = _write_text(
        tmp_path / "glama.html",
        '<a href="/mcp/servers/dKosarevsky/albu-mcp">AlbumentationsX MCP</a>',
    )

    report = check_directory_presence(
        DirectoryPresenceConfig(
            server_json_path=server_json,
            official_registry_response_path=official_response,
            glama_response_path=glama_response,
        )
    )

    assert report.ok is False
    assert report.by_id["official_registry"].listed is False
    assert "not listed" in report.by_id["official_registry"].message
    assert report.by_id["glama"].listed is True
    assert report.by_id["glama"].matched == "dKosarevsky/albu-mcp"


def test_directory_presence_accepts_official_and_glama_listing(tmp_path: Path) -> None:
    server_json = _write_server_json(tmp_path)
    official_response = _write_text(
        tmp_path / "official.json",
        json.dumps(
            {
                "servers": [
                    {
                        "server": {
                            "name": "io.github.dKosarevsky/albu-mcp",
                            "title": "AlbumentationsX MCP",
                        }
                    }
                ],
                "metadata": {"count": 1},
            }
        ),
    )
    glama_response = _write_text(
        tmp_path / "glama.html",
        '<a href="/mcp/servers/dKosarevsky/albu-mcp">AlbumentationsX MCP</a>',
    )

    report = check_directory_presence(
        DirectoryPresenceConfig(
            server_json_path=server_json,
            official_registry_response_path=official_response,
            glama_response_path=glama_response,
        )
    )

    assert report.ok is True
    assert [status.source_id for status in report.sources] == ["official_registry", "glama"]


def test_directory_presence_required_source_guard(tmp_path: Path) -> None:
    server_json = _write_server_json(tmp_path)
    official_response = _write_text(tmp_path / "official.json", json.dumps({"servers": [], "metadata": {"count": 0}}))
    glama_response = _write_text(
        tmp_path / "glama.html",
        '<a href="/mcp/servers/dKosarevsky/albu-mcp">AlbumentationsX MCP</a>',
    )
    report = check_directory_presence(
        DirectoryPresenceConfig(
            server_json_path=server_json,
            official_registry_response_path=official_response,
            glama_response_path=glama_response,
        )
    )

    with pytest.raises(ValueError, match="official_registry"):
        require_directory_sources(report, required_sources=["official_registry"])

    require_directory_sources(report, required_sources=["glama"])


def test_directory_presence_cli_outputs_json(tmp_path: Path) -> None:
    server_json = _write_server_json(tmp_path)
    official_response = _write_text(tmp_path / "official.json", json.dumps({"servers": [], "metadata": {"count": 0}}))
    glama_response = _write_text(
        tmp_path / "glama.html",
        '<a href="/mcp/servers/dKosarevsky/albu-mcp">AlbumentationsX MCP</a>',
    )

    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/check_directory_presence.py",
            "--server-json",
            str(server_json),
            "--official-registry-response",
            str(official_response),
            "--glama-response",
            str(glama_response),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["sources"][0]["source_id"] == "official_registry"
    assert payload["sources"][1]["source_id"] == "glama"


def test_network_growth_docs_are_linked() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    docs_index = Path("docs/INDEX.md").read_text(encoding="utf-8")
    docs = Path("docs/NETWORK_GROWTH.md").read_text(encoding="utf-8")

    assert "[NETWORK_GROWTH.md](NETWORK_GROWTH.md)" in docs_index
    assert "check_directory_presence.py" in docs_index
    assert "https://albumentations.ai/docs/integrations/mcp/" in readme
    assert "albumentations-team/AlbumentationsX/pull/289" in readme
    assert "AlbumentationsX/blob/main/docs/integrations/mcp.md" in docs
    assert "Official MCP Registry" in docs
    assert "Glama" in docs
    assert "https://github.com/albumentations-team/AlbumentationsX/pull/289" in docs
    assert "MERGED" in docs


def _write_server_json(tmp_path: Path) -> Path:
    return _write_text(
        tmp_path / "server.json",
        json.dumps(
            {
                "name": "io.github.dKosarevsky/albu-mcp",
                "title": "AlbumentationsX MCP",
                "repository": {"url": "https://github.com/dKosarevsky/albu-mcp"},
            }
        ),
    )


def _write_text(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path
