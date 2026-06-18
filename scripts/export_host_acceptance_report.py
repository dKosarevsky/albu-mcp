"""Export reviewable host acceptance evidence without claiming manual UI runs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Literal

ReportFormat = Literal["markdown", "json"]

_PROJECT_FIELD_PATTERN = re.compile(r'(?m)^(name|version)\s*=\s*"([^"]+)"')
_AUTOMATED_COVERAGE: tuple[dict[str, str], ...] = (
    {
        "name": "pytest",
        "status": "automated",
        "evidence": "uv run pytest",
    },
    {
        "name": "golden stdio evals",
        "status": "automated",
        "evidence": "uv run python scripts/run_golden_evals.py",
    },
    {
        "name": "output contract snapshots",
        "status": "automated",
        "evidence": "tests/fixtures/snapshots/output_contracts.json",
    },
    {
        "name": "release build",
        "status": "automated",
        "evidence": "uv build and GitHub Release workflow",
    },
    {
        "name": "PyPI publish check",
        "status": "automated",
        "evidence": "Release workflow publish-pypi and post-release-smoke jobs",
    },
    {
        "name": "MCP Registry metadata publish check",
        "status": "automated",
        "evidence": ".github/workflows/publish-mcp.yml",
    },
)
_MANUAL_HOST_UI: tuple[dict[str, str], ...] = (
    {
        "host": "Claude Desktop",
        "status": "pending",
        "date": "none",
        "evidence": "manual UI run not recorded",
    },
    {
        "host": "Claude Code",
        "status": "pending",
        "date": "none",
        "evidence": "manual UI run not recorded",
    },
    {
        "host": "Cursor",
        "status": "pending",
        "date": "none",
        "evidence": "manual UI run not recorded",
    },
    {
        "host": "Codex",
        "status": "pending",
        "date": "none",
        "evidence": "manual UI run not recorded",
    },
)
_MINIMUM_RELEASE_ACCEPTANCE: tuple[str, ...] = (
    "`albumentationsx://capabilities` lists expected tools, prompts, resources, roots, and limits.",
    '`diagnose_environment` returns `status="ok"` or actionable `remediation_actions`.',
    "`validate_preview_request` rejects missing and outside-root paths before rendering.",
    "`export_preview_report` includes contact sheets, concrete feedback, and interactive tuning session timelines.",
    "`export_preview_report` links exported Markdown tuning session artifacts when matching sessions exist.",
    "`export_tuning_session` returns Markdown or JSON content plus artifact metadata suitable for handoff.",
)


def build_host_acceptance_report(root: Path) -> dict[str, Any]:
    """Build a deterministic host acceptance evidence payload from local repo metadata."""
    root = root.resolve()
    package = _read_project_fields(root / "pyproject.toml")
    server = json.loads((root / "server.json").read_text(encoding="utf-8"))
    pypi_package = _first_pypi_package(server)
    manual_host_ui = _manual_host_ui(root)
    return {
        "project": package["name"],
        "version": package["version"],
        "package_version": package["version"],
        "registry_name": server["name"],
        "server_json_version": server["version"],
        "pypi_package": pypi_package["identifier"],
        "pypi_package_version": pypi_package["version"],
        "summary": {
            "automated_coverage": "recorded",
            "manual_host_ui": _manual_summary(manual_host_ui),
        },
        "automated_coverage": [dict(item) for item in _AUTOMATED_COVERAGE],
        "manual_host_ui": manual_host_ui,
        "minimum_release_acceptance": list(_MINIMUM_RELEASE_ACCEPTANCE),
        "manual_run_records": "docs/HOST_MANUAL_RUNS.json",
        "source_docs": [
            "docs/HOST_ACCEPTANCE.md",
            "docs/HOST_MATRIX.md",
            "docs/RELEASE.md",
        ],
    }


def dump_host_acceptance_json(report: dict[str, Any]) -> str:
    """Serialize a host acceptance evidence payload as stable JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def dump_host_acceptance_markdown(report: dict[str, Any]) -> str:
    """Render host acceptance evidence as a concise Markdown review artifact."""
    lines = [
        "# Host Acceptance Evidence",
        "",
        f"- Project: {report['project']}",
        f"- Version: {report['version']}",
        f"- Registry name: {report['registry_name']}",
        f"- PyPI package: {report['pypi_package']}=={report['pypi_package_version']}",
        "- Automated Coverage: recorded",
        f"- Manual Host UI: {report['summary']['manual_host_ui']}",
        "",
        "## Automated Coverage",
        "",
        "| Check | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| {item['name']} | {item['status']} | {item['evidence']} |" for item in report["automated_coverage"])
    lines.extend(
        [
            "",
            "## Manual Host UI",
            "",
            "| Host | Status | Date | Evidence |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| {item['host']} | {item['status']} | {item['date']} | {item['evidence']} |"
        for item in report["manual_host_ui"]
    )
    lines.extend(
        [
            "",
            "## Minimum Release Acceptance",
            "",
        ]
    )
    lines.extend(f"{index}. {item}" for index, item in enumerate(report["minimum_release_acceptance"], start=1))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    """Write host acceptance evidence to stdout or a file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", type=Path, help="Optional output path.")
    parser.add_argument("--root", type=Path, default=Path(), help="Repository root. Defaults to cwd.")
    args = parser.parse_args()

    content = _dump_report(build_host_acceptance_report(args.root), output_format=args.format)
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _dump_report(report: dict[str, Any], *, output_format: ReportFormat) -> str:
    if output_format == "json":
        return dump_host_acceptance_json(report)
    return dump_host_acceptance_markdown(report)


def _read_project_fields(path: Path) -> dict[str, str]:
    project_block = path.read_text(encoding="utf-8").split("[project]", maxsplit=1)[1].split("[", maxsplit=1)[0]
    fields = {match.group(1): match.group(2) for match in _PROJECT_FIELD_PATTERN.finditer(project_block)}
    if "name" not in fields or "version" not in fields:
        msg = f"Could not read project name and version from {path}"
        raise ValueError(msg)
    return fields


def _manual_host_ui(root: Path) -> list[dict[str, str]]:
    records = _read_manual_records(root / "docs" / "HOST_MANUAL_RUNS.json")
    by_host = {record["host"]: record for record in records}
    return [{**item, **by_host.get(item["host"], {})} for item in _MANUAL_HOST_UI]


def _read_manual_records(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    records: list[dict[str, str]] = []
    known_hosts = {item["host"] for item in _MANUAL_HOST_UI}
    for item in payload.get("manual_host_ui", []):
        record = _manual_record(item, known_hosts=known_hosts, path=path)
        records.append(record)
    return records


def _manual_record(item: dict[str, Any], *, known_hosts: set[str], path: Path) -> dict[str, str]:
    host = str(item.get("host", "")).strip()
    status = str(item.get("status", "")).strip()
    if host not in known_hosts:
        msg = f"Unknown host {host!r} in {path}"
        raise ValueError(msg)
    if status not in {"passed", "blocked", "pending"}:
        msg = f"Unsupported manual host UI status {status!r} in {path}"
        raise ValueError(msg)
    date = str(item.get("date", "")).strip() or "none"
    evidence = str(item.get("evidence", "")).strip() or "manual UI run not recorded"
    return {
        "host": host,
        "status": status,
        "date": date,
        "evidence": evidence,
    }


def _manual_summary(manual_host_ui: list[dict[str, str]]) -> str:
    statuses = {item["status"] for item in manual_host_ui}
    if statuses == {"passed"}:
        return "passed"
    if statuses == {"pending"}:
        return "pending"
    if "blocked" in statuses:
        return "blocked"
    return "partial"


def _first_pypi_package(server: dict[str, Any]) -> dict[str, Any]:
    for package in server.get("packages", []):
        if package.get("registryType") == "pypi":
            return package
    msg = "server.json does not contain a PyPI package entry"
    raise ValueError(msg)


if __name__ == "__main__":
    main()
