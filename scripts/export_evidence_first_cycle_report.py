"""Export the current evidence-first execution cycle report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_v1_rc_cutover_gate import build_v1_rc_cutover_gate
from scripts.export_beta_validation_status import build_beta_validation_status
from scripts.export_product_iteration_governor import build_product_iteration_governor


def build_evidence_first_cycle_report() -> dict[str, Any]:
    """Build a report for the latest evidence-first cycle without fabricating outcomes."""
    gate = build_v1_rc_cutover_gate()
    beta = build_beta_validation_status()
    governor = build_product_iteration_governor()
    blocked_reasons = _blocked_reasons(gate=gate, beta=beta)
    return {
        "cycle_status": "ready_for_rc" if not blocked_reasons else "blocked_before_rc",
        "completed_point_count": 5,
        "rc_decision": gate["rc_decision"],
        "publish_allowed": bool(gate["publish_commands"]),
        "blocked_reasons": blocked_reasons,
        "non_fabrication_policy": "No `passed` P0 evidence or beta record was fabricated.",
        "completed_points": [
            "Merged PR #12 into main.",
            "Ran available live host setup probe and P0 preflight.",
            "Recorded blocked P0 host evidence outcomes from observed environment blockers.",
            "Validated beta records and kept beta attempts missing because no real participants were observed.",
            "Reran readiness and hard RC gate; RC remains hold_rc.",
        ],
        "iteration_execution": {
            "requested_iteration_count": governor["iteration_count"],
            "executed_iteration_count": 1,
            "stopped_at_iteration": 1,
            "stop_reason": "current_priority_gate_blocked",
        },
        "next_required_actions": [
            "Run Codex in an observable MCP host UI and complete run_host_smoke_check.",
            "Expose the Claude Code CLI in PATH, then rerun the Claude Code host lane.",
            "Recruit or observe one real beta attempt for each beta workflow.",
            "Rerun the hard RC gate only after P0 and beta records change.",
        ],
        "source_docs": [
            "docs/HOST_MANUAL_RUNS.json",
            "docs/BETA_VALIDATION_RECORDS.json",
            "docs/V1_RC_CUTOVER_GATE.md",
            "docs/PRODUCT_ITERATION_GOVERNOR.md",
        ],
    }


def render_evidence_first_cycle_report_markdown(report: dict[str, Any]) -> str:
    """Render the evidence-first cycle report as Markdown."""
    iteration = report["iteration_execution"]
    lines = [
        "# Evidence First Cycle Report",
        "",
        f"Cycle status: `{report['cycle_status']}`",
        f"Completed point count: `{report['completed_point_count']}`",
        f"RC decision: `{report['rc_decision']}`",
        f"Publish allowed: `{str(report['publish_allowed']).lower()}`",
        "",
        "## Non-Fabrication Policy",
        "",
        report["non_fabrication_policy"],
        "",
        "## Completed Points",
        "",
    ]
    lines.extend(f"{index}. {point}" for index, point in enumerate(report["completed_points"], start=1))
    lines.extend(["", "## Blocked Reasons", ""])
    if report["blocked_reasons"]:
        lines.extend(f"- `{reason}`" for reason in report["blocked_reasons"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## 100-Iteration Execution",
            "",
            f"100 requested iterations stopped at iteration `{iteration['stopped_at_iteration']}`.",
            f"Executed iterations: `{iteration['executed_iteration_count']}` of "
            f"`{iteration['requested_iteration_count']}`.",
            f"Stop reason: `{iteration['stop_reason']}`.",
            "",
            "## Next Required Actions",
            "",
        ]
    )
    lines.extend(f"- {action}" for action in report["next_required_actions"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in report["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for evidence-first cycle report exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_evidence_first_cycle_report_markdown(build_evidence_first_cycle_report())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _blocked_reasons(*, gate: dict[str, Any], beta: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not gate["cutover_allowed"]:
        reasons.append(gate["blocked_reason"])
    if beta["validation_status"] != "ready_for_depth_triage":
        reasons.append("beta_validation_records_missing")
    return reasons


if __name__ == "__main__":
    main()
