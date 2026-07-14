from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_rc_gate_reopen_packet import build_rc_gate_reopen_packet, render_rc_gate_reopen_packet_markdown


def test_rc_gate_reopen_packet_blocks_until_p0_and_beta_evidence() -> None:
    packet = build_rc_gate_reopen_packet()

    assert packet["reopen_status"] == "blocked_until_p0_and_beta_evidence"
    assert packet["cutover_allowed"] is False
    assert packet["publish_allowed"] is False
    assert packet["dry_run_allowed"] is True
    assert packet["rc_decision"] == "hold_rc"
    assert packet["summary"] == {
        "p0_blocked_gate_count": 2,
        "p0_passed_gate_count": 2,
        "beta_record_count": 0,
        "beta_missing_workflow_count": 3,
        "promoted_backlog_item_count": 0,
        "blocked_publish_command_count": 3,
    }
    assert packet["reopen_blockers"] == [
        "p0_host_evidence_blocked",
        "beta_validation_records_missing",
        "p0_host_evidence_missing_or_blocked",
    ]
    assert "git tag vX.Y.Z-rc.1" in packet["blocked_publish_commands"]


def test_rc_gate_reopen_packet_markdown_is_release_safe() -> None:
    markdown = render_rc_gate_reopen_packet_markdown(build_rc_gate_reopen_packet())

    assert markdown.startswith("# RC Gate Reopen Packet\n")
    assert "Reopen status: `blocked_until_p0_and_beta_evidence`" in markdown
    assert "Do not create RC tags, GitHub Releases, PyPI uploads" in markdown
    assert "`p0_host_evidence_blocked`" in markdown
    assert "`beta_validation_records_missing`" in markdown
    assert "`git tag vX.Y.Z-rc.1`" in markdown
    assert "docs/P0_HOST_EVIDENCE_RECOVERY.md" in markdown


def test_committed_rc_gate_reopen_packet_is_current() -> None:
    packet_path = Path("docs/RC_GATE_REOPEN_PACKET.md")

    assert packet_path.read_text(encoding="utf-8") == render_rc_gate_reopen_packet_markdown(
        build_rc_gate_reopen_packet()
    )
    assert "[RC_GATE_REOPEN_PACKET.md](RC_GATE_REOPEN_PACKET.md)" in Path("docs/INDEX.md").read_text(encoding="utf-8")
    assert "docs/RC_GATE_REOPEN_PACKET.md" in Path("docs/V1_READINESS.md").read_text(encoding="utf-8")


def test_rc_gate_reopen_packet_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "rc-gate-reopen-packet.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_rc_gate_reopen_packet.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# RC Gate Reopen Packet\n")
