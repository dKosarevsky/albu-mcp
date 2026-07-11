from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_v1_evidence_operator_packet import (
    build_v1_evidence_operator_packet,
    render_v1_evidence_operator_packet_markdown,
)


def test_v1_evidence_operator_packet_blocks_rc_without_real_host_evidence() -> None:
    packet = build_v1_evidence_operator_packet()

    assert packet["packet_status"] == "manual_evidence_required"
    assert packet["rc_publish_allowed"] is False
    assert packet["required_hosts"] == ["Codex", "Claude Code"]
    assert packet["summary"]["missing_gate_count"] == 0
    assert packet["summary"]["recorded_gate_count"] == 2
    assert packet["summary"]["blocked_gate_count"] == 2
    assert packet["operator_policy"] == "Do not create an RC tag until all P0 host gates are passed in real host UI."
    assert [lane["host"] for lane in packet["operator_lanes"]] == ["Codex", "Claude Code"]
    assert all("run_host_smoke_check" in lane["host_prompt"] for lane in packet["operator_lanes"])
    assert all(
        "scripts/record_host_manual_run.py" in command
        for lane in packet["operator_lanes"]
        for command in lane["record_commands"]
    )


def test_v1_evidence_operator_packet_markdown_is_actionable() -> None:
    markdown = render_v1_evidence_operator_packet_markdown(build_v1_evidence_operator_packet())

    assert markdown.startswith("# V1 Evidence Operator Packet\n")
    assert "Packet status: `manual_evidence_required`" in markdown
    assert "RC publish allowed: `false`" in markdown
    assert "Do not create an RC tag until all P0 host gates are passed in real host UI." in markdown
    assert "## Codex" in markdown
    assert "## Claude Code" in markdown
    assert "run_host_smoke_check" in markdown
    assert "scripts/record_host_manual_run.py" in markdown


def test_committed_v1_evidence_operator_packet_is_current() -> None:
    packet_path = Path("docs/V1_EVIDENCE_OPERATOR_PACKET.md")

    assert packet_path.read_text(encoding="utf-8") == render_v1_evidence_operator_packet_markdown(
        build_v1_evidence_operator_packet()
    )
    assert "[docs/V1_EVIDENCE_OPERATOR_PACKET.md](docs/V1_EVIDENCE_OPERATOR_PACKET.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_v1_evidence_operator_packet_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "v1-evidence-operator-packet.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_v1_evidence_operator_packet.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# V1 Evidence Operator Packet\n")
