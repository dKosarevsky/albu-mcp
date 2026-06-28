from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_product_iteration_governor import (
    build_product_iteration_governor,
    render_product_iteration_governor_markdown,
)


def test_product_iteration_governor_defines_100_safe_iteration_goals() -> None:
    governor = build_product_iteration_governor()

    assert governor["iteration_count"] == 100
    assert governor["governor_status"] == "sequenced_not_auto_executed"
    assert governor["execution_policy"] == (
        "Each iteration needs a named goal, tests, readiness checks, and evidence gates before merge."
    )
    assert governor["iterations"][0] == {
        "iteration": 1,
        "goal": "Close P0 real-host evidence for Codex and Claude Code.",
        "lane": "evidence",
        "status": "current_priority",
    }
    assert governor["iterations"][-1]["iteration"] == 100
    assert all(item["status"] != "auto_merge_allowed" for item in governor["iterations"])


def test_product_iteration_governor_markdown_prevents_blind_automation() -> None:
    markdown = render_product_iteration_governor_markdown(build_product_iteration_governor())

    assert markdown.startswith("# Product Iteration Governor\n")
    assert "Governor status: `sequenced_not_auto_executed`" in markdown
    assert "| 100 |" in markdown
    assert "No blind 100-iteration implementation loop is allowed." in markdown
    assert "`uv run pytest -q`" in markdown


def test_committed_product_iteration_governor_is_current() -> None:
    doc_path = Path("docs/PRODUCT_ITERATION_GOVERNOR.md")

    assert doc_path.read_text(encoding="utf-8") == render_product_iteration_governor_markdown(
        build_product_iteration_governor()
    )
    assert "[docs/PRODUCT_ITERATION_GOVERNOR.md](docs/PRODUCT_ITERATION_GOVERNOR.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_product_iteration_governor_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "product-iteration-governor.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_product_iteration_governor.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Product Iteration Governor\n")
