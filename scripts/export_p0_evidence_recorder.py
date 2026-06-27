"""Export a P0 evidence recording worksheet with safe copyable commands."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Any

_P0_HOSTS = ("Codex", "Claude Code")
_GATES = ("first_10_minutes_replay", "manual_host_ui")
_STATUSES = ("passed", "blocked", "pending")


def build_p0_evidence_recorder() -> dict[str, Any]:
    """Build a deterministic P0 evidence recorder without writing evidence records."""
    return {
        "target_hosts": list(_P0_HOSTS),
        "recording_policy": "Record only redacted, reviewer-observed host UI evidence.",
        "privacy_notes": [
            "Do not record private screenshots, prompts, tokens, or full host logs.",
            "Record the first failing gate when status is blocked.",
            "Keep pending when a host was not run in the real UI.",
        ],
        "required_fields": ["host", "gate", "status", "date", "evidence", "artifact"],
        "records": [_recording_card(host) for host in _P0_HOSTS],
        "after_recording_commands": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md",
            "uv run python scripts/check_release_readiness.py",
        ],
    }


def render_p0_evidence_recorder_markdown(recorder: dict[str, Any]) -> str:
    """Render the P0 evidence recorder as Markdown."""
    lines = [
        "# P0 Evidence Recorder",
        "",
        f"Target hosts: `{', '.join(recorder['target_hosts'])}`",
        "",
        "## Recording Policy",
        "",
        recorder["recording_policy"],
        "",
        "## Privacy Notes",
        "",
    ]
    lines.extend(f"- {note}" for note in recorder["privacy_notes"])
    lines.extend(["", "## Required Fields", ""])
    lines.extend(f"- `{field}`" for field in recorder["required_fields"])
    lines.extend(["", "## Record Commands", ""])
    for card in recorder["records"]:
        lines.extend([f"### {card['host']}", ""])
        for gate in _GATES:
            lines.extend([f"#### {gate}", "", "```bash"])
            lines.extend(card["commands"][gate][status] for status in _STATUSES)
            lines.extend(["```", ""])
    lines.extend(["## After Recording", ""])
    lines.extend(f"- `{command}`" for command in recorder["after_recording_commands"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for P0 evidence recorder exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_p0_evidence_recorder_markdown(build_p0_evidence_recorder())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _recording_card(host: str) -> dict[str, Any]:
    return {
        "host": host,
        "gates": list(_GATES),
        "commands": {
            gate: {status: _record_command(host=host, gate=gate, status=status) for status in _STATUSES}
            for gate in _GATES
        },
    }


def _record_command(*, host: str, gate: str, status: str) -> str:
    args = ["uv", "run", "python", "scripts/record_host_manual_run.py"]
    if gate == "first_10_minutes_replay":
        args.extend(["--kind", "first-10-minutes"])
    args.extend(
        [
            "--host",
            host,
            "--status",
            status,
            "--date",
            "YYYY-MM-DD",
            "--evidence",
            _evidence_note(host=host, gate=gate, status=status),
        ]
    )
    if gate == "first_10_minutes_replay":
        args.extend(["--artifact", "docs/assets/demo/demo_report.md"])
    return " ".join(shlex.quote(arg) for arg in args)


def _evidence_note(*, host: str, gate: str, status: str) -> str:
    if status == "pending":
        return f"{host} {gate} was not run in the real host UI."
    if status == "blocked":
        return f"{host} {gate} blocked at <first failing gate>; redacted symptom: <symptom>."
    return f"{host} {gate} passed in the real host UI with redacted reviewer-observed evidence."


if __name__ == "__main__":
    main()
