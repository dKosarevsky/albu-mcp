from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_rc_dry_run import build_rc_dry_run, render_rc_dry_run_markdown


def test_rc_dry_run_blocks_publish_but_allows_preflight() -> None:
    dry_run = build_rc_dry_run()

    assert dry_run["dry_run_status"] == "preflight_only_blocked_publish"
    assert dry_run["gate_status"] == "blocked"
    assert dry_run["blocked_reason"] == "p0_host_evidence_missing_or_blocked"
    assert dry_run["dry_run_allowed"] is True
    assert dry_run["publish_allowed"] is False
    assert dry_run["rc_cutover_allowed"] is False
    assert dry_run["p0_summary"]["recorded_gate_count"] == 2
    assert dry_run["p0_summary"]["blocked_gate_count"] == 2
    assert "uv build" in dry_run["safe_dry_run_commands"]
    assert "uv run python scripts/check_v1_rc_cutover_gate.py --format json" in dry_run["safe_dry_run_commands"]
    assert "git tag vX.Y.Z-rc.1" in dry_run["blocked_publish_commands"]
    assert dry_run["success_criteria"][1] == "uv build creates local artifacts only; no upload is attempted."


def test_rc_dry_run_markdown_is_release_safe() -> None:
    markdown = render_rc_dry_run_markdown(build_rc_dry_run())

    assert markdown.startswith("# RC Dry Run\n")
    assert "Dry-run status: `preflight_only_blocked_publish`" in markdown
    assert "Publish allowed: `false`" in markdown
    assert "Do not create tags, GitHub Releases, public announcements, or PyPI uploads" in markdown
    assert "`uv run python scripts/check_v1_rc_cutover_gate.py --format json`" in markdown
    assert "`git tag vX.Y.Z-rc.1`" in markdown
    assert "Every P0 host gate has record_status `passed`." in markdown


def test_committed_rc_dry_run_is_current() -> None:
    dry_run_path = Path("docs/RC_DRY_RUN.md")

    assert dry_run_path.read_text(encoding="utf-8") == render_rc_dry_run_markdown(build_rc_dry_run())
    assert "[RC_DRY_RUN.md](RC_DRY_RUN.md)" in Path("docs/ARCHIVE.md").read_text(encoding="utf-8")


def test_rc_dry_run_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "rc-dry-run.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_rc_dry_run.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# RC Dry Run\n")
