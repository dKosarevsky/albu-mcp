from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_activation_command_center_collects_next_operator_packets(tmp_path: Path) -> None:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "activation",
            "command-center",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--release-tag",
            "v1.15.0-rc.1",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["center_status"] == "blocked"
    assert payload["execution_policy"] == "report_only"
    assert payload["p0_hosts"] == ["Codex", "Claude Code"]
    assert payload["trust_dashboard"]["dashboard_status"] == "action_required"
    assert payload["rc_candidate"]["candidate_status"] == "blocked"
    assert [item["host"] for item in payload["p0_evidence_packets"]] == ["Codex", "Claude Code"]
    assert len(payload["beta_intake_wizards"]) == 3
    assert any(command.startswith("albu-mcp evidence packet-bundle") for command in payload["operator_commands"])
    assert any(command.startswith("albu-mcp beta response-validate") for command in payload["operator_commands"])


def test_evidence_packet_bundle_writes_p0_host_packets(tmp_path: Path) -> None:
    evidence_path = tmp_path / "HOST_MANUAL_RUNS.json"
    evidence_path.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    output_dir = tmp_path / "packets"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "packet-bundle",
            "--path",
            str(evidence_path),
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    index_path = output_dir / "p0-evidence-packet-bundle.md"
    codex_packet = output_dir / "codex-evidence-operator-packet.md"
    claude_packet = output_dir / "claude-code-evidence-operator-packet.md"

    assert result.stdout == f"wrote evidence packet-bundle for 2 P0 hosts to {index_path}\n"
    assert "# P0 Evidence Packet Bundle" in index_path.read_text(encoding="utf-8")
    assert "# Codex Evidence Operator Packet" in codex_packet.read_text(encoding="utf-8")
    assert "# Claude Code Evidence Operator Packet" in claude_packet.read_text(encoding="utf-8")
