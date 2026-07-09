from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_evidence_execution_pack_writes_no_record_session_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "evidence-execution"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack",
            "--date",
            "2026-07-09",
            "--reviewer",
            "Release operator",
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == f"wrote evidence execution-pack with 9 artifacts to {output_dir}\n"
    assert (output_dir / "README.md").exists()
    assert (output_dir / "session-plan.md").exists()
    assert (output_dir / "operator-checklist.md").exists()
    assert (output_dir / "post-session-commands.md").exists()
    assert (output_dir / "codex-evidence-session-manifest.json").exists()
    assert (output_dir / "claude-code-evidence-session-manifest.json").exists()
    assert (output_dir / "beta-responses/dataset-health-before-training-beta-response.json").exists()
    assert (output_dir / "beta-responses/noisy-preview-tuning-beta-response.json").exists()
    assert (output_dir / "beta-responses/robustness-distortion-variants-beta-response.json").exists()

    readme = (output_dir / "README.md").read_text(encoding="utf-8")
    commands = (output_dir / "post-session-commands.md").read_text(encoding="utf-8")
    codex_manifest = json.loads((output_dir / "codex-evidence-session-manifest.json").read_text(encoding="utf-8"))
    beta_response = json.loads(
        (output_dir / "beta-responses/noisy-preview-tuning-beta-response.json").read_text(encoding="utf-8")
    )

    assert "Generated execution packs are not evidence" in readme
    assert "writes_records: `false`" in readme
    assert codex_manifest["manifest_status"] == "template"
    assert codex_manifest["confirm_real_host_observed"] is False
    assert codex_manifest["private_data_included"] is False
    assert "replace with" in beta_response["summary"]
    assert beta_response["private_data_included"] is False
    assert "albu-mcp evidence preflight" in commands
    assert "albu-mcp evidence import-wizard" in commands
    assert "--import-ready" in commands
    assert str(output_dir / "codex-evidence-session-manifest.json") in commands
    assert str(output_dir / "claude-code-evidence-session-manifest.json") in commands
    assert str(output_dir / "beta-responses") in commands


def test_evidence_execution_pack_can_target_one_host(tmp_path: Path) -> None:
    output_dir = tmp_path / "claude-pack"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "execution-pack",
            "--host",
            "Claude Code",
            "--date",
            "2026-07-09",
            "--reviewer",
            "Release operator",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == f"wrote evidence execution-pack with 8 artifacts to {output_dir}\n"
    assert (output_dir / "claude-code-evidence-session-manifest.json").exists()
    assert not (output_dir / "codex-evidence-session-manifest.json").exists()

    session_plan = (output_dir / "session-plan.md").read_text(encoding="utf-8")
    assert "Claude Code" in session_plan
    assert "Codex" not in session_plan
