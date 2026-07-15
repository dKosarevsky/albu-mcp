from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import tomllib

from scripts.export_host_profile_acceptance_packet import (
    HostProfileAcceptancePacketConfig,
    build_host_profile_acceptance_artifacts,
)

_EXPECTED_ARTIFACTS = {
    "README.md",
    "codex-config.toml",
    "claude-desktop-config.json",
    "profile-matrix-prompt.md",
    "claude-review-loop-prompt.md",
    "receipt-template.json",
}
_PROFILES = ("core", "review", "dataset", "full")


@pytest.fixture
def packet_config(tmp_path: Path) -> HostProfileAcceptancePacketConfig:
    server_python = tmp_path / "venv" / "bin" / "python"
    server_python.parent.mkdir(parents=True)
    server_python.write_text("#!/bin/sh\n", encoding="utf-8")
    server_python.chmod(0o755)
    allowed_root = tmp_path / "inputs"
    allowed_root.mkdir()
    sample_image = allowed_root / "sample-grid.png"
    sample_image.write_bytes(b"packet fixture")
    return HostProfileAcceptancePacketConfig(
        server_python=server_python,
        source_revision="abc123def456",
        allowed_root=allowed_root,
        artifact_root=tmp_path / "artifacts",
        sample_image=sample_image,
        run_date="2026-07-15",
    )


def test_packet_contains_deterministic_profile_configs(
    packet_config: HostProfileAcceptancePacketConfig,
) -> None:
    artifacts = build_host_profile_acceptance_artifacts(packet_config)

    assert set(artifacts) == _EXPECTED_ARTIFACTS
    codex = tomllib.loads(artifacts["codex-config.toml"])["mcp_servers"]
    desktop = json.loads(artifacts["claude-desktop-config.json"])["mcpServers"]
    assert list(codex) == [f"albumentationsx_{profile}" for profile in _PROFILES]
    assert list(desktop) == [f"albumentationsx_{profile}" for profile in _PROFILES]

    for profile in _PROFILES:
        server_name = f"albumentationsx_{profile}"
        expected_args = [
            "-m",
            "albumentationsx_mcp",
            "--allowed-root",
            str(packet_config.allowed_root),
            "--artifact-root",
            str(packet_config.artifact_root / profile),
            "--capability-profile",
            profile,
        ]
        assert codex[server_name]["command"] == str(packet_config.server_python)
        assert codex[server_name]["args"] == expected_args
        assert codex[server_name]["tool_timeout_sec"] == 300
        assert codex[server_name]["tools"] == {
            "get_workflow_example": {"approval_mode": "approve"},
            "run_host_smoke_check": {"approval_mode": "approve"},
        }
        assert "default_tools_approval_mode" not in codex[server_name]
        assert desktop[server_name] == {
            "command": str(packet_config.server_python),
            "args": expected_args,
        }


def test_packet_prompts_cover_profiles_fallback_and_review_loop(
    packet_config: HostProfileAcceptancePacketConfig,
) -> None:
    artifacts = build_host_profile_acceptance_artifacts(packet_config)
    matrix = artifacts["profile-matrix-prompt.md"]
    review = artifacts["claude-review-loop-prompt.md"]
    readme = artifacts["README.md"]

    for profile in _PROFILES:
        assert f"albumentationsx_{profile}" in matrix
    assert "albumentationsx://examples/client-smoke" in matrix
    assert 'get_workflow_example` with `example_id="client-smoke"' in matrix
    assert "run_host_smoke_check" in matrix
    assert str(packet_config.sample_image) in review
    assert "GaussNoise" in review
    assert "too_noisy:high" in review
    assert "record_preview_feedback" in review
    assert "adjust_pipeline" in review
    assert "compare_preview_runs" in review
    assert "Do not accept the candidate until the reviewer has inspected" in review
    assert "not beta or adoption evidence" in readme
    assert "does not mutate host configuration" in readme
    assert "Only the two read-only matrix tools are pre-approved in the Codex config" in readme


def test_receipt_template_is_pending_and_privacy_safe(
    packet_config: HostProfileAcceptancePacketConfig,
) -> None:
    receipt = json.loads(build_host_profile_acceptance_artifacts(packet_config)["receipt-template.json"])

    assert receipt["schema_version"] == 1
    assert receipt["source_revision"] == packet_config.source_revision
    assert receipt["evidence_classification"] == {
        "adoption_evidence": False,
        "host_evidence": "not_observed",
        "machine_proof": "not_run",
        "packet": "template_only",
    }
    assert [host["host"] for host in receipt["hosts"]] == ["Codex", "Claude Desktop"]
    assert all(host["status"] == "pending" for host in receipt["hosts"])
    assert all(profile["status"] == "pending" for host in receipt["hosts"] for profile in host["profiles"])
    assert receipt["hosts"][0]["review_loop_status"] == "not_requested"
    assert receipt["hosts"][1]["review_loop_status"] == "pending"
    assert str(packet_config.allowed_root) not in artifacts_json(receipt)
    assert str(packet_config.artifact_root) not in artifacts_json(receipt)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("relative_python", "server_python must be absolute"),
        ("missing_python", "server_python must be an executable file"),
        ("relative_allowed_root", "allowed_root must be absolute"),
        ("missing_allowed_root", "allowed_root must be an existing directory"),
        ("sample_outside_root", "sample_image must be contained by allowed_root"),
        ("artifact_inside_root", "artifact_root must not be inside allowed_root"),
        ("empty_revision", "source_revision must not be empty"),
        ("invalid_date", "run_date must be an ISO date"),
        ("unsupported_host", "unsupported host"),
    ],
)
def test_packet_rejects_invalid_inputs(
    packet_config: HostProfileAcceptancePacketConfig,
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    config = packet_config
    if mutation == "relative_python":
        config = replace(config, server_python=Path("python"))
    elif mutation == "missing_python":
        config = replace(config, server_python=tmp_path / "missing-python")
    elif mutation == "relative_allowed_root":
        config = replace(config, allowed_root=Path("inputs"))
    elif mutation == "missing_allowed_root":
        config = replace(config, allowed_root=tmp_path / "missing-inputs")
    elif mutation == "sample_outside_root":
        outside = tmp_path / "outside.png"
        outside.write_bytes(b"outside")
        config = replace(config, sample_image=outside)
    elif mutation == "artifact_inside_root":
        config = replace(config, artifact_root=config.allowed_root / "artifacts")
    elif mutation == "empty_revision":
        config = replace(config, source_revision="  ")
    elif mutation == "invalid_date":
        config = replace(config, run_date="15-07-2026")
    elif mutation == "unsupported_host":
        config = replace(config, hosts=("Codex", "Unknown Host"))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match=message):
        build_host_profile_acceptance_artifacts(config)


def test_packet_cli_writes_six_files(
    packet_config: HostProfileAcceptancePacketConfig,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "packet"

    result = subprocess.run(  # noqa: S603 - static script with controlled fixture paths.
        [
            sys.executable,
            "scripts/export_host_profile_acceptance_packet.py",
            "--server-python",
            str(packet_config.server_python),
            "--revision",
            packet_config.source_revision,
            "--allowed-root",
            str(packet_config.allowed_root),
            "--artifact-root",
            str(packet_config.artifact_root),
            "--sample-image",
            str(packet_config.sample_image),
            "--date",
            packet_config.run_date,
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == f"wrote host profile acceptance packet with 6 artifacts to {output_dir}\n"
    assert {path.name for path in output_dir.iterdir()} == _EXPECTED_ARTIFACTS


def artifacts_json(value: object) -> str:
    return json.dumps(value, sort_keys=True)
