"""Export RC host evidence operations pack without fabricating host evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_v1_rc_cutover_gate import build_v1_rc_cutover_gate
from scripts.export_p0_evidence_regeneration_pack import build_p0_evidence_regeneration_pack
from scripts.export_p0_host_evidence_ledger import build_p0_host_evidence_ledger

_DEFAULT_RECORDS_PATH = Path("docs/HOST_MANUAL_RUNS.json")


def build_rc_host_evidence_ops(records_path: Path = _DEFAULT_RECORDS_PATH) -> dict[str, Any]:
    """Build an operator pack for real-host evidence execution."""
    ledger = build_p0_host_evidence_ledger(records_path)
    regeneration_pack = build_p0_evidence_regeneration_pack(records_path)
    rc_gate = build_v1_rc_cutover_gate(records_path=records_path)
    return {
        "package": rc_gate["package"],
        "package_version": rc_gate["package_version"],
        "records_path": str(records_path),
        "required_hosts": ledger["target_hosts"],
        "ops_status": "ready_for_rc_cutover" if rc_gate["cutover_allowed"] else "blocked_until_real_host_runs",
        "rc_cutover_allowed": rc_gate["cutover_allowed"],
        "p0_summary": ledger["summary"],
        "gate_records": _flat_gate_records(ledger),
        "non_fabrication_policy": "Do not record passed evidence without a real host UI run.",
        "run_commands": [
            "uv run python scripts/check_p0_host_run_preflight.py",
            "uv run python scripts/export_p0_host_run_session.py --output docs/P0_HOST_RUN_SESSION.md",
            "uv run python scripts/verify_host_evidence_import.py --input /path/to/host-evidence-candidate.json",
            "uv run python scripts/validate_host_manual_runs.py",
        ],
        "after_recording_commands": regeneration_pack["gated_regeneration_commands"],
        "rc_gate_commands": [
            "uv run python scripts/check_v1_rc_cutover_gate.py --output docs/V1_RC_CUTOVER_GATE.md",
            "uv run python scripts/check_v1_rc_cutover_gate.py --require-open",
        ],
        "blocked_publish_commands": rc_gate["blocked_publish_commands"],
        "source_docs": [
            "docs/P0_HOST_RUN_SESSION.md",
            "docs/P0_HOST_RUN_PREFLIGHT.md",
            "docs/P0_EVIDENCE_IMPORT_GUIDE.md",
            "docs/P0_EVIDENCE_REGENERATION_PACK.md",
            "docs/V1_RC_CUTOVER_GATE.md",
        ],
        "next_action": _next_action(rc_cutover_allowed=rc_gate["cutover_allowed"]),
    }


def render_rc_host_evidence_ops_markdown(ops: dict[str, Any]) -> str:
    """Render RC host evidence operations as Markdown."""
    lines = [
        "# RC Host Evidence Ops",
        "",
        f"Package: `{ops['package']}=={ops['package_version']}`",
        f"Records path: `{ops['records_path']}`",
        f"Required hosts: `{', '.join(ops['required_hosts'])}`",
        f"Ops status: `{ops['ops_status']}`",
        f"RC cutover allowed: `{str(ops['rc_cutover_allowed']).lower()}`",
        "",
        "## Non-Fabrication Policy",
        "",
        ops["non_fabrication_policy"],
        "",
        "## P0 Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in ops["p0_summary"].items())
    lines.extend(
        [
            "",
            "## Gate Records",
            "",
            "| Host | Gate | Record Status | Date | Evidence |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"{record['host']} | "
        f"`{record['gate']}` | "
        f"`{record['record_status']}` | "
        f"`{record['date']}` | "
        f"{record['evidence']} |"
        for record in ops["gate_records"]
    )
    lines.extend(["", "## Run Commands", ""])
    lines.extend(f"- `{command}`" for command in ops["run_commands"])
    lines.extend(["", "## After Recording Commands", ""])
    lines.extend(f"- `{command}`" for command in ops["after_recording_commands"])
    lines.extend(["", "## RC Gate Commands", ""])
    lines.extend(f"- `{command}`" for command in ops["rc_gate_commands"])
    lines.extend(["", "## Blocked Publish Commands", ""])
    if ops["blocked_publish_commands"]:
        lines.extend(f"- `{command}`" for command in ops["blocked_publish_commands"])
    else:
        lines.append("- none")
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in ops["source_docs"])
    lines.extend(["", "## Next Action", "", ops["next_action"]])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for RC host evidence ops exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=_DEFAULT_RECORDS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_rc_host_evidence_ops_markdown(build_rc_host_evidence_ops(args.records))
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _flat_gate_records(ledger: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "host": host["host"],
            "gate": gate["gate"],
            "record_status": gate["record_status"],
            "date": gate["date"],
            "evidence": gate["evidence"],
        }
        for host in ledger["host_gates"]
        for gate in host["gates"]
    ]


def _next_action(*, rc_cutover_allowed: bool) -> str:
    if rc_cutover_allowed:
        return "Run the hard RC gate with --require-open, then prepare the release candidate."
    return (
        "Run real Codex and Claude Code host UI sessions, verify evidence candidates, and record only observed results."
    )


if __name__ == "__main__":
    main()
