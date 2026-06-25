from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_host_proof_sprint_checklist import (
    build_host_proof_sprint_checklist,
    render_host_proof_sprint_checklist_markdown,
)


def test_host_proof_sprint_checklist_contains_actionable_host_steps() -> None:
    checklist = build_host_proof_sprint_checklist()
    markdown = render_host_proof_sprint_checklist_markdown(checklist)

    assert checklist["ready_for_v1"] is False
    assert {host["host"] for host in checklist["hosts"]} == {
        "Claude Desktop",
        "Claude Code",
        "Cursor",
        "Codex",
    }
    assert all(host["manual_host_ui"]["status"] == "missing" for host in checklist["hosts"])
    assert all(host["first_10_minutes_replay"]["status"] == "missing" for host in checklist["hosts"])
    assert "scripts/export_manual_host_acceptance_packet.py" in markdown
    assert "scripts/record_host_manual_run.py" in markdown
    assert "scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md" in markdown
    assert "scripts/check_release_readiness.py" in markdown


def test_committed_host_proof_sprint_checklist_is_current() -> None:
    checklist_path = Path("docs/HOST_PROOF_SPRINT_CHECKLIST.md")

    assert checklist_path.read_text(encoding="utf-8") == render_host_proof_sprint_checklist_markdown(
        build_host_proof_sprint_checklist()
    )
    assert "[docs/HOST_PROOF_SPRINT_CHECKLIST.md](docs/HOST_PROOF_SPRINT_CHECKLIST.md)" in Path(
        "README.md"
    ).read_text(encoding="utf-8")
    assert "scripts/export_host_proof_sprint_checklist.py" in Path("docs/HOST_PROOF_SPRINT.md").read_text(
        encoding="utf-8"
    )


def test_host_proof_sprint_checklist_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "host-proof-checklist.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_host_proof_sprint_checklist.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# Host Proof Sprint Checklist\n")
    assert "Claude Desktop" in content
