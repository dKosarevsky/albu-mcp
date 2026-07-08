"""Host-level trust next actions for manual MCP evidence closure."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from albumentationsx_mcp.evidence import (
    HOST_NAMES,
    P0_REQUIRED_HOSTS,
    HostManualRuns,
    HostName,
    validate_host_manual_runs,
)

_GATE_ORDER = ("first_10_minutes_replay", "manual_host_ui")
_GATE_LABELS = {
    "manual_host_ui": "Manual Host UI",
    "first_10_minutes_replay": "First 10 Minutes",
}


def build_host_trust_dashboard(
    *,
    path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    host: HostName | None = None,
) -> dict[str, Any]:
    """Build one report-only next-action dashboard for MCP host trust gates."""
    records = validate_host_manual_runs(path) if path.exists() else HostManualRuns()
    host_lanes = [_host_lane(host_name=host_name, records=records) for host_name in _ordered_hosts(host)]
    next_lane = next((lane for lane in host_lanes if lane["overall_status"] != "passed"), None)
    p0_blocked_count = sum(1 for lane in host_lanes if lane["priority"] == "p0" and lane["overall_status"] != "passed")
    return {
        "dashboard_status": "blocked" if p0_blocked_count else "ready",
        "records_path": str(path),
        "execution_policy": "report_only",
        "host_count": len(host_lanes),
        "p0_blocked_count": p0_blocked_count,
        "next_host": next_lane["host"] if next_lane else None,
        "next_command": next_lane["next_command"] if next_lane else "albu-mcp trust next --format json",
        "host_lanes": host_lanes,
        "regeneration_command": "albu-mcp host next-action --format markdown --output docs/HOST_TRUST_DASHBOARD.md",
    }


def render_host_trust_dashboard_markdown(report: dict[str, Any]) -> str:
    """Render the host-level trust dashboard as compact Markdown."""
    rows = "\n".join(_markdown_row(lane) for lane in report["host_lanes"])
    return (
        "# Host Trust Dashboard\n\n"
        f"Records path: `{report['records_path']}`\n\n"
        f"Dashboard status: `{report['dashboard_status']}`\n\n"
        f"Execution policy: `{report['execution_policy']}`. This report does not write evidence records.\n\n"
        f"Next host: `{report['next_host'] or 'none'}`\n\n"
        "## Host Lanes\n\n"
        "| Host | Priority | Overall | Manual Host UI | First 10 Minutes | Next Action | Next Command |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        f"{rows}\n\n"
        "## Regenerate\n\n"
        "```bash\n"
        f"{report['regeneration_command']}\n"
        "```\n\n"
        "## Operator Rules\n\n"
        "- Record `passed` only after reviewer-observed real MCP host UI evidence.\n"
        "- Keep private dataset paths out of committed evidence records.\n"
        "- Use the next command to collect evidence; import only after manifest validation.\n"
    )


def _ordered_hosts(host: HostName | None) -> tuple[HostName, ...]:
    if host is not None:
        return (host,)
    p0_hosts = tuple(P0_REQUIRED_HOSTS)
    p1_hosts = tuple(host_name for host_name in HOST_NAMES if host_name not in p0_hosts)
    return p0_hosts + p1_hosts


def _host_lane(*, host_name: HostName, records: HostManualRuns) -> dict[str, Any]:
    gate_statuses = _gate_statuses(host_name=host_name, records=records)
    overall_status = _overall_status(gate_statuses)
    next_gate = next((gate for gate in _GATE_ORDER if gate_statuses[gate] != "passed"), None)
    next_action_code = _next_action_code(overall_status)
    next_command = _next_command(host_name) if overall_status != "passed" else "none"
    return {
        "host": host_name,
        "priority": "p0" if host_name in P0_REQUIRED_HOSTS else "p1",
        "overall_status": overall_status,
        "gate_statuses": gate_statuses,
        "next_gate": next_gate,
        "next_action_code": next_action_code,
        "next_action": _next_action_label(next_action_code),
        "next_command": next_command,
        "record_command": _record_command(host_name) if overall_status != "passed" else "none",
    }


def _gate_statuses(*, host_name: HostName, records: HostManualRuns) -> dict[str, str]:
    manual = next((record for record in records.manual_host_ui if record.host == host_name), None)
    replay = next((record for record in records.first_10_minutes_replay if record.host == host_name), None)
    return {
        "manual_host_ui": manual.status if manual else "missing",
        "first_10_minutes_replay": replay.status if replay else "missing",
    }


def _overall_status(gate_statuses: dict[str, str]) -> str:
    if all(status == "passed" for status in gate_statuses.values()):
        return "passed"
    if any(status == "blocked" for status in gate_statuses.values()):
        return "blocked"
    return "pending"


def _next_action_code(overall_status: str) -> str:
    if overall_status == "passed":
        return "none"
    if overall_status == "blocked":
        return "triage_blocker"
    return "collect_real_host_evidence"


def _next_action_label(action_code: str) -> str:
    labels = {
        "none": "None",
        "triage_blocker": "Triage blocker",
        "collect_real_host_evidence": "Collect real host evidence",
    }
    return labels[action_code]


def _next_command(host_name: HostName) -> str:
    return (
        f"albu-mcp evidence collect --host {_quote(host_name)} --date YYYY-MM-DD "
        "--reviewer '<reviewer>' --format markdown"
    )


def _record_command(host_name: HostName) -> str:
    return (
        f"albu-mcp evidence import-artifacts --host {_quote(host_name)} --status passed --date YYYY-MM-DD "
        "--evidence '<redacted reviewer-observed evidence>' --artifact docs/assets/demo/demo_report.md "
        "--confirm-real-host-observed"
    )


def _quote(value: str) -> str:
    return shlex.quote(value)


def _markdown_row(lane: dict[str, Any]) -> str:
    gate_statuses = lane["gate_statuses"]
    return (
        f"| {lane['host']} | `{lane['priority']}` | `{lane['overall_status']}` | "
        f"`{gate_statuses['manual_host_ui']}` | `{gate_statuses['first_10_minutes_replay']}` | "
        f"{lane['next_action']} | `{lane['next_command']}` |"
    )
