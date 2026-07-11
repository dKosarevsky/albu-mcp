from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_host_ux_hardening_loop import build_host_ux_hardening_loop, render_host_ux_hardening_loop_markdown


def test_host_ux_hardening_loop_prioritizes_host_blockers() -> None:
    loop = build_host_ux_hardening_loop()

    assert loop["source_reports"] == [
        "docs/V1_LAUNCH_REPORT.md",
        "docs/HOST_FAILURE_COOKBOOK.md",
        "docs/HOST_MANUAL_RUNS.json",
    ]
    assert [item["host"] for item in loop["hardening_queue"][:2]] == ["Claude Code", "Claude Code"]
    assert loop["hardening_queue"][0]["priority"] == "p0"
    assert loop["hardening_queue"][0]["gate"] == "first_10_minutes_replay"
    assert loop["hardening_queue"][0]["triage_entrypoints"] == [
        "docs/HOST_FAILURE_COOKBOOK.md",
        "albumentationsx://diagnostics/guide",
        "run_host_smoke_check",
    ]
    assert loop["loop_steps"] == [
        "Record blocked evidence with the first failing host gate.",
        "Classify the failure with the host failure cookbook.",
        "Patch host UX docs, config snippets, diagnostics, or product behavior.",
        "Add or update a regression test for the failure class.",
        "Regenerate launch, decision, and execution reports.",
    ]


def test_host_ux_hardening_loop_markdown_is_actionable() -> None:
    markdown = render_host_ux_hardening_loop_markdown(build_host_ux_hardening_loop())

    assert markdown.startswith("# Host UX Hardening Loop\n")
    assert "## Hardening Queue" in markdown
    assert "| Claude Code | `p0` | `first_10_minutes_replay` | `blocked` |" in markdown
    assert "## Loop Steps" in markdown
    assert "Classify the failure with the host failure cookbook." in markdown
    assert "## Regression Targets" in markdown
    assert "`tests/test_host_failure_cookbook.py`" in markdown
    assert "## Regeneration Commands" in markdown
    assert "export_real_host_evidence_execution_pack.py --output docs/REAL_HOST_EVIDENCE_EXECUTION.md" in markdown


def test_committed_host_ux_hardening_loop_is_current() -> None:
    loop_path = Path("docs/HOST_UX_HARDENING_LOOP.md")

    assert loop_path.read_text(encoding="utf-8") == render_host_ux_hardening_loop_markdown(
        build_host_ux_hardening_loop()
    )
    assert "[docs/HOST_UX_HARDENING_LOOP.md](docs/HOST_UX_HARDENING_LOOP.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_host_ux_hardening_loop_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "host-ux-hardening-loop.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_host_ux_hardening_loop.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Host UX Hardening Loop\n")
