from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_p0_host_evidence_ledger import (
    build_p0_host_evidence_ledger,
    render_p0_host_evidence_ledger_markdown,
)


def test_p0_host_evidence_ledger_tracks_required_gates_without_claiming_evidence() -> None:
    ledger = build_p0_host_evidence_ledger()

    assert ledger["ledger_status"] == "manual_evidence_required"
    assert ledger["target_hosts"] == ["Codex", "Claude Code"]
    assert ledger["non_fabrication_policy"] == "Only docs/HOST_MANUAL_RUNS.json can satisfy a P0 gate."
    assert ledger["summary"] == {
        "required_gate_count": 4,
        "recorded_gate_count": 2,
        "missing_gate_count": 0,
        "blocked_gate_count": 2,
    }
    assert [gate["gate"] for gate in ledger["host_gates"][0]["gates"]] == [
        "first_10_minutes_replay",
        "manual_host_ui",
    ]
    statuses_by_host = {
        host["host"]: {gate["record_status"] for gate in host["gates"]} for host in ledger["host_gates"]
    }
    assert statuses_by_host == {"Codex": {"passed"}, "Claude Code": {"blocked"}}


def test_p0_host_evidence_ledger_markdown_is_operator_readable() -> None:
    markdown = render_p0_host_evidence_ledger_markdown(build_p0_host_evidence_ledger())

    assert markdown.startswith("# P0 Host Evidence Ledger\n")
    assert "Ledger status: `manual_evidence_required`" in markdown
    assert "Only docs/HOST_MANUAL_RUNS.json can satisfy a P0 gate." in markdown
    assert "| Codex | `first_10_minutes_replay` | `passed` |" in markdown
    assert "| Claude Code | `manual_host_ui` | `blocked` |" in markdown
    assert "uv run python scripts/record_host_manual_run.py" in markdown


def test_committed_p0_host_evidence_ledger_is_current() -> None:
    ledger_path = Path("docs/P0_HOST_EVIDENCE_LEDGER.md")

    assert ledger_path.read_text(encoding="utf-8") == render_p0_host_evidence_ledger_markdown(
        build_p0_host_evidence_ledger()
    )
    assert "[docs/P0_HOST_EVIDENCE_LEDGER.md](docs/P0_HOST_EVIDENCE_LEDGER.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_p0_host_evidence_ledger_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "p0-host-evidence-ledger.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_p0_host_evidence_ledger.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# P0 Host Evidence Ledger\n")
