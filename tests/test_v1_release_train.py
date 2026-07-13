from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_v1_release_train import build_v1_release_train, render_v1_release_train_markdown


def test_v1_release_train_blocks_until_trust_gates_pass() -> None:
    train = build_v1_release_train()
    markdown = render_v1_release_train_markdown(train)

    assert train["package"] == "albumentationsx-mcp"
    assert train["current_version"] == "1.17.1"
    assert train["release_allowed"] is False
    assert train["manual_gate_count"] == 5
    assert "Do not publish a stable v1 release" in markdown
    assert "uv run python scripts/export_v1_trust_gates.py --output docs/V1_TRUST_GATES.md" in markdown
    assert "uv build" in markdown
    assert "gh release create" in markdown


def test_committed_v1_release_train_is_current() -> None:
    train_path = Path("docs/V1_RELEASE_TRAIN.md")

    assert train_path.read_text(encoding="utf-8") == render_v1_release_train_markdown(build_v1_release_train())
    assert "docs/V1_RELEASE_TRAIN.md" in Path("docs/RELEASE.md").read_text(encoding="utf-8")


def test_v1_release_train_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "v1-release-train.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_v1_release_train.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# V1 Release Train\n")
