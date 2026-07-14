from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_product_depth_backlog import build_product_depth_backlog, render_product_depth_backlog_markdown


def test_product_depth_backlog_maps_triage_buckets_to_product_work() -> None:
    backlog = build_product_depth_backlog()

    assert backlog["backlog_status"] == "waiting_for_beta_signal"
    assert backlog["prioritization_rule"] == "Do not promote depth work above P0 host evidence until RC gates pass."
    assert [item["triage_bucket"] for item in backlog["items"]] == [
        "host_setup_gap",
        "review_agent_v3_gap",
        "dataset_quality_gap",
        "docs_gap",
        "workflow_fit_gap",
    ]
    assert backlog["items"][0]["priority"] == "p1_after_p0"
    assert backlog["items"][1]["product_area"] == "preview_review_agent"
    assert "Convert repeated reports into tests before changing behavior." in backlog["quality_bar"]


def test_product_depth_backlog_markdown_is_actionable() -> None:
    markdown = render_product_depth_backlog_markdown(build_product_depth_backlog())

    assert markdown.startswith("# Product Depth Backlog\n")
    assert "Backlog status: `waiting_for_beta_signal`" in markdown
    assert "## Prioritization Rule" in markdown
    assert "Do not promote depth work above P0 host evidence until RC gates pass." in markdown
    assert "| `review_agent_v3_gap` | `preview_review_agent` | `p1_after_p0` |" in markdown
    assert "## Quality Bar" in markdown
    assert "Convert repeated reports into tests before changing behavior." in markdown


def test_committed_product_depth_backlog_is_current() -> None:
    backlog_path = Path("docs/PRODUCT_DEPTH_BACKLOG.md")

    assert backlog_path.read_text(encoding="utf-8") == render_product_depth_backlog_markdown(
        build_product_depth_backlog()
    )
    assert "[PRODUCT_DEPTH_BACKLOG.md](PRODUCT_DEPTH_BACKLOG.md)" in Path("docs/INDEX.md").read_text(encoding="utf-8")


def test_product_depth_backlog_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "product-depth-backlog.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_product_depth_backlog.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Product Depth Backlog\n")
