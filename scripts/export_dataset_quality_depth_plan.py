"""Export a beta-driven dataset quality depth plan."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_feedback_status import build_beta_feedback_status
from scripts.export_product_depth_backlog import build_product_depth_backlog


def build_dataset_quality_depth_plan() -> dict[str, Any]:
    """Build the dataset quality depth plan without changing runtime behavior."""
    beta_status = build_beta_feedback_status()
    backlog_item = _dataset_quality_backlog_item()
    return {
        "plan_status": "ready_for_implementation"
        if beta_status["summary"]["record_count"]
        else "waiting_for_beta_signal",
        "triage_bucket": backlog_item["triage_bucket"],
        "product_area": backlog_item["product_area"],
        "priority": backlog_item["priority"],
        "beta_record_count": beta_status["summary"]["record_count"],
        "candidate": backlog_item["candidate"],
        "success_signal": backlog_item["success_signal"],
        "tracks": [
            {
                "track_id": "annotation_consistency_depth",
                "scope": "Deepen COCO/YOLO/class-directory annotation consistency findings.",
                "test_seed": "Add beta-derived missing/orphan/out-of-bounds annotation fixtures.",
            },
            {
                "track_id": "bbox_mask_preview_readiness",
                "scope": "Expose whether bbox and mask datasets are safe to preview before augmentation.",
                "test_seed": "Assert blockers are reported before render_preview_batch is suggested.",
            },
            {
                "track_id": "duplicate_and_split_risk",
                "scope": "Improve duplicate, class imbalance, and split imbalance prioritization.",
                "test_seed": "Add fixtures that distinguish warning-only from render-blocking findings.",
            },
        ],
        "implementation_guards": [
            "Do not change runtime dataset-quality behavior without repeated beta feedback or a failing test.",
            "Keep dataset inspection read-only and bounded by allowed roots.",
            "Preserve existing output contract snapshots unless a public contract change is intentional.",
        ],
        "acceptance_gates": [
            "At least one repeated dataset_quality_gap record exists or a maintainer supplies a concrete failing case.",
            "New tests fail before implementation and pass after implementation.",
            "Preview rendering remains blocked only for high-confidence path or annotation safety issues.",
        ],
        "source_docs": [
            "docs/BETA_FEEDBACK_STATUS.md",
            "docs/PRODUCT_DEPTH_BACKLOG.md",
            "docs/BETA_VALIDATION_SPRINT.md",
        ],
    }


def render_dataset_quality_depth_plan_markdown(plan: dict[str, Any]) -> str:
    """Render the dataset quality depth plan as Markdown."""
    lines = [
        "# Dataset Quality Depth Plan",
        "",
        f"Plan status: `{plan['plan_status']}`",
        f"Triage bucket: `{plan['triage_bucket']}`",
        f"Product area: `{plan['product_area']}`",
        f"Priority: `{plan['priority']}`",
        f"Beta record count: `{plan['beta_record_count']}`",
        "",
        "## Candidate",
        "",
        plan["candidate"],
        "",
        "## Success Signal",
        "",
        plan["success_signal"],
        "",
        "## Tracks",
        "",
        "| Track | Scope | Test Seed |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| `{track['track_id']}` | {track['scope']} | {track['test_seed']} |" for track in plan["tracks"])
    lines.extend(["", "## Implementation Guards", ""])
    lines.extend(f"- {guard}" for guard in plan["implementation_guards"])
    lines.extend(["", "## Acceptance Gates", ""])
    lines.extend(f"- {gate}" for gate in plan["acceptance_gates"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in plan["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for dataset quality depth plan exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_dataset_quality_depth_plan_markdown(build_dataset_quality_depth_plan())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _dataset_quality_backlog_item() -> dict[str, Any]:
    backlog = build_product_depth_backlog()
    return next(item for item in backlog["items"] if item["triage_bucket"] == "dataset_quality_gap")


if __name__ == "__main__":
    main()
