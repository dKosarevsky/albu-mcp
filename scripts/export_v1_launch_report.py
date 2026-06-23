"""Export a local v1 launch readiness report without network calls."""

from __future__ import annotations

import argparse
import json
import re
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
    blockers = _blockers(manual_host_ui=manual_host_ui, first_10_minutes_replay=replay_status)
    return {
        "package": "albumentationsx-mcp",
        "mcp_name": server_payload["name"],
        "package_version": package_version,
        "server_version": server_payload["version"],
        "host_proof_status_path": str(host_proof_status_path),
        "ready_for_v1": not blockers,
        "blockers": blockers,
        "manual_host_ui": manual_host_ui,
        "first_10_minutes_replay": replay_status,
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
    lines.extend(["", "## Manual Host UI", ""])
    lines.extend(_host_status_lines(report["manual_host_ui"]))
    lines.extend(["", "## First 10 Minutes Replay", ""])
    lines.extend(_host_status_lines(report["first_10_minutes_replay"]))
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


if __name__ == "__main__":
    main()
