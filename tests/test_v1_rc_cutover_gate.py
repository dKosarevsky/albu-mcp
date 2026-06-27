from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.check_v1_rc_cutover_gate import (
    build_v1_rc_cutover_gate,
    render_v1_rc_cutover_gate_markdown,
)


def test_v1_rc_cutover_gate_blocks_release_until_p0_evidence_passes() -> None:
    gate = build_v1_rc_cutover_gate(tag="v1.15.0-rc.1")

    assert gate["gate_status"] == "blocked"
    assert gate["cutover_allowed"] is False
    assert gate["release_tag"] == "v1.15.0-rc.1"
    assert gate["blocked_reason"] == "p0_host_evidence_missing_or_blocked"
    assert gate["p0_summary"]["required_gate_count"] == 4
    assert len(gate["failed_gates"]) == 4
    assert gate["publish_commands"] == []
    assert "git tag v1.15.0-rc.1" in gate["blocked_publish_commands"]


def test_v1_rc_cutover_gate_markdown_is_release_operator_focused() -> None:
    markdown = render_v1_rc_cutover_gate_markdown(build_v1_rc_cutover_gate())

    assert markdown.startswith("# V1 RC Cutover Gate\n")
    assert "Gate status: `blocked`" in markdown
    assert "Cutover allowed: `false`" in markdown
    assert "The RC cutover gate refuses release" in markdown
    assert "| Codex | `first_10_minutes_replay` | `missing` |" in markdown
    assert "## Blocked Publish Commands" in markdown
    assert "`git tag vX.Y.Z-rc.1`" in markdown


def test_v1_rc_cutover_gate_cli_requires_open_gate_for_release() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_v1_rc_cutover_gate.py",
            "--tag",
            "v1.15.0-rc.1",
            "--format",
            "json",
            "--require-open",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["gate_status"] == "blocked"
    assert payload["cutover_allowed"] is False
    assert payload["release_tag"] == "v1.15.0-rc.1"


def test_committed_v1_rc_cutover_gate_is_current() -> None:
    gate_path = Path("docs/V1_RC_CUTOVER_GATE.md")

    assert gate_path.read_text(encoding="utf-8") == render_v1_rc_cutover_gate_markdown(build_v1_rc_cutover_gate())
    assert "[docs/V1_RC_CUTOVER_GATE.md](docs/V1_RC_CUTOVER_GATE.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_v1_rc_cutover_gate_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "v1-rc-cutover-gate.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/check_v1_rc_cutover_gate.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# V1 RC Cutover Gate\n")
