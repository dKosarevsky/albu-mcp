from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from albumentationsx_mcp.adapters.mcp.registration import surface_for_profile
from albumentationsx_mcp.capabilities import CapabilityProfile
from scripts.check_host_profile_conformance import (
    ProfileConformanceConfig,
    build_profile_conformance_report,
    check_profile_conformance,
    profile_conformance_exit_code,
    render_profile_conformance_report,
)


@pytest.fixture
def conformance_config(tmp_path: Path) -> ProfileConformanceConfig:
    allowed_root = tmp_path / "inputs"
    allowed_root.mkdir()
    return ProfileConformanceConfig(
        server_python=Path(sys.executable).absolute(),
        source_root=Path.cwd().resolve(),
        source_revision="abc123def456",
        allowed_root=allowed_root,
        artifact_root=tmp_path / "artifacts",
    )


@pytest.mark.parametrize("profile", CapabilityProfile)
def test_profile_conformance_matches_exact_stdio_surface_and_fallback(
    conformance_config: ProfileConformanceConfig,
    profile: CapabilityProfile,
) -> None:
    result = asyncio.run(check_profile_conformance(conformance_config, profile))
    expected = surface_for_profile(profile)

    assert result["profile"] == profile.value
    assert result["status"] == "passed"
    assert result["surface_matches"] is True
    assert result["surface"] == {
        "prompt_count": len(expected.prompts),
        "prompts_sha256": _surface_digest(expected.prompts),
        "resource_count": len(expected.resources),
        "resource_template_count": len(expected.resource_templates),
        "resource_templates_sha256": _surface_digest(expected.resource_templates),
        "resources_sha256": _surface_digest(expected.resources),
        "tool_count": len(expected.tools),
        "tools_sha256": _surface_digest(expected.tools),
    }
    assert result["surface_mismatches"] == {}
    assert result["smoke_ok"] is True
    assert result["reported_capability_profile"] == profile.value
    assert result["preview_ready"] is (profile is not CapabilityProfile.CORE)
    assert result["fallback_matches_resource"] is True
    assert result["failures"] == []


def test_profile_conformance_report_is_deterministic_and_privacy_safe(
    conformance_config: ProfileConformanceConfig,
) -> None:
    report = asyncio.run(build_profile_conformance_report(conformance_config))
    rendered = render_profile_conformance_report(report)

    assert report["schema_version"] == 2
    assert report["status"] == "passed"
    assert report["source_revision"] == conformance_config.source_revision
    assert report["transport"] == "stdio"
    assert report["evidence_classification"] == "machine_proof_only"
    assert [item["profile"] for item in report["profiles"]] == [profile.value for profile in CapabilityProfile]
    assert profile_conformance_exit_code(report) == 0
    assert rendered == json.dumps(report, indent=2, sort_keys=True) + "\n"
    assert str(conformance_config.allowed_root) not in rendered
    assert str(conformance_config.artifact_root) not in rendered
    assert str(conformance_config.server_python) not in rendered
    assert str(conformance_config.source_root) not in rendered


def test_committed_profile_conformance_report_matches_current_contract(tmp_path: Path) -> None:
    report_path = Path("docs/host-evidence/profile-conformance-2026-07-15.json")
    committed = json.loads(report_path.read_text(encoding="utf-8"))
    allowed_root = Path("docs/assets/demo/inputs").resolve()
    config = ProfileConformanceConfig(
        server_python=Path(sys.executable).absolute(),
        source_root=Path.cwd().resolve(),
        source_revision=committed["source_revision"],
        allowed_root=allowed_root,
        artifact_root=tmp_path / "artifacts",
    )

    assert asyncio.run(build_profile_conformance_report(config)) == committed


def test_profile_conformance_exit_code_rejects_failed_report() -> None:
    assert profile_conformance_exit_code({"status": "failed"}) == 1


def test_profile_conformance_cli_writes_passed_report(
    conformance_config: ProfileConformanceConfig,
    tmp_path: Path,
) -> None:
    output = tmp_path / "profile-conformance.json"

    result = subprocess.run(  # noqa: S603 - static script with controlled fixture paths.
        [
            sys.executable,
            "scripts/check_host_profile_conformance.py",
            "--server-python",
            str(conformance_config.server_python),
            "--source-root",
            str(conformance_config.source_root),
            "--revision",
            conformance_config.source_revision,
            "--allowed-root",
            str(conformance_config.allowed_root),
            "--artifact-root",
            str(conformance_config.artifact_root),
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == f"host profile conformance passed; wrote report to {output}\n"
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "passed"


def _surface_digest(values: tuple[str, ...]) -> str:
    encoded = json.dumps(list(values), ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
