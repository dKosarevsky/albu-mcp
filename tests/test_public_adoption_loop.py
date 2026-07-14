from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_public_adoption_loop import build_public_adoption_loop, render_public_adoption_loop_markdown


def test_public_adoption_loop_covers_product_feedback_cycle() -> None:
    loop = build_public_adoption_loop()
    markdown = render_public_adoption_loop_markdown(loop)

    assert [stage["id"] for stage in loop["stages"]] == [
        "discover",
        "first_run",
        "review_decision",
        "feedback_intake",
        "release_response",
    ]
    assert loop["telemetry_policy"] == "No automatic telemetry; collect explicit, privacy-safe feedback only."
    assert "interpret_preview_feedback" in markdown
    assert "plan_preview_review" in markdown
    assert "host-acceptance.yml" in markdown
    assert "dataset-health.yml" in markdown
    assert "weekly triage" in markdown.lower()


def test_committed_public_adoption_loop_is_current() -> None:
    loop_path = Path("docs/PUBLIC_ADOPTION_LOOP.md")

    assert loop_path.read_text(encoding="utf-8") == render_public_adoption_loop_markdown(build_public_adoption_loop())
    assert "[PUBLIC_ADOPTION_LOOP.md](PUBLIC_ADOPTION_LOOP.md)" in Path("docs/INDEX.md").read_text(encoding="utf-8")
    assert "docs/PUBLIC_ADOPTION_LOOP.md" in Path("docs/NETWORK_GROWTH.md").read_text(encoding="utf-8")


def test_public_adoption_loop_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "public-adoption-loop.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_public_adoption_loop.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# Public Adoption Loop\n")
    assert "No automatic telemetry" in content
