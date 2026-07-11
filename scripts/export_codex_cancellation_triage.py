"""Export a focused triage packet for Codex MCP tool-call cancellations."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_p0_host_unblock_pack import build_p0_host_unblock_pack

_HOST = "Codex"
_FAILURE_CLASS = "codex_tool_call_cancelled"


def build_codex_cancellation_triage() -> dict[str, Any]:
    """Build a deterministic triage packet for Codex cancellation blockers."""
    unblock_pack = build_p0_host_unblock_pack()
    lanes = [lane for lane in unblock_pack["recovery_lanes"] if lane["host"] == _HOST]
    return {
        "triage_status": "blocked_tool_call_cancellation" if lanes else "codex_evidence_recorded",
        "host": _HOST,
        "failure_class": _FAILURE_CLASS,
        "rc_reopen_allowed": unblock_pack["rc_reopen_allowed"] and not lanes,
        "summary": {
            "affected_gate_count": len(lanes),
            "blocked_gate_count": sum(lane["evidence_status"] == "blocked" for lane in lanes),
            "missing_gate_count": sum(lane["evidence_status"] == "missing" for lane in lanes),
        },
        "triage_policy": _triage_policy(has_active_lanes=bool(lanes)),
        "affected_gates": [_affected_gate(lane) for lane in lanes],
        "safe_diagnostics": [
            "Open an interactive Codex session where MCP tool approval prompts are visible.",
            "Confirm AlbumentationsX MCP tools are listed by the host.",
            "Read albumentationsx://examples/client-smoke before calling any tool.",
            "Call run_host_smoke_check and observe whether the approval prompt is accepted or cancelled.",
            "If cancellation repeats, record the first visible blocker as blocked evidence.",
        ],
        "evidence_to_capture": [
            "Whether Codex lists the AlbumentationsX MCP server and tools.",
            "Whether albumentationsx://examples/client-smoke is readable.",
            "The observed run_host_smoke_check result or cancellation state.",
            "The first host-visible approval or permission blocker, redacted for private paths and credentials.",
        ],
        "record_commands": {
            "passed": [lane["record_command"] for lane in lanes],
            "blocked": [_blocked_record_command(gate=lane["gate"]) for lane in lanes],
        },
        "acceptance_criteria": [
            "run_host_smoke_check completes in Codex and reports preview_ready=true.",
            "First 10 Minutes replay is run only after preview_ready=true.",
            "Each affected P0 gate has a dated real-host evidence note or artifact.",
        ],
        "non_goals": [
            "Do not use generated smoke output as real Codex UI evidence.",
            "Do not bypass or disable Codex tool-call approval prompts to force a pass.",
            "Do not paste private images, credentials, or machine-local paths into public artifacts.",
        ],
        "source_docs": [
            "docs/P0_HOST_UNBLOCK_PACK.md",
            "docs/HOST_EVIDENCE_RUNNER.md",
            "docs/HOST_FAILURE_COOKBOOK.md",
            "docs/HOST_MANUAL_RUNS.json",
        ],
    }


def render_codex_cancellation_triage_markdown(triage: dict[str, Any]) -> str:
    """Render Codex cancellation triage as Markdown."""
    lines = [
        "# Codex Cancellation Triage",
        "",
        f"Triage status: `{triage['triage_status']}`",
        f"Host: `{triage['host']}`",
        f"Failure class: `{triage['failure_class']}`",
        f"RC reopen allowed: `{str(triage['rc_reopen_allowed']).lower()}`",
        "",
        "## Triage Policy",
        "",
        triage["triage_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in triage["summary"].items())
    lines.extend(
        [
            "",
            "## Affected Gates",
            "",
            "| Gate | Evidence Status | Passed Command | Blocked Command |",
            "| --- | --- | --- | --- |",
        ]
    )
    if triage["affected_gates"]:
        lines.extend(
            "| "
            f"`{gate['gate']}` | "
            f"`{gate['evidence_status']}` | "
            f"`{gate['passed_record_command']}` | "
            f"`{gate['blocked_record_command']}` |"
            for gate in triage["affected_gates"]
        )
    else:
        lines.append("| `none` | `recorded` | `none` | `none` |")
    lines.extend(["", "## Safe Diagnostics", ""])
    lines.extend(f"- {step}" for step in triage["safe_diagnostics"])
    lines.extend(["", "## Evidence To Capture", ""])
    lines.extend(f"- {item}" for item in triage["evidence_to_capture"])
    lines.extend(["", "## Acceptance Criteria", ""])
    lines.extend(f"- {item}" for item in triage["acceptance_criteria"])
    lines.extend(["", "## Record Commands", "", "Passed evidence:"])
    lines.extend(f"- `{command}`" for command in triage["record_commands"]["passed"])
    lines.extend(["", "Blocked evidence:"])
    lines.extend(f"- `{command}`" for command in triage["record_commands"]["blocked"])
    lines.extend(["", "## Non-Goals", ""])
    lines.extend(f"- {item}" for item in triage["non_goals"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in triage["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for Codex cancellation triage exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_codex_cancellation_triage_markdown(build_codex_cancellation_triage())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _affected_gate(lane: dict[str, Any]) -> dict[str, str]:
    return {
        "gate": lane["gate"],
        "evidence_status": lane["evidence_status"],
        "passed_record_command": lane["record_command"],
        "blocked_record_command": _blocked_record_command(gate=lane["gate"]),
    }


def _triage_policy(*, has_active_lanes: bool) -> str:
    if not has_active_lanes:
        return (
            "Codex has dated reviewer-observed evidence for both required host gates. "
            "No Codex cancellation recovery lane remains; RC readiness may still be blocked by other hosts."
        )
    return (
        "A cancelled Codex MCP tool call is blocking evidence, not a passed host run. Keep the P0 gate closed "
        "until Codex completes the real host flow and records dated reviewer-observed evidence."
    )


def _blocked_record_command(*, gate: str) -> str:
    args = [
        "uv",
        "run",
        "python",
        "scripts/record_host_manual_run.py",
    ]
    if gate == "first_10_minutes_replay":
        args.extend(["--kind", "first-10-minutes"])
    args.extend(
        [
            "--host",
            _HOST,
            "--status",
            "blocked",
            "--date",
            "YYYY-MM-DD",
            "--evidence",
            f"Codex cancelled or blocked run_host_smoke_check before {gate} could pass in the real MCP host UI.",
        ]
    )
    return " ".join(shlex.quote(arg) for arg in args)


if __name__ == "__main__":
    main()
