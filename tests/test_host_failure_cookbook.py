from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_host_failure_cookbook import build_host_failure_cookbook, render_host_failure_cookbook_markdown


def test_host_failure_cookbook_covers_core_host_failures() -> None:
    cookbook = build_host_failure_cookbook()

    assert [item["code"] for item in cookbook["failure_cases"]] == [
        "tools_not_visible",
        "stale_tool_cache",
        "path_policy_rejected",
        "artifact_root_unwritable",
        "uvx_startup_failed",
    ]
    assert all(item["first_check"] for item in cookbook["failure_cases"])
    assert all(item["record_status"] == "blocked" for item in cookbook["failure_cases"])
    assert any(
        "uv run python scripts/export_manual_host_acceptance_packet.py" in command
        for command in cookbook["triage_commands"]
    )
    assert any(
        command == "uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md"
        for command in cookbook["triage_commands"]
    )


def test_host_failure_cookbook_markdown_is_actionable() -> None:
    markdown = render_host_failure_cookbook_markdown(build_host_failure_cookbook())

    assert markdown.startswith("# Host Failure Cookbook\n")
    assert "## Failure Cases" in markdown
    assert "### tools_not_visible" in markdown
    assert "Ask the host to read `albumentationsx://examples/client-smoke`" in markdown
    assert "### stale_tool_cache" in markdown
    assert "Restart the host and clear client-side MCP server discovery cache" in markdown
    assert "### path_policy_rejected" in markdown
    assert "Restart the server with an existing absolute `--allowed-root`" in markdown
    assert "### artifact_root_unwritable" in markdown
    assert "Restart with a writable absolute `--artifact-root`" in markdown
    assert "### uvx_startup_failed" in markdown
    assert "Run the exact `uvx` command in a terminal" in markdown
    assert "## Record Blocked Evidence" in markdown


def test_committed_host_failure_cookbook_is_current() -> None:
    cookbook_path = Path("docs/HOST_FAILURE_COOKBOOK.md")

    assert cookbook_path.read_text(encoding="utf-8") == render_host_failure_cookbook_markdown(
        build_host_failure_cookbook()
    )
    assert "[HOST_FAILURE_COOKBOOK.md](HOST_FAILURE_COOKBOOK.md)" in Path("docs/INDEX.md").read_text(encoding="utf-8")


def test_host_failure_cookbook_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "host-failure-cookbook.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_host_failure_cookbook.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Host Failure Cookbook\n")
