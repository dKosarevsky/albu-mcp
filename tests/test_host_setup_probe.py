from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.check_host_setup_probe import build_host_setup_probe, render_host_setup_probe_markdown


def test_host_setup_probe_default_is_deterministic_manual_template() -> None:
    probe = build_host_setup_probe()

    assert probe["probe_status"] == "manual_probe_required"
    assert probe["live"] is False
    assert probe["summary"] == {
        "host_count": 4,
        "check_count": 6,
        "passed_check_count": 2,
        "failed_check_count": 0,
        "not_run_check_count": 4,
    }
    assert [lane["host"] for lane in probe["host_lanes"]] == ["Codex", "Claude Code", "Cursor", "Claude Desktop"]
    claude_lane = next(lane for lane in probe["host_lanes"] if lane["host"] == "Claude Code")
    assert "claude_cli" in claude_lane["required_checks"]


def test_host_setup_probe_live_mode_uses_injected_executable_checker(tmp_path: Path) -> None:
    allowed_root = tmp_path / "images"
    artifact_root = tmp_path / "artifacts"
    allowed_root.mkdir()
    artifact_root.mkdir()

    probe = build_host_setup_probe(
        live=True,
        allowed_root=allowed_root,
        artifact_root=artifact_root,
        executable_checker=lambda command: f"/usr/local/bin/{command}" if command == "uvx" else None,
    )

    assert probe["probe_status"] == "blocked"
    statuses = {check["name"]: check["status"] for check in probe["checks"]}
    assert statuses["uvx"] == "passed"
    assert statuses["claude_cli"] == "failed"
    assert statuses["allowed_root"] == "passed"
    assert statuses["artifact_root"] == "passed"


def test_host_setup_probe_markdown_is_operator_focused() -> None:
    markdown = render_host_setup_probe_markdown(build_host_setup_probe())

    assert markdown.startswith("# Host Setup Probe\n")
    assert "Probe status: `manual_probe_required`" in markdown
    assert "`claude_cli`" in markdown
    assert "examples/claude_code_preview_command.md" in markdown
    assert "uv run python scripts/check_host_setup_probe.py --live --format json" in markdown


def test_committed_host_setup_probe_is_current() -> None:
    probe_path = Path("docs/HOST_SETUP_PROBE.md")

    assert probe_path.read_text(encoding="utf-8") == render_host_setup_probe_markdown(build_host_setup_probe())


def test_host_setup_probe_cli_writes_markdown_and_json(tmp_path: Path) -> None:
    markdown_path = tmp_path / "host-setup-probe.md"
    json_path = tmp_path / "host-setup-probe.json"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/check_host_setup_probe.py", "--output", str(markdown_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/check_host_setup_probe.py", "--format", "json", "--output", str(json_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert markdown_path.read_text(encoding="utf-8").startswith("# Host Setup Probe\n")
    assert json.loads(json_path.read_text(encoding="utf-8"))["probe_status"] == "manual_probe_required"
