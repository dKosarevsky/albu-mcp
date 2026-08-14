"""Check that the public MCP Registry points at the current server.json release."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_DEFAULT_REGISTRY_BASE_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"
_DEFAULT_TIMEOUT_SECONDS = 90.0
_OFFICIAL_META_KEY = "io.modelcontextprotocol.registry/official"
_MAX_REGISTRY_PAGES = 100


class McpRegistryRetryableError(ValueError):
    """Raised when a later Registry read may produce a valid result."""


class McpRegistryFetchError(McpRegistryRetryableError):
    """Raised when remote Registry metadata could not be read reliably."""


class McpRegistryPropagationError(McpRegistryRetryableError):
    """Raised while a newly published Registry entry is still converging."""


@dataclass(frozen=True)
class McpRegistryStatusReport:
    """Public Registry status for the local server metadata version."""

    name: str
    version: str
    package: str
    package_version: str
    status: str
    is_latest: bool


@dataclass(frozen=True)
class McpRegistryCheckOptions:
    """CLI options for a retryable Registry status check."""

    server_json_path: Path
    registry_response_path: Path | None
    registry_url: str | None
    timeout: float
    retries: int
    retry_delay: float


def validate_mcp_registry_status(
    *,
    server_json_path: Path = Path("server.json"),
    registry_response_path: Path | None = None,
    registry_url: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT_SECONDS,
) -> McpRegistryStatusReport:
    """Return a Registry status report or raise ValueError with an actionable mismatch."""
    server = _read_json_object(server_json_path)
    package = _first_pypi_package(server, source=str(server_json_path))
    response = _registry_response(
        server_name=str(server["name"]),
        registry_response_path=registry_response_path,
        registry_url=registry_url,
        timeout=timeout,
    )
    entry = _current_registry_entry(response, server)
    registry_server = _server_object(entry)
    official = _official_meta(entry)
    status = str(official.get("status", ""))
    is_latest = official.get("isLatest")

    if status == "pending":
        msg = f"MCP Registry entry for {server['name']} {server['version']} has status 'pending'; still converging"
        raise McpRegistryPropagationError(msg)
    if status != "active":
        msg = f"MCP Registry entry for {server['name']} {server['version']} has status {status!r}, expected 'active'"
        raise ValueError(msg)
    if is_latest is not True:
        msg = f"MCP Registry entry for {server['name']} {server['version']} must have isLatest=true"
        raise ValueError(msg)

    _compare_optional_field(server, registry_server, "title")
    _compare_optional_field(server, registry_server, "description")
    _compare_optional_field(server, registry_server, "websiteUrl")
    _compare_optional_field(server, registry_server, "icons")
    _compare_repository(server, registry_server)
    registry_package = _first_pypi_package(registry_server, source="MCP Registry response")
    if registry_package.get("identifier") != package.get("identifier"):
        msg = (
            "MCP Registry package identifier "
            f"{registry_package.get('identifier')!r} does not match server.json {package.get('identifier')!r}"
        )
        raise ValueError(msg)
    if registry_package.get("version") != package.get("version"):
        msg = (
            "MCP Registry package version "
            f"{registry_package.get('version')!r} does not match server.json {package.get('version')!r}"
        )
        raise ValueError(msg)
    if registry_package.get("transport") != package.get("transport"):
        msg = "MCP Registry package transport does not match server.json"
        raise ValueError(msg)

    return McpRegistryStatusReport(
        name=str(server["name"]),
        version=str(server["version"]),
        package=str(package["identifier"]),
        package_version=str(package["version"]),
        status=status,
        is_latest=True,
    )


def main() -> None:
    """CLI entrypoint for release and watchdog workflows."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-json", type=Path, default=Path("server.json"))
    parser.add_argument("--registry-response", type=Path, help="Optional saved Registry response JSON for tests.")
    parser.add_argument("--registry-url", help="Optional Registry search URL override.")
    parser.add_argument("--timeout", type=float, default=_DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--retry-delay", type=float, default=10)
    args = parser.parse_args()

    try:
        report = _validate_with_retries(
            McpRegistryCheckOptions(
                server_json_path=args.server_json,
                registry_response_path=args.registry_response,
                registry_url=args.registry_url,
                timeout=args.timeout,
                retries=args.retries,
                retry_delay=args.retry_delay,
            )
        )
    except (TypeError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc

    sys.stdout.write(
        f"MCP Registry latest is active for {report.name} {report.version} "
        f"({report.package}=={report.package_version})\n"
    )


def _validate_with_retries(options: McpRegistryCheckOptions) -> McpRegistryStatusReport:
    attempts = max(options.retries, 1)
    last_error: McpRegistryRetryableError | None = None
    for attempt in range(1, attempts + 1):
        result = _validate_once(options)
        if isinstance(result, McpRegistryStatusReport):
            return result
        if not isinstance(result, McpRegistryRetryableError):
            raise result
        last_error = result
        if attempt < attempts:
            sys.stderr.write(
                f"MCP Registry status check attempt {attempt}/{attempts} failed: {result}; "
                f"retrying in {options.retry_delay:g} seconds\n"
            )
            time.sleep(options.retry_delay)
    if last_error is None:
        msg = "MCP Registry status check did not run"
        raise ValueError(msg)
    raise last_error


def _validate_once(options: McpRegistryCheckOptions) -> McpRegistryStatusReport | McpRegistryRetryableError:
    try:
        return validate_mcp_registry_status(
            server_json_path=options.server_json_path,
            registry_response_path=options.registry_response_path,
            registry_url=options.registry_url,
            timeout=options.timeout,
        )
    except McpRegistryRetryableError as exc:
        return exc


def _registry_response(
    *,
    server_name: str,
    registry_response_path: Path | None,
    registry_url: str | None,
    timeout: float,
) -> dict[str, Any]:
    if registry_response_path is not None:
        return _read_json_object(registry_response_path)
    return _fetch_registry_response(registry_url or _registry_search_url(server_name), timeout=timeout)


def _registry_search_url(server_name: str) -> str:
    return f"{_DEFAULT_REGISTRY_BASE_URL}?search={urllib.parse.quote(server_name)}"


def _fetch_registry_response(registry_url: str, *, timeout: float) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(registry_url)
    if parsed.scheme != "https":
        msg = f"MCP Registry URL must use https, got {registry_url!r}"
        raise ValueError(msg)

    servers: list[Any] = []
    seen_cursors: set[str] = set()
    page_url = registry_url
    for _page_number in range(1, _MAX_REGISTRY_PAGES + 1):
        payload = _fetch_registry_page(page_url, timeout=timeout)
        page_servers = payload.get("servers")
        if not isinstance(page_servers, list):
            msg = f"MCP Registry response from {page_url} must contain a servers list"
            raise McpRegistryFetchError(msg)
        servers.extend(page_servers)

        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            msg = f"MCP Registry response from {page_url} must contain a metadata object"
            raise McpRegistryFetchError(msg)
        cursor = metadata.get("nextCursor")
        if cursor is None:
            return {"servers": servers, "metadata": {"count": len(servers)}}
        if not isinstance(cursor, str) or not cursor:
            msg = f"MCP Registry response from {page_url} contains an invalid nextCursor"
            raise McpRegistryFetchError(msg)
        if cursor in seen_cursors:
            msg = f"MCP Registry response repeated cursor {cursor!r}"
            raise McpRegistryFetchError(msg)
        seen_cursors.add(cursor)
        page_url = _registry_url_with_cursor(registry_url, cursor)

    msg = f"MCP Registry response exceeded {_MAX_REGISTRY_PAGES} pages"
    raise McpRegistryFetchError(msg)


def _fetch_registry_page(registry_url: str, *, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(registry_url, timeout=timeout) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except (TimeoutError, urllib.error.URLError) as exc:
        msg = f"Could not fetch MCP Registry metadata from {registry_url}: {exc}"
        raise McpRegistryFetchError(msg) from exc
    except json.JSONDecodeError as exc:
        msg = f"MCP Registry response from {registry_url} is not valid JSON: {exc.msg}"
        raise McpRegistryFetchError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"MCP Registry response from {registry_url} must be a JSON object"
        raise McpRegistryFetchError(msg)
    return payload


def _registry_url_with_cursor(registry_url: str, cursor: str) -> str:
    parsed = urllib.parse.urlparse(registry_url)
    query = [(name, value) for name, value in urllib.parse.parse_qsl(parsed.query) if name != "cursor"]
    query.append(("cursor", cursor))
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"{path}: invalid JSON: {exc.msg}"
        raise ValueError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"{path}: expected a JSON object"
        raise TypeError(msg)
    return payload


def _current_registry_entry(response: dict[str, Any], server: dict[str, Any]) -> dict[str, Any]:
    name = str(server["name"])
    version = str(server["version"])
    entries = [entry for entry in response.get("servers", []) if _server_object(entry).get("name") == name]
    if not entries:
        msg = f"MCP Registry response does not include server {name!r}"
        raise McpRegistryPropagationError(msg)

    latest_entries = [entry for entry in entries if _official_meta(entry).get("isLatest") is True]
    if len(latest_entries) > 1:
        msg = f"MCP Registry marks multiple {name!r} entries as isLatest=true"
        raise ValueError(msg)

    current_entries = [entry for entry in entries if _server_object(entry).get("version") == version]
    if not current_entries:
        versions = ", ".join(sorted(str(_server_object(entry).get("version")) for entry in entries))
        msg = f"MCP Registry response does not include {name} {version}; available versions: {versions}"
        raise McpRegistryPropagationError(msg)
    current = current_entries[0]
    if _official_meta(current).get("isLatest") is not True:
        latest_versions = ", ".join(str(_server_object(entry).get("version")) for entry in latest_entries) or "none"
        msg = f"MCP Registry entry for {name} {version} must have isLatest=true; latest versions: {latest_versions}"
        raise McpRegistryPropagationError(msg)
    return current


def _server_object(entry: Any) -> dict[str, Any]:
    if isinstance(entry, dict) and isinstance(entry.get("server"), dict):
        return entry["server"]
    return {}


def _official_meta(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        return {}
    meta = entry.get("_meta")
    if not isinstance(meta, dict):
        return {}
    official = meta.get(_OFFICIAL_META_KEY)
    if not isinstance(official, dict):
        return {}
    return official


def _first_pypi_package(server: dict[str, Any], *, source: str) -> dict[str, Any]:
    for package in server.get("packages", []):
        if isinstance(package, dict) and package.get("registryType") == "pypi":
            return package
    msg = f"{source} does not contain a PyPI package entry"
    raise ValueError(msg)


def _compare_optional_field(local_server: dict[str, Any], registry_server: dict[str, Any], field: str) -> None:
    if field in local_server and registry_server.get(field) != local_server[field]:
        msg = f"MCP Registry {field} does not match server.json"
        raise ValueError(msg)


def _compare_repository(local_server: dict[str, Any], registry_server: dict[str, Any]) -> None:
    local_repository = local_server.get("repository")
    if local_repository is None:
        return
    if registry_server.get("repository") != local_repository:
        msg = "MCP Registry repository does not match server.json"
        raise ValueError(msg)


if __name__ == "__main__":
    main()
