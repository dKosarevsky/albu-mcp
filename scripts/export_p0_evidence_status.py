"""Export current P0 evidence status for the v1 RC gate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_v1_rc_readiness_report import build_v1_rc_readiness_report

_GATES = ("first_10_minutes_replay", "manual_host_ui")


def build_p0_evidence_status() -> dict[str, Any]:
    """Build deterministic P0 evidence status from the RC readiness report."""
    rc_report = build_v1_rc_readiness_report()
    blocker_by_host_gate = {(item["host"], item["gate"]): item for item in rc_report["rc_blockers"]}
    host_statuses = [
        {
            "host": host,
            "gates": [
                _gate_status(host=host, gate=gate, blocker=blocker_by_host_gate.get((host, gate))) for gate in _GATES
            ],
        }
        for host in rc_report["required_rc_hosts"]
    ]
    gates = [gate for item in host_statuses for gate in item["gates"]]
    return {
        "target_hosts": rc_report["required_rc_hosts"],
        "rc_decision": rc_report["rc_decision"],
        "rc_ready": rc_report["rc_release_candidate_allowed"],
        "summary": {
            "host_count": len(host_statuses),
            "passed_gate_count": sum(gate["status"] == "recorded" for gate in gates),
            "required_gate_count": len(gates),
            "blocked_gate_count": sum(gate["status"] == "blocked" for gate in gates),
            "missing_gate_count": sum(gate["status"] == "missing" for gate in gates),
        },
        "host_statuses": host_statuses,
        "next_action": _next_action(rc_ready=rc_report["rc_release_candidate_allowed"]),
    }


def render_p0_evidence_status_markdown(status: dict[str, Any]) -> str:
    """Render P0 evidence status as Markdown."""
    lines = [
        "# P0 Evidence Status",
        "",
        f"Target hosts: `{', '.join(status['target_hosts'])}`",
        f"RC decision: `{status['rc_decision']}`",
        f"RC ready: `{str(status['rc_ready']).lower()}`",
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in status["summary"].items())
    lines.extend(
        [
            "",
            "## Gate Status",
            "",
            "| Host | Gate | Status | Next Action |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in status["host_statuses"]:
        lines.extend(
            "| "
            f"{item['host']} | "
            f"`{gate['gate']}` | "
            f"`{gate['status']}` | "
            f"`{gate['next_action']}` |"
            for gate in item["gates"]
        )
    lines.extend(["", "## Next Action", "", status["next_action"]])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for P0 evidence status exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_p0_evidence_status_markdown(build_p0_evidence_status())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _gate_status(*, host: str, gate: str, blocker: dict[str, str] | None) -> dict[str, str]:
    if blocker is None:
        return {"host": host, "gate": gate, "status": "recorded", "next_action": "no_action"}
    return {
        "host": host,
        "gate": gate,
        "status": blocker["evidence_status"],
        "next_action": blocker["next_action"],
    }


def _next_action(*, rc_ready: bool) -> str:
    if rc_ready:
        return "Prepare the v1 RC release packet."
    return "Run P0 host runbook and record real UI evidence."


if __name__ == "__main__":
    main()
