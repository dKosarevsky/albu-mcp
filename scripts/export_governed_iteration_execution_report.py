"""Export the governed execution result for the requested 100 iterations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_product_iteration_governor import build_product_iteration_governor
from scripts.export_rc_release_decision_report import build_rc_release_decision_report


def build_governed_iteration_execution_report() -> dict[str, Any]:
    """Build the governed iteration execution report without running blind iterations."""
    governor = build_product_iteration_governor()
    rc_decision = build_rc_release_decision_report()
    stop_reason = "completed" if rc_decision["decision"] == "go" else "current_priority_gate_blocked"
    return {
        "requested_iteration_count": governor["iteration_count"],
        "executed_iteration_count": 1,
        "stopped_at_iteration": 1,
        "stop_reason": stop_reason,
        "completed_path_count": 3,
        "completed_plan_point_count": 7,
        "execution_policy": governor["execution_policy"],
        "safety_policy": "No blind implementation loop was executed.",
        "completed_paths": [
            "Evidence Unblock path: capture kit prepared; real P0 evidence remains blocked.",
            "Beta Validation Sprint path: capture kit prepared; real beta attempts remain missing.",
            "Policy Assistant MVP path: contract prepared behind gates; runtime behavior not implemented.",
        ],
        "completed_plan_points": [
            "Merged PR #13.",
            "Prepared host evidence capture kit.",
            "Kept P0 outcomes blocked until real host UI evidence exists.",
            "Prepared beta attempt capture kit.",
            "Prepared policy assistant MVP contract behind gates.",
            "Produced RC no-go decision for v1.15.0-rc.1.",
            "Stopped 100-iteration execution at the first blocked governed gate.",
        ],
        "source_docs": [
            "docs/PRODUCT_ITERATION_GOVERNOR.md",
            "docs/RC_RELEASE_DECISION_REPORT.md",
            "docs/HOST_EVIDENCE_CAPTURE_KIT.md",
            "docs/BETA_ATTEMPT_CAPTURE_KIT.md",
            "docs/POLICY_ASSISTANT_MVP_CONTRACT.md",
        ],
    }


def render_governed_iteration_execution_report_markdown(report: dict[str, Any]) -> str:
    """Render the governed iteration execution report as Markdown."""
    lines = [
        "# Governed 100-Iteration Execution Report",
        "",
        f"Requested iterations: `{report['requested_iteration_count']}`",
        f"Executed iterations: `{report['executed_iteration_count']}`",
        f"Stopped at iteration: `{report['stopped_at_iteration']}`",
        f"Stop reason: `{report['stop_reason']}`",
        f"Completed paths: `{report['completed_path_count']}`",
        f"Completed plan points: `{report['completed_plan_point_count']}`",
        "",
        "## Execution Policy",
        "",
        report["execution_policy"],
        report["safety_policy"],
        "",
        "## Completed Paths",
        "",
    ]
    lines.extend(f"- {path}" for path in report["completed_paths"])
    lines.extend(["", "## Completed Plan Points", ""])
    lines.extend(f"{index}. {point}" for index, point in enumerate(report["completed_plan_points"], start=1))
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in report["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for governed iteration execution report exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_governed_iteration_execution_report_markdown(build_governed_iteration_execution_report())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
