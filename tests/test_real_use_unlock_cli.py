from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_host_setup_probe_cli_reports_one_host_operator_path(tmp_path: Path) -> None:
    allowed_root = tmp_path / "images"
    artifact_root = tmp_path / "artifacts"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "host",
            "setup-probe",
            "--host",
            "Codex",
            "--allowed-root",
            str(allowed_root),
            "--artifact-root",
            str(artifact_root),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["probe_status"] == "manual_probe_required"
    assert payload["writes_records"] is False
    assert payload["summary"]["host_count"] == 1
    assert payload["host_lanes"][0]["host"] == "Codex"
    assert payload["host_lanes"][0]["operator_command"].startswith(
        "uvx --from albumentationsx-mcp albumentationsx-mcp"
    )
    assert "claude_cli" not in payload["host_lanes"][0]["blocking_checks"]
    assert payload["next_action"] == "run_live_probe"
