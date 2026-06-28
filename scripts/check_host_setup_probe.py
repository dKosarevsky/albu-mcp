"""Build or run a host setup probe before first-preview work."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

_DEFAULT_ALLOWED_ROOT = Path("/absolute/path/to/images")
_DEFAULT_ARTIFACT_ROOT = Path("/absolute/path/to/albu-artifacts")
_HOSTS = ("Codex", "Claude Code", "Cursor", "Claude Desktop")
_HOST_DOCS = {
    "Codex": "examples/codex_preview_mcp_config.toml",
    "Claude Code": "examples/claude_code_preview_command.md",
    "Cursor": "examples/cursor_preview_mcp_config.json",
    "Claude Desktop": "examples/claude_desktop_preview_config.json",
}


def build_host_setup_probe(
    *,
    live: bool = False,
    allowed_root: Path = _DEFAULT_ALLOWED_ROOT,
    artifact_root: Path = _DEFAULT_ARTIFACT_ROOT,
    executable_checker: Callable[[str], str | None] = shutil.which,
) -> dict[str, Any]:
    """Build a deterministic or live host setup probe report."""
    checks = [
        _executable_check(name="uvx", command="uvx", live=live, executable_checker=executable_checker),
        _executable_check(name="claude_cli", command="claude", live=live, executable_checker=executable_checker),
        _path_check(name="allowed_root", path=allowed_root, live=live, must_exist=True),
        _path_check(name="artifact_root", path=artifact_root, live=live, must_exist=False),
        _static_check(
            name="package_command",
            status="passed",
            detail="uvx --from albumentationsx-mcp albumentationsx-mcp",
            remediation="Use the published PyPI package command from docs/INSTALL.md.",
        ),
        _static_check(
            name="bounded_roots",
            status="passed",
            detail="Use --allowed-root and --artifact-root for preview work.",
            remediation="Keep local image reads and generated artifacts scoped to explicit directories.",
        ),
    ]
    failed_count = sum(check["status"] == "failed" for check in checks)
    not_run_count = sum(check["status"] == "not_run" for check in checks)
    return {
        "probe_status": _probe_status(live=live, failed_count=failed_count),
        "live": live,
        "allowed_root": str(allowed_root),
        "artifact_root": str(artifact_root),
        "summary": {
            "host_count": len(_HOSTS),
            "check_count": len(checks),
            "passed_check_count": sum(check["status"] == "passed" for check in checks),
            "failed_check_count": failed_count,
            "not_run_check_count": not_run_count,
        },
        "checks": checks,
        "host_lanes": [_host_lane(host) for host in _HOSTS],
        "post_probe_commands": [
            "uv run python scripts/check_host_setup_probe.py --live --format json",
            "uv run python scripts/check_p0_host_run_preflight.py",
            "uv run python scripts/check_host_setup_probe.py --output docs/HOST_SETUP_PROBE.md",
            "uv run python scripts/check_release_readiness.py",
        ],
        "source_docs": [
            "docs/INSTALL.md",
            "docs/HOST_MATRIX.md",
            "docs/HOST_FAILURE_COOKBOOK.md",
            "docs/HOST_EVIDENCE_RUNNER.md",
        ],
    }


def render_host_setup_probe_markdown(probe: dict[str, Any]) -> str:
    """Render a host setup probe report as Markdown."""
    lines = [
        "# Host Setup Probe",
        "",
        f"Probe status: `{probe['probe_status']}`",
        f"Live probe: `{str(probe['live']).lower()}`",
        f"Allowed root: `{probe['allowed_root']}`",
        f"Artifact root: `{probe['artifact_root']}`",
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in probe["summary"].items())
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Check | Status | Detail | Remediation |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| `{check['name']}` | `{check['status']}` | {check['detail']} | {check['remediation']} |"
        for check in probe["checks"]
    )
    lines.extend(
        [
            "",
            "## Host Lanes",
            "",
            "| Host | Setup Doc | Required Checks |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| {lane['host']} | `{lane['setup_doc']}` | {', '.join(f'`{check}`' for check in lane['required_checks'])} |"
        for lane in probe["host_lanes"]
    )
    lines.extend(["", "## Post-Probe Commands", ""])
    lines.extend(f"- `{command}`" for command in probe["post_probe_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in probe["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for host setup probes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Probe the current machine instead of rendering a template.",
    )
    parser.add_argument("--allowed-root", type=Path, default=_DEFAULT_ALLOWED_ROOT)
    parser.add_argument("--artifact-root", type=Path, default=_DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    probe = build_host_setup_probe(live=args.live, allowed_root=args.allowed_root, artifact_root=args.artifact_root)
    content = (
        json.dumps(probe, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_host_setup_probe_markdown(probe)
    )
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _probe_status(*, live: bool, failed_count: int) -> str:
    if not live:
        return "manual_probe_required"
    return "blocked" if failed_count else "passed"


def _executable_check(
    *,
    name: str,
    command: str,
    live: bool,
    executable_checker: Callable[[str], str | None],
) -> dict[str, str]:
    if not live:
        return _static_check(
            name=name,
            status="not_run",
            detail=f"Run `command -v {command}` in the host operator shell.",
            remediation=f"Install or expose `{command}` before relying on host setup.",
        )
    path = executable_checker(command)
    return _static_check(
        name=name,
        status="passed" if path else "failed",
        detail=path or f"{command} not found on PATH",
        remediation=f"Install or expose `{command}` in the same shell/session that starts the MCP host.",
    )


def _path_check(*, name: str, path: Path, live: bool, must_exist: bool) -> dict[str, str]:
    if not live:
        return _static_check(
            name=name,
            status="not_run",
            detail=f"Replace `{path}` with a local absolute path before preview work.",
            remediation="Use the smallest useful local root and keep generated artifacts outside source datasets.",
        )
    exists = path.exists()
    writable = os.access(path if exists else path.parent, os.W_OK)
    ok = exists and path.is_dir() if must_exist else writable
    return _static_check(
        name=name,
        status="passed" if ok else "failed",
        detail=f"{path} exists={exists} writable_parent_or_path={writable}",
        remediation="Create the directory or choose an absolute path writable by the MCP host process.",
    )


def _static_check(*, name: str, status: str, detail: str, remediation: str) -> dict[str, str]:
    return {
        "name": name,
        "status": status,
        "detail": detail,
        "remediation": remediation,
    }


def _host_lane(host: str) -> dict[str, Any]:
    checks = ["uvx", "allowed_root", "artifact_root", "package_command", "bounded_roots"]
    if host == "Claude Code":
        checks.insert(1, "claude_cli")
    return {
        "host": host,
        "setup_doc": _HOST_DOCS[host],
        "required_checks": checks,
    }


if __name__ == "__main__":
    main()
