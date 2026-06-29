from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_evidence_operator_packet_writes_host_markdown(tmp_path: Path) -> None:
    evidence_path = tmp_path / "HOST_MANUAL_RUNS.json"
    evidence_path.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    output_dir = tmp_path / "operator-packets"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "operator-packet",
            "--path",
            str(evidence_path),
            "--host",
            "Codex",
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    packet_path = output_dir / "codex-evidence-operator-packet.md"
    packet = packet_path.read_text(encoding="utf-8")

    assert result.stdout == f"wrote evidence operator-packet for Codex to {packet_path}\n"
    assert "# Codex Evidence Operator Packet" in packet
    assert "run_host_smoke_check" in packet
    assert "albu-mcp evidence import-artifacts --host 'Codex'" in packet
    assert "Record passed only after a reviewer observes the real MCP host UI flow" in packet
