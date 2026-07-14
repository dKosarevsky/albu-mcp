from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_product_depth_selection import (
    build_product_depth_selection,
    render_product_depth_selection_markdown,
)


def test_product_depth_selection_recommends_first_p1_but_keeps_it_blocked() -> None:
    selection = build_product_depth_selection()

    assert selection["selection_status"] == "blocked_until_depth_gate_opens"
    assert selection["implementation_allowed"] is False
    assert selection["blocked_reasons"] == ["rc_cutover_blocked", "beta_validation_incomplete"]
    assert selection["recommended_candidate"]["product_area"] == "host_onboarding"
    assert selection["recommended_candidate"]["priority"] == "p1_after_p0"
    assert selection["recommended_candidate"]["triage_bucket"] == "host_setup_gap"
    assert selection["recommended_candidate"]["candidate"] == (
        "Host-specific setup probes and clearer blocked evidence capture."
    )
    assert selection["decision_policy"] == "Select one P1 depth item only after RC and beta validation gates open."


def test_product_depth_selection_markdown_is_gate_aware() -> None:
    markdown = render_product_depth_selection_markdown(build_product_depth_selection())

    assert markdown.startswith("# Product Depth Selection\n")
    assert "Selection status: `blocked_until_depth_gate_opens`" in markdown
    assert "Implementation allowed: `false`" in markdown
    assert "## Recommended Candidate" in markdown
    assert "`host_onboarding`" in markdown
    assert "`host_setup_gap`" in markdown
    assert "Complete P0 real-host evidence and beta validation before implementation." in markdown


def test_committed_product_depth_selection_is_current() -> None:
    selection_path = Path("docs/PRODUCT_DEPTH_SELECTION.md")

    assert selection_path.read_text(encoding="utf-8") == render_product_depth_selection_markdown(
        build_product_depth_selection()
    )
    assert "[PRODUCT_DEPTH_SELECTION.md](PRODUCT_DEPTH_SELECTION.md)" in Path("docs/INDEX.md").read_text(
        encoding="utf-8"
    )


def test_product_depth_selection_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "product-depth-selection.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_product_depth_selection.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Product Depth Selection\n")
