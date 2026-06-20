"""Report whether AlbumentationsX MCP is visible in public MCP directories."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_OFFICIAL_REGISTRY_BASE_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"
_GLAMA_BASE_URL = "https://glama.ai/mcp/servers"
_GITHUB_OWNER_REPO_PARTS = 2


@dataclass(frozen=True)
class DirectoryPresenceConfig:
    """Inputs for public directory presence checks."""

    server_json_path: Path = Path("server.json")
    official_registry_response_path: Path | None = None
    official_registry_url: str | None = None
    glama_response_path: Path | None = None
    glama_url: str | None = None
    timeout: float = 30


@dataclass(frozen=True)
class DirectorySourceStatus:
    """One public directory lookup result."""

    source_id: str
    name: str
    url: str
    listed: bool
    message: str
    matched: str = ""


@dataclass(frozen=True)
class DirectoryPresenceReport:
    """Aggregated public directory lookup result."""

    server_name: str
    title: str
    repository: str
    sources: list[DirectorySourceStatus]

    @property
    def ok(self) -> bool:
        """Return true only when every configured directory lists the project."""
        return all(source.listed for source in self.sources)

    @property
    def by_id(self) -> dict[str, DirectorySourceStatus]:
        """Return statuses keyed by stable source ID."""
        return {source.source_id: source for source in self.sources}


def check_directory_presence(config: DirectoryPresenceConfig | None = None) -> DirectoryPresenceReport:
    """Check official and third-party MCP directory visibility."""
    config = config or DirectoryPresenceConfig()
    server = _read_json_object(config.server_json_path)
    server_name = str(server["name"])
    title = str(server.get("title") or server_name)
    repository = _repository_url(server)
    owner_repo = _owner_repo_from_repository(repository, server_name=server_name)
    sources = [
        _check_official_registry(server_name=server_name, title=title, config=config),
        _check_glama(title=title, owner_repo=owner_repo, config=config),
    ]
    return DirectoryPresenceReport(server_name=server_name, title=title, repository=repository, sources=sources)


def require_directory_sources(report: DirectoryPresenceReport, *, required_sources: list[str]) -> None:
    """Raise when a required source is missing or not listed."""
    statuses = report.by_id
    missing = [
        source_id for source_id in required_sources if source_id not in statuses or not statuses[source_id].listed
    ]
    if missing:
        details = ", ".join(
            f"{source_id}: {statuses.get(source_id).message if source_id in statuses else 'unknown'}"
            for source_id in missing
        )
        msg = f"Required directory sources are not listed for {report.server_name}: {details}"
        raise ValueError(msg)


def main() -> None:
    """CLI entrypoint for manual directory visibility checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-json", type=Path, default=Path("server.json"))
    parser.add_argument("--official-registry-response", type=Path)
    parser.add_argument("--official-registry-url")
    parser.add_argument("--glama-response", type=Path)
    parser.add_argument("--glama-url")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument(
        "--require-source",
        action="append",
        default=[],
        choices=["official_registry", "glama"],
        help="Fail if the named directory source is not listed. Can be repeated.",
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    try:
        report = check_directory_presence(
            DirectoryPresenceConfig(
                server_json_path=args.server_json,
                official_registry_response_path=args.official_registry_response,
                official_registry_url=args.official_registry_url,
                glama_response_path=args.glama_response,
                glama_url=args.glama_url,
                timeout=args.timeout,
            )
        )
        require_directory_sources(report, required_sources=args.require_source)
    except (OSError, TypeError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc

    if args.format == "json":
        sys.stdout.write(json.dumps(_report_payload(report), indent=2))
        sys.stdout.write("\n")
        return
    _write_text_report(report)


def _check_official_registry(
    *,
    server_name: str,
    title: str,
    config: DirectoryPresenceConfig,
) -> DirectorySourceStatus:
    url = config.official_registry_url or _official_registry_search_url(server_name)
    response = (
        _read_json_object(config.official_registry_response_path)
        if config.official_registry_response_path is not None
        else _fetch_json_object(url, timeout=config.timeout)
    )
    entries = [_server_object(entry) for entry in response.get("servers", [])]
    matches = [entry for entry in entries if entry.get("name") == server_name]
    if not matches:
        return DirectorySourceStatus(
            source_id="official_registry",
            name="Official MCP Registry",
            url=url,
            listed=False,
            message=f"{server_name} is not listed",
        )
    matched_title = str(matches[0].get("title") or title)
    return DirectorySourceStatus(
        source_id="official_registry",
        name="Official MCP Registry",
        url=url,
        listed=True,
        message=f"{server_name} is listed",
        matched=matched_title,
    )


def _check_glama(*, title: str, owner_repo: str, config: DirectoryPresenceConfig) -> DirectorySourceStatus:
    url = config.glama_url or f"{_GLAMA_BASE_URL}/{owner_repo}"
    html = (
        config.glama_response_path.read_text(encoding="utf-8")
        if config.glama_response_path is not None
        else _fetch_text(url, timeout=config.timeout)
    )
    expected_path = f"/mcp/servers/{owner_repo}"
    if title not in html and expected_path not in html:
        return DirectorySourceStatus(
            source_id="glama",
            name="Glama",
            url=url,
            listed=False,
            message=f"{owner_repo} is not listed",
        )
    return DirectorySourceStatus(
        source_id="glama",
        name="Glama",
        url=url,
        listed=True,
        message=f"{owner_repo} is listed",
        matched=owner_repo,
    )


def _official_registry_search_url(server_name: str) -> str:
    return f"{_OFFICIAL_REGISTRY_BASE_URL}?search={urllib.parse.quote(server_name)}"


def _fetch_json_object(url: str, *, timeout: float) -> dict[str, Any]:
    return _json_object_from_text(_fetch_text(url, timeout=timeout), source=url)


def _fetch_text(url: str, *, timeout: float) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        msg = f"Directory URL must use https, got {url!r}"
        raise ValueError(msg)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            return response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        msg = f"Could not fetch directory metadata from {url}: {exc}"
        raise ValueError(msg) from exc


def _read_json_object(path: Path | None) -> dict[str, Any]:
    if path is None:
        msg = "JSON path is required"
        raise ValueError(msg)
    return _json_object_from_text(path.read_text(encoding="utf-8"), source=str(path))


def _json_object_from_text(text: str, *, source: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        msg = f"{source}: invalid JSON: {exc.msg}"
        raise ValueError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"{source}: expected a JSON object"
        raise TypeError(msg)
    return payload


def _server_object(entry: Any) -> dict[str, Any]:
    if isinstance(entry, dict) and isinstance(entry.get("server"), dict):
        return entry["server"]
    if isinstance(entry, dict):
        return entry
    return {}


def _repository_url(server: dict[str, Any]) -> str:
    repository = server.get("repository")
    if isinstance(repository, dict) and repository.get("url"):
        return str(repository["url"])
    return ""


def _owner_repo_from_repository(repository: str, *, server_name: str) -> str:
    parsed = urllib.parse.urlparse(repository)
    path = parsed.path.strip("/")
    if parsed.netloc == "github.com" and len(path.split("/")) >= _GITHUB_OWNER_REPO_PARTS:
        owner, repo = path.split("/")[:2]
        return f"{owner}/{repo}"
    if server_name.startswith("io.github."):
        return server_name.removeprefix("io.github.")
    msg = f"Could not infer GitHub owner/repo from repository {repository!r} or server name {server_name!r}"
    raise ValueError(msg)


def _report_payload(report: DirectoryPresenceReport) -> dict[str, Any]:
    return {
        "ok": report.ok,
        "server_name": report.server_name,
        "title": report.title,
        "repository": report.repository,
        "sources": [asdict(source) for source in report.sources],
    }


def _write_text_report(report: DirectoryPresenceReport) -> None:
    status = "listed" if report.ok else "partial"
    sys.stdout.write(f"directory presence for {report.server_name}: {status}\n")
    for source in report.sources:
        marker = "listed" if source.listed else "missing"
        sys.stdout.write(f"- {source.source_id}: {marker} - {source.message} ({source.url})\n")


if __name__ == "__main__":
    main()
