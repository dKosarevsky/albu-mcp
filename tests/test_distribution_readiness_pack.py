from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_distribution_readiness_pack import (
    build_distribution_readiness_pack,
    render_distribution_readiness_pack_markdown,
)


def test_distribution_readiness_pack_blocks_until_rc_cutover() -> None:
    pack = build_distribution_readiness_pack()

    assert pack["distribution_status"] == "blocked_until_rc_cutover"
    assert pack["rc_cutover_allowed"] is False
    assert pack["release_tag"] == "vX.Y.Z-rc.1"
    assert pack["publish_commands"] == []
    assert "git tag vX.Y.Z-rc.1" in pack["blocked_publish_commands"]
    assert "uv run python scripts/check_mcp_registry_status.py" in pack["post_rc_checks"]
    assert "uv run python scripts/check_directory_presence.py" in pack["post_rc_checks"]


def test_distribution_readiness_pack_markdown_is_operator_focused() -> None:
    markdown = render_distribution_readiness_pack_markdown(build_distribution_readiness_pack())

    assert markdown.startswith("# Distribution Readiness Pack\n")
    assert "Distribution status: `blocked_until_rc_cutover`" in markdown
    assert "RC cutover allowed: `false`" in markdown
    assert "PyPI package page" in markdown
    assert "MCP Registry server page" in markdown
    assert "AlbumentationsX upstream docs link" in markdown


def test_committed_distribution_readiness_pack_is_current() -> None:
    pack_path = Path("docs/DISTRIBUTION_READINESS_PACK.md")

    assert pack_path.read_text(encoding="utf-8") == render_distribution_readiness_pack_markdown(
        build_distribution_readiness_pack()
    )
    assert "[DISTRIBUTION_READINESS_PACK.md](DISTRIBUTION_READINESS_PACK.md)" in Path("docs/INDEX.md").read_text(
        encoding="utf-8"
    )


def test_distribution_readiness_pack_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "distribution-readiness-pack.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_distribution_readiness_pack.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Distribution Readiness Pack\n")
