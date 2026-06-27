"""Export v1 trust gates without fabricating manual host evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_v1_launch_report import build_v1_launch_report


def build_v1_trust_gates() -> dict[str, Any]:
    """Build a deterministic v1 trust gate report from committed evidence."""
    launch_report = build_v1_launch_report()
    manual_gates = _manual_gates(launch_report)
    return {
        "package": launch_report["package"],
        "package_version": launch_report["package_version"],
        "ready_for_v1": launch_report["ready_for_v1"],
        "manual_evidence_required": bool(manual_gates),
        "automated_gates": [
            {
                "code": "release_readiness",
                "status": "configured",
                "evidence": "scripts/check_release_readiness.py covers committed release gates.",
            },
            {
                "code": "host_proof_sprint_docs",
                "status": "configured",
                "evidence": "docs/HOST_PROOF_SPRINT_CHECKLIST.md provides host-by-host commands.",
            },
            {
                "code": "v1_launch_report",
                "status": "configured",
                "evidence": "docs/V1_LAUNCH_REPORT.md is generated from committed evidence state.",
            },
        ],
        "manual_gates": manual_gates,
        "release_decision": (
            "Do not cut v1.0.0 until every manual gate is passed."
            if manual_gates
            else "v1.0.0 can proceed after final release readiness and publish checks."
        ),
    }


def render_v1_trust_gates_markdown(report: dict[str, Any]) -> str:
    """Render v1 trust gates as Markdown."""
    lines = [
        "# V1 Trust Gates",
        "",
        f"Package: `{report['package']}=={report['package_version']}`",
        f"Ready for v1: `{str(report['ready_for_v1']).lower()}`",
        f"Manual evidence required: `{str(report['manual_evidence_required']).lower()}`",
        "",
        "## Release Decision",
        "",
        report["release_decision"],
        "",
        "## Automated Gates",
        "",
    ]
    lines.extend(f"- `{gate['code']}`: `{gate['status']}` — {gate['evidence']}" for gate in report["automated_gates"])
    lines.extend(["", "## Manual Gates", ""])
    if report["manual_gates"]:
        lines.extend(
            f"- {gate['host']} / {gate['kind']}: `{gate['status']}` — {gate['evidence']}"
            for gate in report["manual_gates"]
        )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for v1 trust gate exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    report = build_v1_trust_gates()
    content = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_v1_trust_gates_markdown(report)
    )
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _manual_gates(launch_report: dict[str, Any]) -> list[dict[str, str]]:
    gates = [
        {
            "host": item["host"],
            "kind": "manual Host UI evidence",
            "status": item["status"],
            "evidence": item["evidence"],
        }
        for item in launch_report["manual_host_ui"]
        if not item["ok"]
    ]
    gates.extend(
        {
            "host": item["host"],
            "kind": "first 10 minutes replay",
            "status": item["status"],
            "evidence": item["evidence"],
        }
        for item in launch_report["first_10_minutes_replay"]
        if not item["ok"]
    )
    return gates


if __name__ == "__main__":
    main()
