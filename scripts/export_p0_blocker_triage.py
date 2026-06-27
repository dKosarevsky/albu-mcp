"""Export a P0 blocker triage matrix for host evidence failures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_host_failure_cookbook import build_host_failure_cookbook
from scripts.export_p0_evidence_status import build_p0_evidence_status

_ENTRYPOINTS = [
    "docs/P0_HOST_RUNBOOK.md",
    "docs/P0_EVIDENCE_RECORDER.md",
    "docs/HOST_FAILURE_COOKBOOK.md",
]


def build_p0_blocker_triage() -> dict[str, Any]:
    """Build a deterministic P0 blocker triage matrix."""
    status = build_p0_evidence_status()
    cookbook = build_host_failure_cookbook()
    return {
        "source_docs": [
            "docs/P0_EVIDENCE_STATUS.md",
            "docs/HOST_FAILURE_COOKBOOK.md",
            "docs/HOST_UX_HARDENING_LOOP.md",
        ],
        "triage_matrix": [
            _triage_item(host=item["host"], gate=gate)
            for item in status["host_statuses"]
            for gate in item["gates"]
            if gate["status"] != "recorded"
        ],
        "failure_classes": [item["code"] for item in cookbook["failure_cases"]],
        "escalation_rule": "Convert repeated blocked evidence into a regression test before changing product behavior.",
    }


def render_p0_blocker_triage_markdown(triage: dict[str, Any]) -> str:
    """Render P0 blocker triage as Markdown."""
    lines = ["# P0 Blocker Triage Matrix", "", "## Source Docs", ""]
    lines.extend(f"- `{source}`" for source in triage["source_docs"])
    lines.extend(
        [
            "",
            "## Triage Matrix",
            "",
            "| Host | Gate | Evidence Status | Triage Action | Entrypoints |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"{item['host']} | "
        f"`{item['gate']}` | "
        f"`{item['evidence_status']}` | "
        f"`{item['triage_action']}` | "
        f"{', '.join(f'`{entrypoint}`' for entrypoint in item['entrypoints'])} |"
        for item in triage["triage_matrix"]
    )
    lines.extend(["", "## Failure Classes", ""])
    lines.extend(f"- `{failure_class}`" for failure_class in triage["failure_classes"])
    lines.extend(["", "## Escalation Rule", "", triage["escalation_rule"]])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for P0 blocker triage exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_p0_blocker_triage_markdown(build_p0_blocker_triage())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _triage_item(*, host: str, gate: dict[str, str]) -> dict[str, Any]:
    return {
        "host": host,
        "gate": gate["gate"],
        "evidence_status": gate["status"],
        "triage_action": "triage_blocker" if gate["status"] == "blocked" else "run_p0_host_runbook",
        "entrypoints": list(_ENTRYPOINTS),
    }


if __name__ == "__main__":
    main()
