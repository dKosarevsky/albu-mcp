"""Export a host UX hardening loop from current launch blockers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_v1_launch_report import build_v1_launch_report

_HOST_ORDER = ("Codex", "Claude Code", "Cursor", "Claude Desktop")
_LOOP_STEPS = [
    "Record blocked evidence with the first failing host gate.",
    "Classify the failure with the host failure cookbook.",
    "Patch host UX docs, config snippets, diagnostics, or product behavior.",
    "Add or update a regression test for the failure class.",
    "Regenerate launch, decision, and execution reports.",
]


def build_host_ux_hardening_loop() -> dict[str, Any]:
    """Build a deterministic hardening loop from host-level launch blockers."""
    launch_report = build_v1_launch_report()
    return {
        "source_reports": [
            "docs/V1_LAUNCH_REPORT.md",
            "docs/HOST_FAILURE_COOKBOOK.md",
            "docs/HOST_MANUAL_RUNS.json",
        ],
        "hardening_queue": [_queue_item(item) for item in _sorted_host_blockers(launch_report["host_blockers"])],
        "loop_steps": list(_LOOP_STEPS),
        "regression_targets": [
            "tests/test_host_failure_cookbook.py",
            "tests/test_host_ux_packets.py",
            "tests/test_manual_host_acceptance_packet.py",
            "tests/test_v1_launch_report.py",
        ],
        "regeneration_commands": [
            "uv run python scripts/export_host_failure_cookbook.py --output docs/HOST_FAILURE_COOKBOOK.md",
            "uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md",
            "uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md",
            "uv run python scripts/export_real_host_evidence_execution_pack.py --output docs/REAL_HOST_EVIDENCE_EXECUTION.md",
            "uv run python scripts/export_host_ux_hardening_loop.py --output docs/HOST_UX_HARDENING_LOOP.md",
        ],
    }


def render_host_ux_hardening_loop_markdown(loop: dict[str, Any]) -> str:
    """Render the host UX hardening loop as Markdown."""
    lines = [
        "# Host UX Hardening Loop",
        "",
        "## Source Reports",
        "",
    ]
    lines.extend(f"- `{source}`" for source in loop["source_reports"])
    lines.extend(
        [
            "",
            "## Hardening Queue",
            "",
            "| Host | Priority | Gate | Evidence Status | Next Action |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if loop["hardening_queue"]:
        lines.extend(
            "| "
            f"{item['host']} | "
            f"`{item['priority']}` | "
            f"`{item['gate']}` | "
            f"`{item['evidence_status']}` | "
            f"`{item['next_action']}` |"
            for item in loop["hardening_queue"]
        )
    else:
        lines.append("| none | `none` | `none` | `recorded` | `no_action` |")
    lines.extend(["", "## Loop Steps", ""])
    lines.extend(f"{index}. {step}" for index, step in enumerate(loop["loop_steps"], start=1))
    lines.extend(["", "## Triage Entrypoints", ""])
    for item in loop["hardening_queue"]:
        lines.extend(
            [
                f"### {item['host']} / {item['gate']}",
                "",
                *[f"- `{entrypoint}`" for entrypoint in item["triage_entrypoints"]],
                "",
            ]
        )
    lines.extend(["## Regression Targets", ""])
    lines.extend(f"- `{target}`" for target in loop["regression_targets"])
    lines.extend(["", "## Regeneration Commands", ""])
    lines.extend(f"- `{command}`" for command in loop["regeneration_commands"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for host UX hardening loop exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_host_ux_hardening_loop_markdown(build_host_ux_hardening_loop())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _queue_item(item: dict[str, str]) -> dict[str, Any]:
    return {
        "host": item["host"],
        "priority": item["priority"],
        "gate": item["gate"],
        "evidence_status": item["evidence_status"],
        "next_action": item["next_action"],
        "triage_entrypoints": [
            "docs/HOST_FAILURE_COOKBOOK.md",
            "albumentationsx://diagnostics/guide",
            "run_host_smoke_check",
        ],
    }


def _sorted_host_blockers(items: list[dict[str, str]]) -> list[dict[str, str]]:
    host_rank = {host: index for index, host in enumerate(_HOST_ORDER)}
    gate_rank = {"first_10_minutes_replay": 0, "manual_host_ui": 1}
    return sorted(
        items,
        key=lambda item: (
            host_rank.get(item["host"], len(host_rank)),
            gate_rank.get(item["gate"], len(gate_rank)),
        ),
    )


if __name__ == "__main__":
    main()
