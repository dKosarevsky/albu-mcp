"""Export the evidence-first v1 operator packet."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_p0_host_evidence_ledger import build_p0_host_evidence_ledger
from scripts.export_v1_rc_automation_pack import build_v1_rc_automation_pack


def build_v1_evidence_operator_packet() -> dict[str, Any]:
    """Build an operator packet from committed evidence records without fabricating evidence."""
    ledger = build_p0_host_evidence_ledger()
    automation_pack = build_v1_rc_automation_pack()
    return {
        "packet_status": ledger["ledger_status"],
        "rc_publish_allowed": automation_pack["release_candidate_allowed"],
        "required_hosts": ledger["target_hosts"],
        "operator_policy": "Do not create an RC tag until all P0 host gates are passed in real host UI.",
        "summary": ledger["summary"],
        "operator_lanes": [_operator_lane(host_gate) for host_gate in ledger["host_gates"]],
        "post_recording_commands": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md",
            "uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md",
            "uv run python scripts/export_v1_evidence_operator_packet.py --output docs/V1_EVIDENCE_OPERATOR_PACKET.md",
            "uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md",
            "uv run python scripts/export_v1_rc_automation_pack.py --output docs/V1_RC_AUTOMATION_PACK.md",
            "uv run python scripts/check_release_readiness.py",
        ],
        "source_docs": [
            "docs/P0_HOST_EVIDENCE_LEDGER.md",
            "docs/V1_RC_AUTOMATION_PACK.md",
            "docs/HOST_MANUAL_RUNS.json",
        ],
    }


def render_v1_evidence_operator_packet_markdown(packet: dict[str, Any]) -> str:
    """Render the v1 evidence operator packet as Markdown."""
    lines = [
        "# V1 Evidence Operator Packet",
        "",
        f"Packet status: `{packet['packet_status']}`",
        f"RC publish allowed: `{str(packet['rc_publish_allowed']).lower()}`",
        f"Required hosts: `{', '.join(packet['required_hosts'])}`",
        "",
        "## Operator Policy",
        "",
        packet["operator_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in packet["summary"].items())
    lines.extend(["", "## Operator Lanes", ""])
    for lane in packet["operator_lanes"]:
        lines.extend(
            [
                f"## {lane['host']}",
                "",
                "Host prompt:",
                "",
                f"> {lane['host_prompt']}",
                "",
                "Record commands:",
                "",
            ]
        )
        lines.extend(f"- `{command}`" for command in lane["record_commands"])
        lines.extend(["", "Gate statuses:", ""])
        lines.extend(f"- `{gate['gate']}`: `{gate['record_status']}`" for gate in lane["gates"])
        lines.append("")
    lines.extend(["## Post-Recording Commands", ""])
    lines.extend(f"- `{command}`" for command in packet["post_recording_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in packet["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for v1 evidence operator packet exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_v1_evidence_operator_packet_markdown(build_v1_evidence_operator_packet())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _operator_lane(host_gate: dict[str, Any]) -> dict[str, Any]:
    host = host_gate["host"]
    return {
        "host": host,
        "host_prompt": (
            "List AlbumentationsX MCP tools, call run_host_smoke_check, complete the First 10 Minutes workflow, "
            "and record only reviewer-observed real host UI evidence."
        ),
        "gates": host_gate["gates"],
        "record_commands": [gate["record_command"] for gate in host_gate["gates"]],
    }


if __name__ == "__main__":
    main()
