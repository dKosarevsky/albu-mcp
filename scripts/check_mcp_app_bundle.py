"""Verify that Python distributions contain the self-contained preview review MCP App."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

_WHEEL_APP_PATH = "albumentationsx_mcp/ui/preview-review.html"
_SDIST_APP_SUFFIX = f"/src/{_WHEEL_APP_PATH}"
_APP_MARKER = 'data-albumentationsx-mcp-app="preview-review"'
_ACTIVE_URL_ATTRIBUTES = {"action", "data", "formaction", "href", "poster", "src", "srcset"}
_CSS_URL_PATTERN = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE | re.DOTALL)
_SCRIPT_LITERAL_REFERENCE_PATTERN = re.compile(
    r"\b(?:fetch|import|importScripts|Worker|SharedWorker)\s*\(\s*(['\"`])([^'\"`]+)\1",
    re.IGNORECASE,
)
_SOURCE_MAP_PATTERN = re.compile(r"source(?:Mapping)?URL\s*=\s*([^\s*]+)", re.IGNORECASE)
_REQUIRED_SDIST_SOURCE_SUFFIXES = {
    "/mcp-app/package.json",
    "/mcp-app/package-lock.json",
    "/mcp-app/preview-review.html",
    "/mcp-app/src/main.ts",
    "/mcp-app/src/review-state.ts",
    "/mcp-app/src/styles.css",
    "/mcp-app/tsconfig.json",
    "/mcp-app/vite.config.ts",
}


class McpAppBundleError(ValueError):
    """Raised when a distribution has an incomplete or unsafe MCP App bundle."""


class _AppHTMLInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.remote_references: list[str] = []
        self.script_count = 0
        self._inside_inline_script = False
        self._inline_script_chunks: list[str] = []
        self._inside_style = False
        self._style_chunks: list[str] = []

    @property
    def inline_script_text(self) -> str:
        return "".join(self._inline_script_chunks)

    @property
    def style_text(self) -> str:
        return "".join(self._style_chunks)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): value for name, value in attrs}
        for name in _ACTIVE_URL_ATTRIBUTES:
            value = attributes.get(name)
            if value is not None and not _is_embedded_reference(value, attribute=name):
                self.remote_references.append(value)
        if tag.lower() == "script":
            self.script_count += 1
            self._inside_inline_script = attributes.get("src") is None
        if tag.lower() == "style":
            self._inside_style = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            self._inside_inline_script = False
        if tag.lower() == "style":
            self._inside_style = False

    def handle_data(self, data: str) -> None:
        if self._inside_inline_script:
            self._inline_script_chunks.append(data)
        if self._inside_style:
            self._style_chunks.append(data)


def inspect_wheel(path: Path) -> dict[str, Any]:
    """Inspect the packaged MCP App in one wheel and return a deterministic receipt."""
    try:
        with zipfile.ZipFile(path) as archive:
            entries = [item for item in archive.infolist() if item.filename == _WHEEL_APP_PATH and not item.is_dir()]
            if len(entries) != 1:
                msg = f"wheel must contain exactly one {_WHEEL_APP_PATH!r}; found {len(entries)}"
                raise McpAppBundleError(msg)
            html_bytes = archive.read(entries[0])
    except (OSError, zipfile.BadZipFile) as exc:
        msg = f"could not read wheel {path}: {exc}"
        raise McpAppBundleError(msg) from exc

    _validate_app_html(html_bytes, source=path.name)
    return _receipt(path, _WHEEL_APP_PATH, html_bytes)


def inspect_sdist(path: Path) -> dict[str, Any]:
    """Inspect the packaged app and reproducible frontend sources in one sdist."""
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            files = [item for item in archive.getmembers() if item.isfile()]
            app_entries = [item for item in files if item.name.endswith(_SDIST_APP_SUFFIX)]
            if len(app_entries) != 1:
                msg = f"sdist must contain exactly one packaged MCP App; found {len(app_entries)}"
                raise McpAppBundleError(msg)
            source_suffixes = {
                suffix
                for suffix in _REQUIRED_SDIST_SOURCE_SUFFIXES
                if any(item.name.endswith(suffix) for item in files)
            }
            missing = sorted(_REQUIRED_SDIST_SOURCE_SUFFIXES - source_suffixes)
            if missing:
                msg = f"sdist is missing MCP App source files: {', '.join(missing)}"
                raise McpAppBundleError(msg)
            extracted = archive.extractfile(app_entries[0])
            if extracted is None:
                msg = "sdist MCP App entry could not be read"
                raise McpAppBundleError(msg)
            html_bytes = extracted.read()
            app_path = app_entries[0].name
    except (OSError, tarfile.TarError) as exc:
        msg = f"could not read sdist {path}: {exc}"
        raise McpAppBundleError(msg) from exc

    _validate_app_html(html_bytes, source=path.name)
    receipt = _receipt(path, app_path, html_bytes)
    receipt["source_file_count"] = len(_REQUIRED_SDIST_SOURCE_SUFFIXES)
    return receipt


def check_distributions(dist_dir: Path) -> dict[str, dict[str, Any]]:
    """Check the single wheel and sdist expected in a release output directory."""
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        msg = f"expected one wheel and one sdist in {dist_dir}; found {len(wheels)} wheel(s), {len(sdists)} sdist(s)"
        raise McpAppBundleError(msg)
    receipt = {"wheel": inspect_wheel(wheels[0]), "sdist": inspect_sdist(sdists[0])}
    if receipt["wheel"]["sha256"] != receipt["sdist"]["sha256"]:
        msg = "wheel and sdist MCP App payloads differ"
        raise McpAppBundleError(msg)
    return receipt


def _validate_app_html(html_bytes: bytes, *, source: str) -> None:
    try:
        html = html_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        msg = f"MCP App in {source} is not UTF-8"
        raise McpAppBundleError(msg) from exc
    if _APP_MARKER not in html:
        msg = f"MCP App in {source} is missing the preview-review marker"
        raise McpAppBundleError(msg)

    inspector = _AppHTMLInspector()
    inspector.feed(html)
    if inspector.remote_references:
        msg = f"MCP App in {source} contains an external asset reference"
        raise McpAppBundleError(msg)
    if inspector.script_count != 1 or not inspector.inline_script_text.strip():
        msg = f"MCP App in {source} must contain exactly one non-empty inline script"
        raise McpAppBundleError(msg)
    if _contains_external_css_reference(inspector.style_text) or _contains_external_script_reference(
        inspector.inline_script_text
    ):
        msg = f"MCP App in {source} contains an active remote dependency"
        raise McpAppBundleError(msg)


def _is_embedded_reference(value: str, *, attribute: str = "") -> bool:
    reference = value.strip().lower()
    if attribute == "srcset":
        return not reference
    return not reference or reference.startswith(("#", "data:", "blob:")) or reference == "about:blank"


def _contains_external_css_reference(css: str) -> bool:
    if re.search(r"@import\b", css, re.IGNORECASE):
        return True
    return any(not _is_embedded_reference(match.group(2)) for match in _CSS_URL_PATTERN.finditer(css))


def _contains_external_script_reference(script: str) -> bool:
    literal_references = (match.group(2) for match in _SCRIPT_LITERAL_REFERENCE_PATTERN.finditer(script))
    source_maps = (match.group(1).strip("'\"") for match in _SOURCE_MAP_PATTERN.finditer(script))
    return any(not _is_embedded_reference(reference) for reference in (*literal_references, *source_maps))


def _receipt(distribution: Path, app_path: str, html_bytes: bytes) -> dict[str, Any]:
    return {
        "distribution": distribution.name,
        "app_path": app_path,
        "size_bytes": len(html_bytes),
        "sha256": hashlib.sha256(html_bytes).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    """Run the distribution check and print a machine-readable receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    try:
        receipt = check_distributions(args.dist_dir)
    except McpAppBundleError as exc:
        sys.stderr.write(f"MCP App bundle check failed: {exc}\n")
        return 1
    sys.stdout.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
