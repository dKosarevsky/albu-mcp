from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_rc_host_evidence_ops import (
    build_rc_host_evidence_ops,
    render_rc_host_evidence_ops_markdown,
)


def test_rc_host_evidence_ops_stays_blocked_until_real_host_runs() -> None:
    ops = build_rc_host_evidence_ops()

    assert ops["ops_status"] == "blocked_until_real_host_runs"
    assert ops["required_hosts"] == ["Codex", "Claude Code"]
    assert ops["rc_cutover_allowed"] is False
    assert ops["p0_summary"]["required_gate_count"] == 4
    assert ops["p0_summary"]["missing_gate_count"] == 0
    assert ops["p0_summary"]["blocked_gate_count"] == 4
    assert "uv run python scripts/check_p0_host_run_preflight.py" in ops["run_commands"]
    assert (
        "uv run python scripts/verify_host_evidence_import.py --input /path/to/host-evidence-candidate.json"
        in ops["run_commands"]
    )
    assert "uv run python scripts/check_v1_rc_cutover_gate.py --require-open" in ops["rc_gate_commands"]


def test_rc_host_evidence_ops_markdown_is_operator_focused() -> None:
    markdown = render_rc_host_evidence_ops_markdown(build_rc_host_evidence_ops())

    assert markdown.startswith("# RC Host Evidence Ops\n")
    assert "Ops status: `blocked_until_real_host_runs`" in markdown
    assert "Do not record passed evidence without a real host UI run." in markdown
    assert "| Codex | `first_10_minutes_replay` | `blocked` |" in markdown
    assert "`uv run python scripts/check_v1_rc_cutover_gate.py --require-open`" in markdown


def test_committed_rc_host_evidence_ops_is_current() -> None:
    ops_path = Path("docs/RC_HOST_EVIDENCE_OPS.md")

    assert ops_path.read_text(encoding="utf-8") == render_rc_host_evidence_ops_markdown(build_rc_host_evidence_ops())
    assert "[docs/RC_HOST_EVIDENCE_OPS.md](docs/RC_HOST_EVIDENCE_OPS.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_rc_host_evidence_ops_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "rc-host-evidence-ops.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_rc_host_evidence_ops.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# RC Host Evidence Ops\n")
