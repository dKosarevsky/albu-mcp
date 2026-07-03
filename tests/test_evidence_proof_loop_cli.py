from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_empty_records(tmp_path: Path) -> tuple[Path, Path]:
    host_records = tmp_path / "HOST_MANUAL_RUNS.json"
    beta_records = tmp_path / "BETA_VALIDATION_RECORDS.json"
    host_records.write_text('{"manual_host_ui": [], "first_10_minutes_replay": []}\n', encoding="utf-8")
    beta_records.write_text('{"records": []}\n', encoding="utf-8")
    return host_records, beta_records


def _write_filled_manifest(tmp_path: Path) -> Path:
    manifest = tmp_path / "codex-evidence-session-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_status": "filled",
                "host": "Codex",
                "status": "passed",
                "date": "2026-07-03",
                "reviewer": "Release operator",
                "evidence": "reviewer observed real MCP host UI and first preview replay",
                "artifacts": ["docs/assets/demo/demo_report.md"],
                "commands_used": ["albu-mcp host setup-probe --host Codex --live --format json"],
                "confirm_real_host_observed": True,
                "private_data_included": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def test_evidence_proof_runner_reports_no_write_import_flow(tmp_path: Path) -> None:
    host_records, _ = _write_empty_records(tmp_path)
    manifest = _write_filled_manifest(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "proof-runner",
            "--input",
            str(manifest),
            "--path",
            str(host_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["runner_status"] == "ready_to_import"
    assert payload["writes_records"] is False
    assert payload["host"] == "Codex"
    assert payload["manifest_validation"]["validation_status"] == "ready_to_import"
    assert payload["next_commands"] == [
        f"albu-mcp evidence validate-manifest --input {manifest} --path {host_records} --format json",
        f"albu-mcp evidence import-manifest --input {manifest} --path {host_records} --format json",
        f"albu-mcp evidence close-host --host Codex --path {host_records} --format json",
        (
            "albu-mcp trust gate-transition "
            f"--before-host-records {host_records} --before-beta-records docs/BETA_VALIDATION_RECORDS.json "
            f"--after-host-records {host_records} --after-beta-records docs/BETA_VALIDATION_RECORDS.json "
            "--format markdown"
        ),
    ]
    assert host_records.read_text(encoding="utf-8") == '{"manual_host_ui": [], "first_10_minutes_replay": []}\n'


def test_evidence_proof_status_reports_required_host_gaps(tmp_path: Path) -> None:
    host_records, _ = _write_empty_records(tmp_path)

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "proof-status",
            "--path",
            str(host_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["required_hosts"] == ["Codex", "Claude Code"]
    assert payload["host_count"] == 2
    assert [host["host"] for host in payload["hosts"]] == ["Codex", "Claude Code"]
    assert all(host["closure_status"] == "blocked" for host in payload["hosts"])
    assert all(host["missing_gates"] == ["manual_host_ui", "first_10_minutes_replay"] for host in payload["hosts"])
    assert all(host["next_commands"] for host in payload["hosts"])
    assert payload["next_action"] == "run_proof_runner_for_first_blocked_host"
    assert host_records.read_text(encoding="utf-8") == '{"manual_host_ui": [], "first_10_minutes_replay": []}\n'


def test_evidence_transition_pack_writes_trust_and_rc_artifacts(tmp_path: Path) -> None:
    before_host, beta_records = _write_empty_records(tmp_path)
    after_host = tmp_path / "AFTER_HOST_MANUAL_RUNS.json"
    after_host.write_text(before_host.read_text(encoding="utf-8"), encoding="utf-8")
    output_dir = tmp_path / "transition-pack"

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "transition-pack",
            "--before-host-records",
            str(before_host),
            "--after-host-records",
            str(after_host),
            "--beta-records",
            str(beta_records),
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    expected_files = {
        "trust-transition-pack-index.md",
        "trust-gate-transition.md",
        "rc-go-check-preview.md",
    }
    index = (output_dir / "trust-transition-pack-index.md").read_text(encoding="utf-8")
    transition = (output_dir / "trust-gate-transition.md").read_text(encoding="utf-8")
    rc_preview = (output_dir / "rc-go-check-preview.md").read_text(encoding="utf-8")

    assert result.stdout == f"wrote evidence transition-pack with {len(expected_files)} artifacts to {output_dir}\n"
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert "# Trust Transition Pack" in index
    assert "Writes records: `false`" in index
    assert "albu-mcp trust gate-transition" in index
    assert "albu-mcp rc go-check" in index
    assert "# Trust Gate Transition Report" in transition
    assert "Before trust score" in transition
    assert "After trust score" in transition
    assert "# RC Go Check" in rc_preview
    assert "Go decision: `no_go`" in rc_preview


def test_evidence_rc_unblock_preview_reports_release_blockers(tmp_path: Path) -> None:
    host_records, beta_records = _write_empty_records(tmp_path)
    host_before = host_records.read_text(encoding="utf-8")
    beta_before = beta_records.read_text(encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "rc-unblock-preview",
            "--host-records",
            str(host_records),
            "--beta-records",
            str(beta_records),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["preview_status"] == "blocked"
    assert payload["writes_records"] is False
    assert payload["publish_allowed"] is False
    assert payload["blocked_reasons"] == [
        "p0_host_evidence_missing_or_blocked",
        "beta_validation_incomplete",
    ]
    assert payload["next_unlock_commands"] == [
        "albu-mcp evidence proof-status --format json",
        "albu-mcp beta loop-pack --output-dir docs/beta-loop --format markdown",
        "albu-mcp rc go-check --format markdown",
    ]
    assert payload["release_readiness_command"] == "albu-mcp distribution readiness --format json"
    assert payload["proof_status"]["blocked_host_count"] == 2
    assert payload["rc_go_decision"] == "no_go"
    assert host_records.read_text(encoding="utf-8") == host_before
    assert beta_records.read_text(encoding="utf-8") == beta_before
