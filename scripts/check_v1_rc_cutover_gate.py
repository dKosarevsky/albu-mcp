"""Check the hard v1 RC cutover gate before tagging or publishing."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_p0_host_evidence_ledger import build_p0_host_evidence_ledger
from scripts.export_v1_rc_automation_pack import build_v1_rc_automation_pack
from scripts.historical_status import add_historical_status_banner

_DEFAULT_RECORDS_PATH = Path("docs/HOST_MANUAL_RUNS.json")
_DEFAULT_RELEASE_TAG = "vX.Y.Z-rc.1"


def build_v1_rc_cutover_gate(
    *,
    tag: str = _DEFAULT_RELEASE_TAG,
    records_path: Path = _DEFAULT_RECORDS_PATH,
) -> dict[str, Any]:
    """Build the hard RC cutover gate without mutating release state."""
    ledger = build_p0_host_evidence_ledger(records_path)
    automation_pack = build_v1_rc_automation_pack()
    failed_gates = _failed_gates(ledger)
    cutover_allowed = automation_pack["release_candidate_allowed"] and not failed_gates
    publish_commands = [_with_release_tag(command, tag=tag) for command in automation_pack["publish_commands"]]
    return {
        "package": automation_pack["package"],
        "package_version": automation_pack["package_version"],
        "release_tag": tag,
        "required_hosts": automation_pack["required_hosts"],
        "gate_status": "open" if cutover_allowed else "blocked",
        "cutover_allowed": cutover_allowed,
        "rc_decision": automation_pack["rc_decision"],
        "blocked_reason": "none" if cutover_allowed else "p0_host_evidence_missing_or_blocked",
        "gate_policy": ("The RC cutover gate refuses release while any P0 real-host evidence gate is not passed."),
        "p0_summary": ledger["summary"],
        "failed_gates": failed_gates,
        "preflight_commands": automation_pack["preflight_commands"],
        "publish_commands": publish_commands if cutover_allowed else [],
        "blocked_publish_commands": [] if cutover_allowed else publish_commands,
        "source_docs": [
            "docs/P0_HOST_EVIDENCE_LEDGER.md",
            "docs/P0_EVIDENCE_REGENERATION_PACK.md",
            "docs/V1_RC_READINESS.md",
            "docs/V1_RC_AUTOMATION_PACK.md",
        ],
        "next_action": _next_action(cutover_allowed=cutover_allowed),
    }


def render_v1_rc_cutover_gate_markdown(gate: dict[str, Any]) -> str:
    """Render the hard v1 RC cutover gate as Markdown."""
    lines = [
        "# V1 RC Cutover Gate",
        "",
        f"Package: `{gate['package']}=={gate['package_version']}`",
        f"Release tag: `{gate['release_tag']}`",
        f"Required hosts: `{', '.join(gate['required_hosts'])}`",
        f"Gate status: `{gate['gate_status']}`",
        f"Cutover allowed: `{str(gate['cutover_allowed']).lower()}`",
        f"RC decision: `{gate['rc_decision']}`",
        f"Blocked reason: `{gate['blocked_reason']}`",
        "",
        "## Gate Policy",
        "",
        gate["gate_policy"],
        "",
        "## P0 Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in gate["p0_summary"].items())
    lines.extend(
        [
            "",
            "## Failed Gates",
            "",
            "| Host | Gate | Record Status | Date | Evidence |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if gate["failed_gates"]:
        lines.extend(
            "| "
            f"{record['host']} | "
            f"`{record['gate']}` | "
            f"`{record['record_status']}` | "
            f"`{record['date']}` | "
            f"{record['evidence']} |"
            for record in gate["failed_gates"]
        )
    else:
        lines.append("| none | `none` | `passed` | `recorded` | No failed P0 gates. |")
    lines.extend(["", "## Preflight Commands", ""])
    lines.extend(f"- `{command}`" for command in gate["preflight_commands"])
    lines.extend(["", "## Publish Commands", ""])
    if gate["publish_commands"]:
        lines.extend(f"- `{command}`" for command in gate["publish_commands"])
    else:
        lines.append("- none")
    lines.extend(["", "## Blocked Publish Commands", ""])
    if gate["blocked_publish_commands"]:
        lines.extend(f"- `{command}`" for command in gate["blocked_publish_commands"])
    else:
        lines.append("- none")
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in gate["source_docs"])
    lines.extend(["", "## Next Action", "", gate["next_action"]])
    return add_historical_status_banner("\n".join(lines) + "\n")


def main() -> None:
    """CLI entrypoint for v1 RC cutover gate checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=_DEFAULT_RELEASE_TAG)
    parser.add_argument("--records", type=Path, default=_DEFAULT_RECORDS_PATH)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--require-open",
        action="store_true",
        help="Exit with status 1 while the hard RC cutover gate is blocked.",
    )
    args = parser.parse_args()

    gate = build_v1_rc_cutover_gate(tag=args.tag, records_path=args.records)
    content = (
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_v1_rc_cutover_gate_markdown(gate)
    )
    _write_or_print(content=content, output=args.output)
    if args.require_open and not gate["cutover_allowed"]:
        raise SystemExit(1)


def _failed_gates(ledger: dict[str, Any]) -> list[dict[str, str]]:
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
        if gate["record_status"] != "passed"
    ]


def _with_release_tag(command: str, *, tag: str) -> str:
    return command.replace(_DEFAULT_RELEASE_TAG, tag)


def _next_action(*, cutover_allowed: bool) -> str:
    if cutover_allowed:
        return "Run preflight commands, then tag and publish the v1 release candidate."
    return "Do not tag or publish the RC; complete P0 real-host evidence and rerun this gate with --require-open."


def _write_or_print(*, content: str, output: Path | None) -> None:
    if output is None:
        sys.stdout.write(content)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
