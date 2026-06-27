from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_v1_rc_automation_pack import build_v1_rc_automation_pack, render_v1_rc_automation_pack_markdown


def test_v1_rc_automation_pack_is_blocked_until_cutover_is_ready() -> None:
    pack = build_v1_rc_automation_pack()

    assert pack["automation_status"] == "blocked"
    assert pack["rc_decision"] == "hold_rc"
    assert pack["release_candidate_allowed"] is False
    assert "Do not run publish commands while automation_status is blocked." in pack["operator_warnings"]
    assert "uv run python scripts/check_release_readiness.py" in pack["preflight_commands"]
    assert "git tag vX.Y.Z-rc.1" in pack["publish_commands"]


def test_v1_rc_automation_pack_markdown_is_copyable() -> None:
    markdown = render_v1_rc_automation_pack_markdown(build_v1_rc_automation_pack())

    assert markdown.startswith("# V1 RC Automation Pack\n")
    assert "Automation status: `blocked`" in markdown
    assert "Release candidate allowed: `false`" in markdown
    assert "## Operator Warnings" in markdown
    assert "Do not run publish commands while automation_status is blocked." in markdown
    assert "## Preflight Commands" in markdown
    assert "`uv run python scripts/check_release_readiness.py`" in markdown
    assert "## Publish Commands" in markdown
    assert "`git tag vX.Y.Z-rc.1`" in markdown


def test_committed_v1_rc_automation_pack_is_current() -> None:
    pack_path = Path("docs/V1_RC_AUTOMATION_PACK.md")

    assert pack_path.read_text(encoding="utf-8") == render_v1_rc_automation_pack_markdown(build_v1_rc_automation_pack())
    assert "[docs/V1_RC_AUTOMATION_PACK.md](docs/V1_RC_AUTOMATION_PACK.md)" in Path("README.md").read_text(
        encoding="utf-8"
    )


def test_v1_rc_automation_pack_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "v1-rc-automation-pack.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_v1_rc_automation_pack.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# V1 RC Automation Pack\n")
