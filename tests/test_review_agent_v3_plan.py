from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_review_agent_v3_plan import build_review_agent_v3_plan, render_review_agent_v3_plan_markdown


def test_review_agent_v3_plan_waits_for_beta_signal() -> None:
    plan = build_review_agent_v3_plan()

    assert plan["plan_status"] == "waiting_for_beta_signal"
    assert plan["triage_bucket"] == "review_agent_v3_gap"
    assert plan["product_area"] == "preview_review_agent"
    assert plan["beta_record_count"] == 0
    assert (
        "Do not change runtime review behavior without repeated beta feedback or a failing test."
        in plan["implementation_guards"]
    )
    assert "feedback_intent_calibration" in [track["track_id"] for track in plan["tracks"]]


def test_review_agent_v3_plan_markdown_is_test_first() -> None:
    markdown = render_review_agent_v3_plan_markdown(build_review_agent_v3_plan())

    assert markdown.startswith("# Review Agent V3 Plan\n")
    assert "Plan status: `waiting_for_beta_signal`" in markdown
    assert "Product area: `preview_review_agent`" in markdown
    assert "## Implementation Guards" in markdown
    assert "Do not change runtime review behavior without repeated beta feedback or a failing test." in markdown
    assert "| `feedback_intent_calibration` |" in markdown
    assert "## Acceptance Gates" in markdown


def test_committed_review_agent_v3_plan_is_current() -> None:
    plan_path = Path("docs/REVIEW_AGENT_V3_PLAN.md")

    assert plan_path.read_text(encoding="utf-8") == render_review_agent_v3_plan_markdown(build_review_agent_v3_plan())
    assert "[REVIEW_AGENT_V3_PLAN.md](REVIEW_AGENT_V3_PLAN.md)" in Path("docs/INDEX.md").read_text(encoding="utf-8")


def test_review_agent_v3_plan_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "review-agent-v3-plan.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_review_agent_v3_plan.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Review Agent V3 Plan\n")
