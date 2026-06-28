"""Export a real-host P0 run session packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_v1_evidence_operator_packet import build_v1_evidence_operator_packet


def build_p0_host_run_session() -> dict[str, Any]:
    """Build host-by-host P0 run session instructions without claiming evidence."""
    packet = build_v1_evidence_operator_packet()
    return {
        "session_status": packet["packet_status"],
        "required_hosts": packet["required_hosts"],
        "non_fabrication_policy": "Record only reviewer-observed real host UI evidence.",
        "summary": packet["summary"],
        "host_sessions": [_host_session(lane) for lane in packet["operator_lanes"]],
        "post_session_commands": packet["post_recording_commands"],
        "source_docs": [
            "docs/V1_EVIDENCE_OPERATOR_PACKET.md",
            "docs/P0_HOST_EVIDENCE_LEDGER.md",
            "docs/FIRST_10_MINUTES.md",
            "docs/HOST_MANUAL_RUNS.json",
        ],
    }


def render_p0_host_run_session_markdown(session: dict[str, Any]) -> str:
    """Render the P0 host run session packet as Markdown."""
    lines = [
        "# P0 Host Run Session",
        "",
        f"Session status: `{session['session_status']}`",
        f"Required hosts: `{', '.join(session['required_hosts'])}`",
        "",
        "## Non-Fabrication Policy",
        "",
        session["non_fabrication_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in session["summary"].items())
    lines.extend(["", "## Host Sessions", ""])
    for host_session in session["host_sessions"]:
        lines.extend(
            [
                f"## {host_session['host']} Session",
                "",
                f"Session status: `{host_session['session_status']}`",
                "",
                "Host prompt:",
                "",
                f"> {host_session['host_prompt']}",
                "",
                "Run checklist:",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in host_session["run_checklist"])
        lines.extend(["", "Record commands:", ""])
        lines.extend(f"- `{command}`" for command in host_session["record_commands"])
        lines.extend(["", "Evidence candidate templates:", ""])
        for gate, template in host_session["evidence_candidate_templates"].items():
            lines.extend(
                [
                    f"`{gate}`:",
                    "",
                    "```json",
                    json.dumps(template, indent=2),
                    "```",
                    "",
                ]
            )
        lines.extend(["", "Gate statuses:", ""])
        lines.extend(f"- `{gate['gate']}`: `{gate['record_status']}`" for gate in host_session["gates"])
        lines.append("")
    lines.extend(["## Post-Session Commands", ""])
    lines.extend(f"- `{command}`" for command in session["post_session_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in session["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for P0 host run session exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_p0_host_run_session_markdown(build_p0_host_run_session())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _host_session(lane: dict[str, Any]) -> dict[str, Any]:
    missing_or_pending = [gate for gate in lane["gates"] if gate["record_status"] in {"missing", "pending"}]
    blocked = [gate for gate in lane["gates"] if gate["record_status"] == "blocked"]
    if blocked:
        status = "blocked"
    elif missing_or_pending:
        status = "not_started"
    else:
        status = "passed"
    return {
        "host": lane["host"],
        "session_status": status,
        "host_prompt": lane["host_prompt"],
        "run_checklist": [
            "Start the MCP host with the published or local server command.",
            "List AlbumentationsX MCP tools/resources in the real host UI.",
            "Call run_host_smoke_check and inspect preview_ready.",
            "Complete docs/FIRST_10_MINUTES.md in the same host UI.",
            "Record only redacted, reviewer-observed evidence after the run.",
        ],
        "record_commands": lane["record_commands"],
        "evidence_candidate_templates": {
            "manual_host_ui": _manual_host_ui_template(lane["host"]),
            "first_10_minutes_replay": _first_10_minutes_template(lane["host"]),
        },
        "gates": lane["gates"],
    }


def _manual_host_ui_template(host: str) -> dict[str, str]:
    return {
        "host": host,
        "status": "passed",
        "date": "YYYY-MM-DD",
        "evidence": f"Redacted reviewer-observed {host} host UI evidence summary.",
    }


def _first_10_minutes_template(host: str) -> dict[str, str | list[str]]:
    return {
        "host": host,
        "status": "passed",
        "date": "YYYY-MM-DD",
        "evidence": f"Redacted reviewer-observed {host} first-10-minutes replay summary.",
        "artifacts": ["docs/assets/demo/demo_report.md"],
    }


if __name__ == "__main__":
    main()
