from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.check_mcp_app_bundle import McpAppBundleError, inspect_sdist, inspect_wheel

_APP_HTML = b"""<!doctype html>
<html data-albumentationsx-mcp-app="preview-review">
<head><style>body { color: CanvasText; }</style></head>
<body><script>globalThis.__mcpApp = true;</script></body>
</html>
"""


def test_inspect_wheel_accepts_one_self_contained_mcp_app(tmp_path: Path) -> None:
    wheel = tmp_path / "albumentationsx_mcp-1.18.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("albumentationsx_mcp/ui/preview-review.html", _APP_HTML)

    receipt = inspect_wheel(wheel)

    assert receipt["distribution"] == wheel.name
    assert receipt["app_path"] == "albumentationsx_mcp/ui/preview-review.html"
    assert receipt["size_bytes"] == len(_APP_HTML)
    assert len(receipt["sha256"]) == 64


@pytest.mark.parametrize(
    "html",
    [
        b"<html><script>missing marker</script></html>",
        b'<html data-albumentationsx-mcp-app="preview-review"><script src="https://cdn.example/app.js"></script></html>',
        b'<html data-albumentationsx-mcp-app="preview-review"><link href="//cdn.example/app.css"></html>',
    ],
)
def test_inspect_wheel_rejects_incomplete_or_remote_apps(tmp_path: Path, html: bytes) -> None:
    wheel = tmp_path / "invalid.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("albumentationsx_mcp/ui/preview-review.html", html)

    with pytest.raises(McpAppBundleError):
        inspect_wheel(wheel)


def test_inspect_sdist_requires_app_source_and_packaged_output(tmp_path: Path) -> None:
    sdist = tmp_path / "albumentationsx_mcp-1.18.0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        files = {
            "albumentationsx_mcp-1.18.0/src/albumentationsx_mcp/ui/preview-review.html": _APP_HTML,
            "albumentationsx_mcp-1.18.0/mcp-app/package.json": b"{}",
            "albumentationsx_mcp-1.18.0/mcp-app/package-lock.json": b"{}",
            "albumentationsx_mcp-1.18.0/mcp-app/preview-review.html": b"<main></main>",
            "albumentationsx_mcp-1.18.0/mcp-app/src/main.ts": b"export {};",
            "albumentationsx_mcp-1.18.0/mcp-app/src/review-state.ts": b"export {};",
            "albumentationsx_mcp-1.18.0/mcp-app/src/styles.css": b":root {}",
            "albumentationsx_mcp-1.18.0/mcp-app/tsconfig.json": b"{}",
            "albumentationsx_mcp-1.18.0/mcp-app/vite.config.ts": b"export {};",
        }
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))

    receipt = inspect_sdist(sdist)

    assert receipt["distribution"] == sdist.name
    assert receipt["source_file_count"] == 8
    assert receipt["size_bytes"] == len(_APP_HTML)


def test_inspect_sdist_rejects_missing_frontend_source(tmp_path: Path) -> None:
    sdist = tmp_path / "invalid.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        info = tarfile.TarInfo("invalid/src/albumentationsx_mcp/ui/preview-review.html")
        info.size = len(_APP_HTML)
        archive.addfile(info, io.BytesIO(_APP_HTML))

    with pytest.raises(McpAppBundleError, match="missing MCP App source"):
        inspect_sdist(sdist)
