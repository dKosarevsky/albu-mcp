from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_real_host_evidence_execution_pack import (
    build_real_host_evidence_execution_pack,
    render_real_host_evidence_execution_pack_markdown,
)


def test_real_host_evidence_execution_pack_tracks_run_queue_and_policy() -> None:
    pack = build_real_host_evidence_execution_pack()

    assert pack["decision"] == "hold_v1"
    assert pack["ready_for_v1"] is False
    assert pack["non_fabrication_policy"] == "Record passed only after a real MCP host UI completes the flow."
    assert [item["host"] for item in pack["run_queue"]] == ["Codex", "Claude Code", "Cursor", "Claude Desktop"]
    assert pack["run_queue"][0]["next_action"] == "run_first_10_minutes_replay"
    assert "export_manual_host_acceptance_packet.py --host Codex" in pack["run_queue"][0]["packet_command"]
    assert pack["run_queue"][0]["worksheet"]["required_observations"] == [
        "Host shows AlbumentationsX MCP tools and resources.",
        "Host completes run_host_smoke_check.",
        "Host validates the preview request before rendering.",
        "Host renders baseline and candidate previews under artifact root.",
        "Host compares preview runs and exports a pipeline or report.",
    ]
    assert "uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md" in pack[
        "after_run_commands"
    ]


def test_real_host_evidence_execution_pack_markdown_is_actionable() -> None:
    markdown = render_real_host_evidence_execution_pack_markdown(build_real_host_evidence_execution_pack())

    assert markdown.startswith("# Real Host Evidence Execution Pack\n")
    assert "Decision: `hold_v1`" in markdown
    assert "## Non-Fabrication Policy" in markdown
    assert "Record passed only after a real MCP host UI completes the flow." in markdown
    assert "## Execution Queue" in markdown
    assert "| 1 | Codex | `p0` | `run_first_10_minutes_replay` |" in markdown
    assert "## Reviewer Worksheet" in markdown
    assert "Host shows AlbumentationsX MCP tools and resources." in markdown
    assert "## After Each Host Run" in markdown
    assert "export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md" in markdown


def test_committed_real_host_evidence_execution_pack_is_current() -> None:
    pack_path = Path("docs/REAL_HOST_EVIDENCE_EXECUTION.md")

    assert pack_path.read_text(encoding="utf-8") == render_real_host_evidence_execution_pack_markdown(
        build_real_host_evidence_execution_pack()
    )
    assert "[docs/REAL_HOST_EVIDENCE_EXECUTION.md](docs/REAL_HOST_EVIDENCE_EXECUTION.md)" in Path(
        "README.md"
    ).read_text(encoding="utf-8")


def test_real_host_evidence_execution_pack_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "real-host-evidence.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_real_host_evidence_execution_pack.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Real Host Evidence Execution Pack\n")
