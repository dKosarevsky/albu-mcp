from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_v1_rc_release_packet import build_v1_rc_release_packet, render_v1_rc_release_packet_markdown


def test_v1_rc_release_packet_holds_until_p0_evidence_passes() -> None:
    packet = build_v1_rc_release_packet()

    assert packet["rc_decision"] == "hold_rc"
    assert packet["release_candidate_allowed"] is False
    assert packet["required_hosts"] == ["Codex", "Claude Code"]
    assert packet["source_reports"] == ["docs/V1_RC_READINESS.md", "docs/P0_EVIDENCE_STATUS.md"]
    assert "Do not tag v1 RC until P0 real host evidence passes." in packet["blocked_release_steps"]
    assert "uv run python scripts/check_release_readiness.py" in packet["ready_release_steps"]
    assert "uv build" in packet["ready_release_steps"]


def test_v1_rc_release_packet_markdown_is_actionable() -> None:
    markdown = render_v1_rc_release_packet_markdown(build_v1_rc_release_packet())

    assert markdown.startswith("# V1 RC Release Packet\n")
    assert "RC decision: `hold_rc`" in markdown
    assert "Release candidate allowed: `false`" in markdown
    assert "## Blocked Release Steps" in markdown
    assert "Do not tag v1 RC until P0 real host evidence passes." in markdown
    assert "## Ready Release Steps" in markdown
    assert "`uv run python scripts/check_release_readiness.py`" in markdown
    assert "## Source Reports" in markdown
    assert "`docs/P0_EVIDENCE_STATUS.md`" in markdown


def test_committed_v1_rc_release_packet_is_current() -> None:
    packet_path = Path("docs/V1_RC_RELEASE_PACKET.md")

    assert packet_path.read_text(encoding="utf-8") == render_v1_rc_release_packet_markdown(build_v1_rc_release_packet())
    assert "[docs/V1_RC_RELEASE_PACKET.md](docs/V1_RC_RELEASE_PACKET.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_v1_rc_release_packet_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "v1-rc-release-packet.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_v1_rc_release_packet.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Release candidate allowed: `false`" in output_path.read_text(encoding="utf-8")
