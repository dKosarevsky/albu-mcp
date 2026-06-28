from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_beta_to_backlog_triage import (
    build_beta_to_backlog_triage,
    render_beta_to_backlog_triage_markdown,
)


def test_beta_to_backlog_triage_blocks_without_beta_signal() -> None:
    triage = build_beta_to_backlog_triage()

    assert triage["triage_status"] == "blocked_until_beta_signal"
    assert triage["product_depth_allowed"] is False
    assert triage["beta_validation_status"] == "manual_beta_required"
    assert triage["summary"] == {
        "record_count": 0,
        "workflow_count": 3,
        "covered_workflow_count": 0,
        "backlog_item_count": 5,
        "promoted_backlog_item_count": 0,
    }
    assert triage["blocked_reasons"] == ["rc_cutover_blocked", "beta_validation_incomplete"]
    assert all(lane["signal_count"] == 0 for lane in triage["triage_lanes"])
    assert all(lane["recommendation_status"] == "blocked_no_beta_signal" for lane in triage["triage_lanes"])


def test_beta_to_backlog_triage_markdown_is_decision_focused() -> None:
    markdown = render_beta_to_backlog_triage_markdown(build_beta_to_backlog_triage())

    assert markdown.startswith("# Beta-to-Backlog Triage\n")
    assert "Triage status: `blocked_until_beta_signal`" in markdown
    assert "Promote product-depth work only when repeated privacy-safe beta records" in markdown
    assert "| `host_setup_gap` | `0` | `host_onboarding` | `blocked_no_beta_signal` |" in markdown
    assert "`beta_validation_incomplete`" in markdown


def test_committed_beta_to_backlog_triage_is_current() -> None:
    triage_path = Path("docs/BETA_TO_BACKLOG_TRIAGE.md")

    assert triage_path.read_text(encoding="utf-8") == render_beta_to_backlog_triage_markdown(
        build_beta_to_backlog_triage()
    )


def test_beta_to_backlog_triage_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "beta-to-backlog-triage.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_beta_to_backlog_triage.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Beta-to-Backlog Triage\n")
