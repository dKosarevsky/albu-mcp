"""Host setup probes for real MCP operator runs."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from albumentationsx_mcp.evidence import HOST_NAMES, HostName

DEFAULT_ALLOWED_ROOT = Path("/absolute/path/to/images")
DEFAULT_ARTIFACT_ROOT = Path("/absolute/path/to/albu-artifacts")

_HOST_DOCS: dict[HostName, str] = {
    "Codex": "examples/codex_preview_mcp_config.toml",
    "Claude Code": "examples/claude_code_preview_command.md",
    "Cursor": "examples/cursor_preview_mcp_config.json",
    "Claude Desktop": "examples/claude_desktop_preview_config.json",
}
_HOST_ORDER: tuple[HostName, ...] = ("Codex", "Claude Code", "Cursor", "Claude Desktop")
_NON_EVIDENCE_POLICY = (
    "Setup probes only validate local readiness. They do not record P0 evidence or replace reviewer-observed real "
    "MCP host UI runs."
)


def build_host_setup_probe(
    *,
    live: bool = False,
    allowed_root: Path = DEFAULT_ALLOWED_ROOT,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    host: HostName | None = None,
    executable_checker: Callable[[str], str | None] = shutil.which,
) -> dict[str, Any]:
    """Build a deterministic or live host setup probe report."""
    hosts = _selected_hosts(host)
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
    probe_status = _probe_status(live=live, failed_count=failed_count)
    return {
        "probe_status": probe_status,
        "live": live,
        "writes_records": False,
        "allowed_root": str(allowed_root),
        "artifact_root": str(artifact_root),
        "summary": {
            "host_count": len(hosts),
            "check_count": len(checks),
            "passed_check_count": sum(check["status"] == "passed" for check in checks),
            "failed_check_count": failed_count,
            "not_run_check_count": not_run_count,
        },
        "checks": checks,
        "host_lanes": [_host_lane(selected_host, checks) for selected_host in hosts],
        "next_action": _next_action(probe_status),
        "non_evidence_policy": _NON_EVIDENCE_POLICY,
        "post_probe_commands": [
            "uv run python scripts/check_host_setup_probe.py --live --format json",
            "albu-mcp host setup-probe --live --format json",
            "uv run python scripts/check_p0_host_run_preflight.py",
            "albu-mcp evidence collect --host Codex --format json",
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
        f"Writes records: `{str(probe['writes_records']).lower()}`",
        f"Allowed root: `{probe['allowed_root']}`",
        f"Artifact root: `{probe['artifact_root']}`",
        "",
        "## Non-Evidence Policy",
        "",
        probe["non_evidence_policy"],
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
            "| Host | Setup Doc | Operator Command | Required Checks | Blocking Checks | Next Action |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        (
            f"| {lane['host']} | `{lane['setup_doc']}` | `{lane['operator_command']}` | "
            f"{', '.join(f'`{check}`' for check in lane['required_checks'])} | "
            f"{_render_check_list(lane['blocking_checks'])} | `{lane['next_action']}` |"
        )
        for lane in probe["host_lanes"]
    )
    lines.extend(["", "## Post-Probe Commands", ""])
    lines.extend(f"- `{command}`" for command in probe["post_probe_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in probe["source_docs"])
    return "\n".join(lines) + "\n"


def _selected_hosts(host: HostName | None) -> list[HostName]:
    if host is None:
        return list(_HOST_ORDER)
    if host not in HOST_NAMES:
        msg = f"unsupported host: {host}"
        raise ValueError(msg)
    return [host]


def _probe_status(*, live: bool, failed_count: int) -> str:
    if not live:
        return "manual_probe_required"
    return "blocked" if failed_count else "passed"


def _next_action(probe_status: str) -> str:
    if probe_status == "manual_probe_required":
        return "run_live_probe"
    if probe_status == "blocked":
        return "fix_blocking_checks"
    return "run_evidence_collect"


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


def _host_lane(host: HostName, checks: list[dict[str, str]]) -> dict[str, Any]:
    required_checks = ["uvx", "allowed_root", "artifact_root", "package_command", "bounded_roots"]
    if host == "Claude Code":
        required_checks.insert(1, "claude_cli")
    check_by_name = {check["name"]: check for check in checks}
    blocking_checks = [name for name in required_checks if check_by_name[name]["status"] == "failed"]
    return {
        "host": host,
        "setup_doc": _HOST_DOCS[host],
        "operator_command": _operator_command(host),
        "required_checks": required_checks,
        "blocking_checks": blocking_checks,
        "next_action": "fix_blocking_checks" if blocking_checks else "run_evidence_collect",
    }


def _operator_command(host: HostName) -> str:
    command = "uvx --from albumentationsx-mcp albumentationsx-mcp"
    if host == "Claude Code":
        return f"claude mcp add albumentationsx -- {command}"
    return command


def _render_check_list(checks: list[str]) -> str:
    if not checks:
        return "`none`"
    return ", ".join(f"`{check}`" for check in checks)
