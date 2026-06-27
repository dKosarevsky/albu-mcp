from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_product_depth_gate import build_product_depth_gate, render_product_depth_gate_markdown


def test_product_depth_gate_blocks_until_rc_and_beta_signal() -> None:
    gate = build_product_depth_gate()

    assert gate["gate_status"] == "blocked_by_rc_and_beta_signal"
    assert gate["product_depth_allowed"] is False
    assert gate["rc_cutover_allowed"] is False
    assert gate["beta_validation_status"] == "manual_beta_required"
    assert gate["backlog_status"] == "waiting_for_beta_signal"
    assert gate["prioritization_rule"] == "Do not promote depth work above P0 host evidence until RC gates pass."
    assert gate["blocked_reasons"] == ["rc_cutover_blocked", "beta_validation_incomplete"]


def test_product_depth_gate_markdown_is_release_and_beta_aware() -> None:
    markdown = render_product_depth_gate_markdown(build_product_depth_gate())

    assert markdown.startswith("# Product Depth Gate\n")
    assert "Gate status: `blocked_by_rc_and_beta_signal`" in markdown
    assert "Product depth allowed: `false`" in markdown
    assert "`docs/PRODUCT_DEPTH_BACKLOG.md`" in markdown
    assert "`docs/BETA_VALIDATION_STATUS.md`" in markdown
    assert "`docs/V1_RC_CUTOVER_GATE.md`" in markdown


def test_committed_product_depth_gate_is_current() -> None:
    gate_path = Path("docs/PRODUCT_DEPTH_GATE.md")

    assert gate_path.read_text(encoding="utf-8") == render_product_depth_gate_markdown(build_product_depth_gate())
    assert "[docs/PRODUCT_DEPTH_GATE.md](docs/PRODUCT_DEPTH_GATE.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_product_depth_gate_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "product-depth-gate.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_product_depth_gate.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Product Depth Gate\n")
