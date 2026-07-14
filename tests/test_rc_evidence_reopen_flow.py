from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_rc_evidence_reopen_flow import (
    build_rc_evidence_reopen_flow,
    render_rc_evidence_reopen_flow_markdown,
)


def test_rc_evidence_reopen_flow_keeps_publish_blocked_until_evidence_is_real() -> None:
    flow = build_rc_evidence_reopen_flow()

    assert flow["flow_status"] == "blocked_until_p0_and_beta_evidence"
    assert flow["publish_allowed"] is False
    assert flow["cutover_allowed"] is False
    assert flow["decision"] == "hold_rc"
    assert flow["hard_gate_command"] == "uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json"
    assert flow["gates"] == [
        {"name": "p0_host_evidence", "status": "blocked", "required_before": "rc_tag"},
        {"name": "beta_validation", "status": "missing", "required_before": "rc_tag"},
        {"name": "release_readiness", "status": "ready", "required_before": "rc_tag"},
        {"name": "hard_rc_gate", "status": "blocked", "required_before": "publish"},
    ]


def test_rc_evidence_reopen_flow_markdown_separates_safe_and_blocked_commands() -> None:
    markdown = render_rc_evidence_reopen_flow_markdown(build_rc_evidence_reopen_flow())

    assert markdown.startswith("# RC Evidence Reopen Flow\n")
    assert "Flow status: `blocked_until_p0_and_beta_evidence`" in markdown
    assert "## Safe Commands" in markdown
    assert "## Blocked Publish Commands" in markdown
    assert "`git tag vX.Y.Z-rc.1`" in markdown
    assert "No tag, release, upload, or public announcement is allowed while any evidence gate is blocked." in markdown


def test_committed_rc_evidence_reopen_flow_is_current() -> None:
    doc_path = Path("docs/RC_EVIDENCE_REOPEN_FLOW.md")

    assert doc_path.read_text(encoding="utf-8") == render_rc_evidence_reopen_flow_markdown(
        build_rc_evidence_reopen_flow()
    )
    assert "[RC_EVIDENCE_REOPEN_FLOW.md](RC_EVIDENCE_REOPEN_FLOW.md)" in Path("docs/INDEX.md").read_text(
        encoding="utf-8"
    )


def test_rc_evidence_reopen_flow_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "rc-evidence-flow.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_rc_evidence_reopen_flow.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# RC Evidence Reopen Flow\n")
