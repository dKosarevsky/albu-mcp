from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_p0_evidence_regeneration_pack import (
    build_p0_evidence_regeneration_pack,
    render_p0_evidence_regeneration_pack_markdown,
)


def test_p0_evidence_regeneration_pack_blocks_until_p0_evidence_passes() -> None:
    pack = build_p0_evidence_regeneration_pack()

    assert pack["pack_status"] == "blocked_until_p0_evidence"
    assert pack["rc_regeneration_allowed"] is False
    assert pack["summary"]["required_gate_count"] == 4
    assert pack["summary"]["missing_gate_count"] == 0
    assert pack["summary"]["blocked_gate_count"] == 4
    assert pack["blocked_reason"] == "p0_host_evidence_missing_or_blocked"
    assert "uv run python scripts/verify_host_evidence_import.py" in pack["safe_anytime_commands"]
    assert (
        "uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md"
        in pack["gated_regeneration_commands"]
    )


def test_p0_evidence_regeneration_pack_markdown_is_operator_readable() -> None:
    markdown = render_p0_evidence_regeneration_pack_markdown(build_p0_evidence_regeneration_pack())

    assert markdown.startswith("# P0 Evidence Regeneration Pack\n")
    assert "Pack status: `blocked_until_p0_evidence`" in markdown
    assert "RC regeneration allowed: `false`" in markdown
    assert "Do not treat generated RC artifacts as release-ready" in markdown
    assert "| Codex | `first_10_minutes_replay` | `blocked` |" in markdown
    assert (
        "uv run python scripts/export_v1_growth_cutover_report.py --output docs/V1_GROWTH_CUTOVER_REPORT.md" in markdown
    )


def test_committed_p0_evidence_regeneration_pack_is_current() -> None:
    pack_path = Path("docs/P0_EVIDENCE_REGENERATION_PACK.md")

    assert pack_path.read_text(encoding="utf-8") == render_p0_evidence_regeneration_pack_markdown(
        build_p0_evidence_regeneration_pack()
    )
    assert "[docs/P0_EVIDENCE_REGENERATION_PACK.md](docs/P0_EVIDENCE_REGENERATION_PACK.md)" in Path(
        "README.md"
    ).read_text(encoding="utf-8")


def test_p0_evidence_regeneration_pack_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "p0-evidence-regeneration-pack.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_p0_evidence_regeneration_pack.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# P0 Evidence Regeneration Pack\n")
