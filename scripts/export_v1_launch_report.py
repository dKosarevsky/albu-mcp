"""Export a local v1 launch readiness report without network calls."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_first_10_minutes_replay import check_first_10_minutes_replay
from scripts.validate_host_manual_runs import HOST_NAMES, HostName, validate_host_manual_runs

_DEFAULT_MANUAL_RUNS_PATH = Path("docs/HOST_MANUAL_RUNS.json")
_DEFAULT_PYPROJECT_PATH = Path("pyproject.toml")
_DEFAULT_SERVER_JSON_PATH = Path("server.json")
_DEFAULT_HOST_PROOF_STATUS_PATH = Path("docs/HOST_PROOF_STATUS.md")
_VERSION_PATTERN = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
_P0_HOSTS = frozenset({"Codex", "Claude Code"})


def build_v1_launch_report(
    *,
    manual_runs_path: Path = _DEFAULT_MANUAL_RUNS_PATH,
    pyproject_path: Path = _DEFAULT_PYPROJECT_PATH,
    server_json_path: Path = _DEFAULT_SERVER_JSON_PATH,
    host_proof_status_path: Path = _DEFAULT_HOST_PROOF_STATUS_PATH,
) -> dict[str, Any]:
    """Build a deterministic local v1 launch report from committed evidence."""
    package_version = _read_pyproject_version(pyproject_path)
    server_payload = json.loads(server_json_path.read_text(encoding="utf-8"))
    manual_runs = validate_host_manual_runs(manual_runs_path)
    manual_host_ui = _manual_host_ui_status(manual_runs.manual_host_ui)
    replay = check_first_10_minutes_replay(manual_runs_path)
    replay_status = [
        {
            "host": check.host,
            "status": check.status,
            "ok": check.ok,
            "message": check.message,
            "date": check.date,
            "evidence": check.evidence,
            "artifacts": check.artifacts or [],
        }
        for check in replay.checks
    ]
    evidence_plan = _evidence_plan(manual_host_ui=manual_host_ui, first_10_minutes_replay=replay_status)
    blockers = _blockers(manual_host_ui=manual_host_ui, first_10_minutes_replay=replay_status)
    host_blockers = _host_blockers(evidence_plan)
    return {
        "package": "albumentationsx-mcp",
        "mcp_name": server_payload["name"],
        "package_version": package_version,
        "server_version": server_payload["version"],
        "host_proof_status_path": str(host_proof_status_path),
        "ready_for_v1": not blockers,
        "blockers": blockers,
        "host_blockers": host_blockers,
        "manual_host_ui": manual_host_ui,
        "first_10_minutes_replay": replay_status,
        "evidence_plan": evidence_plan,
        "recommended_next_actions": _recommended_next_actions(blockers),
    }


def render_v1_launch_report_markdown(report: dict[str, Any]) -> str:
    """Render a reviewable Markdown launch report."""
    lines = [
        "# V1 Launch Report",
        "",
        f"Package: `{report['package']}`",
        f"MCP name: `{report['mcp_name']}`",
        f"Package version: `{report['package_version']}`",
        f"Server version: `{report['server_version']}`",
        f"Ready for v1: `{str(report['ready_for_v1']).lower()}`",
        f"Host proof status: `{report['host_proof_status_path']}`",
        "",
        "## Blockers",
        "",
    ]
    if report["blockers"]:
        lines.extend(
            f"- `{blocker['code']}` ({blocker['severity']}): {blocker['summary']}" for blocker in report["blockers"]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Host Blockers", ""])
    lines.extend(_host_blocker_lines(report["host_blockers"]))
    lines.extend(["", "## Manual Host UI", ""])
    lines.extend(_host_status_lines(report["manual_host_ui"]))
    lines.extend(["", "## First 10 Minutes Replay", ""])
    lines.extend(_host_status_lines(report["first_10_minutes_replay"]))
    lines.extend(["", "## Evidence Plan", ""])
    lines.extend(_evidence_plan_lines(report["evidence_plan"]))
    lines.extend(["", "## Recommended Next Actions", ""])
    lines.extend(f"- {action}" for action in report["recommended_next_actions"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for local v1 launch report exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    report = build_v1_launch_report()
    content = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_v1_launch_report_markdown(report)
    )
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _read_pyproject_version(path: Path) -> str:
    match = _VERSION_PATTERN.search(path.read_text(encoding="utf-8"))
    if match is None:
        msg = f"{path}: project version not found"
        raise ValueError(msg)
    return match.group(1)


def _manual_host_ui_status(records: list[Any]) -> list[dict[str, Any]]:
    by_host = {record.host: record for record in records}
    statuses: list[dict[str, Any]] = []
    for host in HOST_NAMES:
        record = by_host.get(host)
        if record is None:
            statuses.append(
                {
                    "host": host,
                    "status": "pending",
                    "ok": False,
                    "message": "manual host UI evidence not recorded",
                    "date": "none",
                    "evidence": "manual host UI evidence not recorded",
                }
            )
            continue
        statuses.append(
            {
                "host": record.host,
                "status": record.status,
                "ok": record.status == "passed",
                "message": _manual_message(host=record.host, status=record.status),
                "date": record.model_dump(mode="json")["date"],
                "evidence": record.evidence,
            }
        )
    return statuses


def _manual_message(*, host: HostName, status: str) -> str:
    if status == "passed":
        return f"{host} has dated manual host UI evidence"
    if status == "blocked":
        return f"{host} manual host UI evidence is blocked"
    return f"{host} manual host UI evidence is pending"


def _blockers(
    *,
    manual_host_ui: list[dict[str, Any]],
    first_10_minutes_replay: list[dict[str, Any]],
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    if any(not item["ok"] for item in manual_host_ui):
        blockers.append(
            {
                "code": "manual_host_ui_pending",
                "severity": "high",
                "summary": "At least one supported host lacks passed manual UI evidence.",
            }
        )
    if any(not item["ok"] for item in first_10_minutes_replay):
        blockers.append(
            {
                "code": "first_10_minutes_replay_pending",
                "severity": "high",
                "summary": "At least one supported host lacks passed First 10 Minutes replay evidence.",
            }
        )
    return blockers


def _recommended_next_actions(blockers: list[dict[str, str]]) -> list[str]:
    if not blockers:
        return ["Cut v1.0.0 after a final release-readiness run and tag workflow."]
    actions: list[str] = []
    blocker_codes = {blocker["code"] for blocker in blockers}
    if "manual_host_ui_pending" in blocker_codes:
        actions.append("Run the host proof sprint in real MCP host UIs and record dated evidence.")
    if "first_10_minutes_replay_pending" in blocker_codes:
        actions.append("Replay docs/FIRST_10_MINUTES.md in target hosts and record artifacts.")
    actions.append("Re-run scripts/export_v1_launch_report.py after updating docs/HOST_MANUAL_RUNS.json.")
    return actions


def _host_status_lines(items: list[dict[str, Any]]) -> list[str]:
    return [f"- {item['host']}: `{item['status']}` — {item['message']}" for item in items]


def _host_blockers(evidence_plan: list[dict[str, Any]]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for item in evidence_plan:
        host = item["host"]
        for gate in ("first_10_minutes_replay", "manual_host_ui"):
            requirement = item[gate]
            if requirement["status"] == "recorded":
                continue
            blockers.append(
                {
                    "host": host,
                    "priority": _host_priority(host),
                    "gate": gate,
                    "code": _host_blocker_code(gate=gate, status=requirement["status"]),
                    "severity": "high",
                    "evidence_status": requirement["status"],
                    "reason": requirement["message"],
                    "next_action": _host_blocker_next_action(gate=gate, status=requirement["status"]),
                    "packet_command": _packet_command(host),
                    "record_command": item["record_commands"][gate],
                }
            )
    return blockers


def _host_priority(host: str) -> str:
    return "p0" if host in _P0_HOSTS else "p1"


def _host_blocker_code(*, gate: str, status: str) -> str:
    if status == "blocked":
        return f"{gate}_blocked"
    return f"{gate}_missing"


def _host_blocker_next_action(*, gate: str, status: str) -> str:
    if status == "blocked":
        return "triage_blocker"
    if gate == "first_10_minutes_replay":
        return "run_first_10_minutes_replay"
    return "run_manual_host_ui"


def _packet_command(host: str) -> str:
    output = f"/tmp/albu-host-{_host_slug(host)}.md"  # noqa: S108 - local reviewer packet scratch path.
    return " ".join(
        shlex.quote(part)
        for part in [
            "uv",
            "run",
            "python",
            "scripts/export_manual_host_acceptance_packet.py",
            "--host",
            host,
            "--output",
            output,
        ]
    )


def _host_slug(host: str) -> str:
    return host.lower().replace(" ", "-")


def _host_blocker_lines(items: list[dict[str, str]]) -> list[str]:
    if not items:
        return ["- none"]
    lines = [
        "| Host | Priority | Gate | Status | Next Action |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        "| "
        f"{item['host']} | "
        f"`{item['priority']}` | "
        f"`{item['gate']}` | "
        f"`{item['evidence_status']}` | "
        f"`{item['next_action']}` |"
        for item in items
    )
    lines.extend(["", "Packet commands:"])
    lines.extend(f"- {item['host']} / {item['gate']}: `{item['packet_command']}`" for item in items)
    return lines


def _evidence_plan(
    *,
    manual_host_ui: list[dict[str, Any]],
    first_10_minutes_replay: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    manual_by_host = {item["host"]: item for item in manual_host_ui}
    replay_by_host = {item["host"]: item for item in first_10_minutes_replay}
    return [
        {
            "host": host,
            "manual_host_ui": _evidence_requirement(
                item=manual_by_host[host],
                missing_message="Run the host UI, list MCP tools, and execute run_host_smoke_check.",
            ),
            "first_10_minutes_replay": _evidence_requirement(
                item=replay_by_host[host],
                missing_message="Replay docs/FIRST_10_MINUTES.md and capture at least one artifact path.",
            ),
            "record_commands": {
                "manual_host_ui": _record_command(host=host, kind="manual-host-ui"),
                "first_10_minutes_replay": _record_command(host=host, kind="first-10-minutes"),
            },
        }
        for host in HOST_NAMES
    ]


def _evidence_requirement(*, item: dict[str, Any], missing_message: str) -> dict[str, str]:
    if item["ok"]:
        return {
            "status": "recorded",
            "message": item["message"],
            "date": item["date"],
        }
    return {
        "status": "missing" if item["status"] == "pending" else item["status"],
        "message": missing_message if item["status"] == "pending" else item["message"],
        "date": item["date"],
    }


def _record_command(*, host: HostName, kind: str) -> str:
    args = [
        "uv",
        "run",
        "python",
        "scripts/record_host_manual_run.py",
    ]
    if kind == "first-10-minutes":
        args.extend(["--kind", "first-10-minutes"])
    args.extend(
        [
            "--host",
            host,
            "--status",
            "passed",
            "--date",
            "YYYY-MM-DD",
            "--evidence",
            _evidence_placeholder(host=host, kind=kind),
        ]
    )
    if kind == "first-10-minutes":
        args.extend(["--artifact", "docs/assets/demo/demo_report.md"])
    return " ".join(shlex.quote(arg) for arg in args)


def _evidence_placeholder(*, host: HostName, kind: str) -> str:
    if kind == "first-10-minutes":
        return (
            f"{host} completed smoke check, preview validation, baseline and candidate render, comparison, "
            "and pipeline export."
        )
    return f"{host} listed MCP tools and completed run_host_smoke_check in the host UI."


def _evidence_plan_lines(items: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in items:
        lines.extend(
            [
                f"- {item['host']}: manual UI `{item['manual_host_ui']['status']}`, "
                f"first 10 minutes `{item['first_10_minutes_replay']['status']}`",
                f"  - Manual UI: `{item['record_commands']['manual_host_ui']}`",
                f"  - First 10 Minutes: `{item['record_commands']['first_10_minutes_replay']}`",
            ]
        )
    return lines


if __name__ == "__main__":
    main()
