"""Export a gated P0 evidence regeneration pack for RC artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_p0_host_evidence_ledger import build_p0_host_evidence_ledger
from scripts.export_v1_rc_readiness_report import build_v1_rc_readiness_report

_DEFAULT_RECORDS_PATH = Path("docs/HOST_MANUAL_RUNS.json")


def build_p0_evidence_regeneration_pack(records_path: Path = _DEFAULT_RECORDS_PATH) -> dict[str, Any]:
    """Build a deterministic regeneration pack without running gated report exports."""
    ledger = build_p0_host_evidence_ledger(records_path)
    rc_report = build_v1_rc_readiness_report()
    rc_regeneration_allowed = ledger["ledger_status"] == "ready_for_rc"
    return {
        "package": rc_report["package"],
        "package_version": rc_report["package_version"],
        "records_path": ledger["records_path"],
        "target_hosts": ledger["target_hosts"],
        "pack_status": "ready_to_regenerate" if rc_regeneration_allowed else "blocked_until_p0_evidence",
        "rc_regeneration_allowed": rc_regeneration_allowed,
        "blocked_reason": "none" if rc_regeneration_allowed else "p0_host_evidence_missing_or_blocked",
        "gate_policy": (
            "Regenerate RC cutover artifacts only after real P0 host evidence records pass. "
            "Do not treat generated RC artifacts as release-ready while this pack is blocked."
        ),
        "summary": ledger["summary"],
        "gate_records": _flat_gate_records(ledger),
        "safe_anytime_commands": [
            "uv run python scripts/check_p0_host_run_preflight.py",
            "uv run python scripts/verify_host_evidence_import.py",
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md",
            "uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md",
            "uv run python scripts/check_release_readiness.py",
        ],
        "gated_regeneration_commands": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md",
            "uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md",
            "uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md",
            "uv run python scripts/export_v1_rc_release_packet.py --output docs/V1_RC_RELEASE_PACKET.md",
            "uv run python scripts/export_v1_rc_cutover_checklist.py --output docs/V1_RC_CUTOVER_CHECKLIST.md",
            "uv run python scripts/export_v1_rc_automation_pack.py --output docs/V1_RC_AUTOMATION_PACK.md",
            "uv run python scripts/export_v1_growth_cutover_report.py --output docs/V1_GROWTH_CUTOVER_REPORT.md",
            "uv run python scripts/check_release_readiness.py",
        ],
        "source_docs": [
            "docs/P0_HOST_RUN_SESSION.md",
            "docs/P0_HOST_RUN_PREFLIGHT.md",
            "docs/P0_EVIDENCE_IMPORT_GUIDE.md",
            "docs/P0_HOST_EVIDENCE_LEDGER.md",
            "docs/V1_RC_READINESS.md",
        ],
        "next_action": _next_action(rc_regeneration_allowed=rc_regeneration_allowed),
    }


def render_p0_evidence_regeneration_pack_markdown(pack: dict[str, Any]) -> str:
    """Render the gated P0 evidence regeneration pack as Markdown."""
    lines = [
        "# P0 Evidence Regeneration Pack",
        "",
        f"Package: `{pack['package']}=={pack['package_version']}`",
        f"Records path: `{pack['records_path']}`",
        f"Target hosts: `{', '.join(pack['target_hosts'])}`",
        f"Pack status: `{pack['pack_status']}`",
        f"RC regeneration allowed: `{str(pack['rc_regeneration_allowed']).lower()}`",
        f"Blocked reason: `{pack['blocked_reason']}`",
        "",
        "## Gate Policy",
        "",
        pack["gate_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in pack["summary"].items())
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
        for record in pack["gate_records"]
    )
    lines.extend(["", "## Safe Anytime Commands", ""])
    lines.extend(f"- `{command}`" for command in pack["safe_anytime_commands"])
    lines.extend(["", "## Gated Regeneration Commands", ""])
    lines.extend(f"- `{command}`" for command in pack["gated_regeneration_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in pack["source_docs"])
    lines.extend(["", "## Next Action", "", pack["next_action"]])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for the gated P0 evidence regeneration pack."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=_DEFAULT_RECORDS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_p0_evidence_regeneration_pack_markdown(build_p0_evidence_regeneration_pack(args.records))
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


def _next_action(*, rc_regeneration_allowed: bool) -> str:
    if rc_regeneration_allowed:
        return "Regenerate the RC readiness, release packet, automation pack, and growth cutover reports."
    return "Complete real P0 host runs, verify candidate evidence, and record passed gates before RC cutover."


if __name__ == "__main__":
    main()
