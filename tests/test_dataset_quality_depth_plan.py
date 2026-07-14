from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_dataset_quality_depth_plan import (
    build_dataset_quality_depth_plan,
    render_dataset_quality_depth_plan_markdown,
)


def test_dataset_quality_depth_plan_waits_for_beta_signal() -> None:
    plan = build_dataset_quality_depth_plan()

    assert plan["plan_status"] == "waiting_for_beta_signal"
    assert plan["triage_bucket"] == "dataset_quality_gap"
    assert plan["product_area"] == "dataset_quality"
    assert plan["beta_record_count"] == 0
    assert "annotation_consistency_depth" in [track["track_id"] for track in plan["tracks"]]
    assert (
        "Do not change runtime dataset-quality behavior without repeated beta feedback or a failing test."
        in plan["implementation_guards"]
    )


def test_dataset_quality_depth_plan_markdown_is_test_first() -> None:
    markdown = render_dataset_quality_depth_plan_markdown(build_dataset_quality_depth_plan())

    assert markdown.startswith("# Dataset Quality Depth Plan\n")
    assert "Plan status: `waiting_for_beta_signal`" in markdown
    assert "Product area: `dataset_quality`" in markdown
    assert "| `annotation_consistency_depth` |" in markdown
    assert "## Implementation Guards" in markdown
    assert (
        "Do not change runtime dataset-quality behavior without repeated beta feedback or a failing test." in markdown
    )


def test_committed_dataset_quality_depth_plan_is_current() -> None:
    plan_path = Path("docs/DATASET_QUALITY_DEPTH_PLAN.md")

    assert plan_path.read_text(encoding="utf-8") == render_dataset_quality_depth_plan_markdown(
        build_dataset_quality_depth_plan()
    )
    assert "[DATASET_QUALITY_DEPTH_PLAN.md](DATASET_QUALITY_DEPTH_PLAN.md)" in Path("docs/INDEX.md").read_text(
        encoding="utf-8"
    )


def test_dataset_quality_depth_plan_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "dataset-quality-depth-plan.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_dataset_quality_depth_plan.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Dataset Quality Depth Plan\n")
