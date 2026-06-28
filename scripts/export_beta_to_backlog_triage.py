"""Export beta validation signal mapped to product-depth backlog targets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_validation_status import build_beta_validation_status
from scripts.export_product_depth_backlog import build_product_depth_backlog
from scripts.export_product_depth_gate import build_product_depth_gate


def build_beta_to_backlog_triage() -> dict[str, Any]:
    """Build beta-to-backlog triage without inventing beta findings."""
    beta_status = build_beta_validation_status()
    backlog = build_product_depth_backlog()
    gate = build_product_depth_gate()
    lanes = [_triage_lane(item=item, beta_status=beta_status, gate=gate) for item in backlog["items"]]
    promoted_count = sum(lane["recommendation_status"] == "ready_for_depth_plan" for lane in lanes)
    return {
        "triage_status": "ready_for_depth_planning" if promoted_count else "blocked_until_beta_signal",
        "product_depth_allowed": gate["product_depth_allowed"],
        "beta_validation_status": beta_status["validation_status"],
        "summary": {
            "record_count": beta_status["summary"]["record_count"],
            "workflow_count": beta_status["summary"]["workflow_count"],
            "covered_workflow_count": beta_status["summary"]["covered_workflow_count"],
            "backlog_item_count": len(lanes),
            "promoted_backlog_item_count": promoted_count,
        },
        "triage_policy": (
            "Promote product-depth work only when repeated privacy-safe beta records support a backlog bucket and "
            "the product-depth gate is open."
        ),
        "triage_lanes": lanes,
        "blocked_reasons": gate["blocked_reasons"],
        "next_actions": [
            "Collect one privacy-safe beta validation record for each beta workflow.",
            "Regenerate beta validation status and this triage report after recording attempts.",
            "Promote only repeated or high-confidence beta findings into implementation plans.",
        ],
        "source_docs": [
            "docs/BETA_VALIDATION_STATUS.md",
            "docs/BETA_VALIDATION_RECORDING_PACK.md",
            "docs/PRODUCT_DEPTH_BACKLOG.md",
            "docs/PRODUCT_DEPTH_GATE.md",
        ],
    }


def render_beta_to_backlog_triage_markdown(triage: dict[str, Any]) -> str:
    """Render beta-to-backlog triage as Markdown."""
    lines = [
        "# Beta-to-Backlog Triage",
        "",
        f"Triage status: `{triage['triage_status']}`",
        f"Product depth allowed: `{str(triage['product_depth_allowed']).lower()}`",
        f"Beta validation status: `{triage['beta_validation_status']}`",
        "",
        "## Triage Policy",
        "",
        triage["triage_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in triage["summary"].items())
    lines.extend(["", "## Blocked Reasons", ""])
    if triage["blocked_reasons"]:
        lines.extend(f"- `{reason}`" for reason in triage["blocked_reasons"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Triage Lanes",
            "",
            "| Bucket | Signal Count | Product Area | Recommendation Status | Candidate |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"`{lane['triage_bucket']}` | "
        f"`{lane['signal_count']}` | "
        f"`{lane['product_area']}` | "
        f"`{lane['recommendation_status']}` | "
        f"{lane['candidate']} |"
        for lane in triage["triage_lanes"]
    )
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in triage["next_actions"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in triage["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for beta-to-backlog triage exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_beta_to_backlog_triage_markdown(build_beta_to_backlog_triage())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _triage_lane(*, item: dict[str, str], beta_status: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    signal_count = beta_status["triage_bucket_counts"][item["triage_bucket"]]
    return {
        "triage_bucket": item["triage_bucket"],
        "signal_count": signal_count,
        "product_area": item["product_area"],
        "priority": item["priority"],
        "candidate": item["candidate"],
        "success_signal": item["success_signal"],
        "recommendation_status": _recommendation_status(signal_count=signal_count, gate=gate),
    }


def _recommendation_status(*, signal_count: int, gate: dict[str, Any]) -> str:
    if signal_count == 0:
        return "blocked_no_beta_signal"
    if not gate["product_depth_allowed"]:
        return "blocked_by_product_depth_gate"
    return "ready_for_depth_plan"


if __name__ == "__main__":
    main()
