from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.check_host_profile_conformance as profile_conformance
from albumentationsx_mcp.adapters.mcp.registration import surface_for_profile
from albumentationsx_mcp.capabilities import CapabilityProfile
from scripts.check_host_profile_conformance import (
    ProfileConformanceConfig,
    _profile_identity_failures,
    build_profile_conformance_report,
    check_profile_conformance,
    profile_conformance_exit_code,
    render_profile_conformance_report,
)

_CURRENT_PROFILE_EVIDENCE = Path("docs/host-evidence/profile-conformance-2026-08-04.json")
_HISTORICAL_PROFILE_EVIDENCE = Path("docs/host-evidence/profile-conformance-2026-07-15.json")


@pytest.fixture
def conformance_config(tmp_path: Path) -> ProfileConformanceConfig:
    allowed_root = tmp_path / "inputs"
    allowed_root.mkdir()
    return ProfileConformanceConfig(
        server_python=Path(sys.executable).absolute(),
        source_root=Path.cwd().resolve(),
        source_revision=_git_stdout(Path.cwd().resolve(), "rev-parse", "HEAD"),
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
    assert result["profile_identity_matches"] is True
    assert result["diagnostics_reported_capability_profile"] == profile.value
    assert result["smoke_ok"] is True
    assert result["reported_capability_profile"] == profile.value
    assert result["preview_ready"] is (profile is not CapabilityProfile.CORE)
    assert result["fallback_matches_resource"] is True
    assert result["failures"] == []


@pytest.mark.parametrize(
    ("diagnostics", "smoke", "expected_failure"),
    [
        ({}, {"capability_profile": "core"}, "diagnose_environment did not report capability profile 'core'"),
        (
            {"capability_profile": "wrong"},
            {"capability_profile": "core"},
            "diagnose_environment did not report capability profile 'core'",
        ),
        ({"capability_profile": "core"}, {}, "run_host_smoke_check did not report capability profile 'core'"),
        (
            {"capability_profile": "core"},
            {"capability_profile": "wrong"},
            "run_host_smoke_check did not report capability profile 'core'",
        ),
    ],
)
def test_profile_identity_rejects_missing_or_wrong_tool_report(
    diagnostics: dict[str, str],
    smoke: dict[str, str],
    expected_failure: str,
) -> None:
    failures = _profile_identity_failures(
        diagnostics=diagnostics,
        smoke=smoke,
        expected=CapabilityProfile.CORE,
    )

    assert failures == [expected_failure]


def test_profile_conformance_report_is_deterministic_and_privacy_safe(
    conformance_config: ProfileConformanceConfig,
) -> None:
    report = asyncio.run(build_profile_conformance_report(conformance_config))
    rendered = render_profile_conformance_report(report)

    assert report["schema_version"] == 3
    assert report["status"] == "passed"
    assert report["source_revision"] == conformance_config.source_revision
    assert report["relevant_tree_sha256"] == profile_conformance.relevant_tree_sha256(
        conformance_config.source_root,
        conformance_config.source_revision,
    )
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
    committed = json.loads(_CURRENT_PROFILE_EVIDENCE.read_text(encoding="utf-8"))
    historical = json.loads(_HISTORICAL_PROFILE_EVIDENCE.read_text(encoding="utf-8"))
    source_root = Path.cwd().resolve()
    profile_conformance.validate_committed_report_provenance(committed, source_root=source_root)
    current_revision = _git_stdout(source_root, "rev-parse", "HEAD")
    allowed_root = Path("docs/assets/demo/inputs").resolve()
    config = ProfileConformanceConfig(
        server_python=Path(sys.executable).absolute(),
        source_root=source_root,
        source_revision=current_revision,
        allowed_root=allowed_root,
        artifact_root=tmp_path / "artifacts",
    )

    current = asyncio.run(build_profile_conformance_report(config))
    assert current["profiles"] == committed["profiles"]
    assert {key: value for key, value in current.items() if key != "source_revision"} == {
        key: value for key, value in committed.items() if key != "source_revision"
    }
    assert committed["profiles"] == historical["profiles"]
    assert committed["status"] == historical["status"]
    assert committed["transport"] == historical["transport"]
    assert committed["evidence_classification"] == historical["evidence_classification"]
    assert current["source_revision"] == current_revision


def test_current_profile_conformance_evidence_is_forced_to_lf_on_checkout() -> None:
    attributes = Path(".gitattributes").read_text(encoding="utf-8").splitlines()
    raw_report = _CURRENT_PROFILE_EVIDENCE.read_bytes()
    report = json.loads(raw_report)

    assert "docs/host-evidence/profile-conformance-2026-08-04.json text eol=lf" in attributes
    assert b"\r" not in raw_report
    assert raw_report == render_profile_conformance_report(report).encode("utf-8")


@pytest.mark.parametrize(
    ("revision", "expected_error"),
    [
        ("not-a-commit", "source_revision must be a full Git commit id"),
        ("f" * 40, "source_revision does not identify a commit in source_root"),
    ],
)
def test_committed_profile_conformance_provenance_rejects_fake_revision(
    revision: str,
    expected_error: str,
) -> None:
    with pytest.raises(ValueError, match=rf"^{expected_error}$") as exc_info:
        profile_conformance.validate_committed_report_provenance(
            {"source_revision": revision},
            source_root=Path.cwd().resolve(),
        )

    assert str(exc_info.value) == expected_error
    assert revision not in str(exc_info.value)


def test_committed_profile_conformance_provenance_rejects_relevant_source_drift(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    _run_git(source_root, "init", "--quiet")
    _run_git(source_root, "config", "user.name", "Profile Conformance Test")
    _run_git(source_root, "config", "user.email", "profile-conformance@example.invalid")
    runtime_source = source_root / "src" / "albumentationsx_mcp" / "runtime.py"
    runtime_source.parent.mkdir(parents=True)
    runtime_source.write_text("STATE = 'before'\n", encoding="utf-8")
    _run_git(source_root, "add", "--", "src/albumentationsx_mcp/runtime.py")
    _run_git(source_root, "commit", "--quiet", "-m", "test: baseline")
    evidence_revision = _git_stdout(source_root, "rev-parse", "HEAD")
    runtime_source.write_text("STATE = 'after'\n", encoding="utf-8")
    _run_git(source_root, "add", "--", "src/albumentationsx_mcp/runtime.py")
    _run_git(source_root, "commit", "--quiet", "-m", "test: relevant drift")

    with pytest.raises(
        ValueError,
        match=r"^profile-conformance-relevant sources changed after evidence revision$",
    ) as exc_info:
        profile_conformance.validate_committed_report_provenance(
            {"source_revision": evidence_revision},
            source_root=source_root,
        )

    assert str(exc_info.value) == "profile-conformance-relevant sources changed after evidence revision"
    assert str(source_root) not in str(exc_info.value)
    assert evidence_revision not in str(exc_info.value)


def test_profile_conformance_provenance_accepts_equivalent_non_ancestor_tree(tmp_path: Path) -> None:
    source_root = _profile_source_repository(tmp_path)
    evidence_revision = _git_stdout(source_root, "rev-parse", "HEAD")
    evidence_digest = profile_conformance.relevant_tree_sha256(source_root, evidence_revision)
    tree = _git_stdout(source_root, "rev-parse", "HEAD^{tree}")
    rewritten_revision = _git_stdout(source_root, "commit-tree", tree, "-m", "test: squash equivalent")
    _run_git(source_root, "checkout", "--quiet", "--detach", rewritten_revision)

    resolved = profile_conformance.validate_committed_report_provenance(
        {
            "schema_version": 3,
            "source_revision": evidence_revision,
            "relevant_tree_sha256": evidence_digest,
        },
        source_root=source_root,
    )

    assert resolved == evidence_revision
    assert (
        _run_git(
            source_root,
            "merge-base",
            "--is-ancestor",
            evidence_revision,
            rewritten_revision,
            check=False,
        ).returncode
        == 1
    )


def test_profile_conformance_provenance_accepts_unavailable_revision_with_matching_tree(tmp_path: Path) -> None:
    source_root = _profile_source_repository(tmp_path)
    current_revision = _git_stdout(source_root, "rev-parse", "HEAD")
    evidence_digest = profile_conformance.relevant_tree_sha256(source_root, current_revision)
    unavailable_revision = "f" * 40

    resolved = profile_conformance.validate_committed_report_provenance(
        {
            "schema_version": 3,
            "source_revision": unavailable_revision,
            "relevant_tree_sha256": evidence_digest,
        },
        source_root=source_root,
    )

    assert resolved == unavailable_revision


@pytest.mark.parametrize("digest", [None, "", "a" * 63, "g" * 64])
def test_profile_conformance_provenance_rejects_malformed_tree_digest(
    tmp_path: Path,
    digest: object,
) -> None:
    source_root = _profile_source_repository(tmp_path)
    revision = _git_stdout(source_root, "rev-parse", "HEAD")

    with pytest.raises(ValueError, match=r"^relevant_tree_sha256 must be a SHA-256 digest$"):
        profile_conformance.validate_committed_report_provenance(
            {
                "schema_version": 3,
                "source_revision": revision,
                "relevant_tree_sha256": digest,
            },
            source_root=source_root,
        )


def test_profile_conformance_provenance_rejects_schema_v3_relevant_source_drift(tmp_path: Path) -> None:
    source_root = _profile_source_repository(tmp_path)
    evidence_revision = _git_stdout(source_root, "rev-parse", "HEAD")
    evidence_digest = profile_conformance.relevant_tree_sha256(source_root, evidence_revision)
    runtime_source = source_root / "src" / "albumentationsx_mcp" / "runtime.py"
    runtime_source.write_text("STATE = 'after'\n", encoding="utf-8")
    _run_git(source_root, "add", "--", "src/albumentationsx_mcp/runtime.py")
    _run_git(source_root, "commit", "--quiet", "-m", "test: relevant drift")

    with pytest.raises(
        ValueError,
        match=r"^profile-conformance-relevant sources changed after evidence revision$",
    ):
        profile_conformance.validate_committed_report_provenance(
            {
                "schema_version": 3,
                "source_revision": evidence_revision,
                "relevant_tree_sha256": evidence_digest,
            },
            source_root=source_root,
        )


def test_profile_conformance_exit_code_rejects_failed_report() -> None:
    assert profile_conformance_exit_code({"status": "failed"}) == 1


def test_profile_conformance_cli_writes_passed_report(
    conformance_config: ProfileConformanceConfig,
    tmp_path: Path,
) -> None:
    output = tmp_path / "profile-conformance.json"
    current_revision = _git_stdout(conformance_config.source_root, "rev-parse", "HEAD")

    result = subprocess.run(  # noqa: S603 - static script with controlled fixture paths.
        [
            sys.executable,
            "scripts/check_host_profile_conformance.py",
            "--server-python",
            str(conformance_config.server_python),
            "--source-root",
            str(conformance_config.source_root),
            "--revision",
            current_revision,
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
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["status"] == "passed"
    assert written["source_revision"] == current_revision


def test_profile_conformance_cli_rejects_revision_that_is_not_head(
    conformance_config: ProfileConformanceConfig,
    tmp_path: Path,
) -> None:
    output = tmp_path / "profile-conformance.json"
    ancestor_revision = _git_stdout(conformance_config.source_root, "rev-parse", "HEAD^")

    result = subprocess.run(  # noqa: S603 - static script with controlled fixture paths.
        [
            sys.executable,
            "scripts/check_host_profile_conformance.py",
            "--server-python",
            str(conformance_config.server_python),
            "--source-root",
            str(conformance_config.source_root),
            "--revision",
            ancestor_revision,
            "--allowed-root",
            str(conformance_config.allowed_root),
            "--artifact-root",
            str(conformance_config.artifact_root),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == "host profile conformance error: source_revision must equal source_root Git HEAD\n"
    assert ancestor_revision not in result.stderr
    assert str(conformance_config.source_root) not in result.stderr
    assert not output.exists()


def _surface_digest(values: tuple[str, ...]) -> str:
    encoded = json.dumps(list(values), ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _run_git(source_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed Git executable with argument-list inputs only.
        ["git", "-C", str(source_root), *args],  # noqa: S607 - test environment Git.
        check=check,
        capture_output=True,
        text=True,
        timeout=5,
    )


def _git_stdout(source_root: Path, *args: str) -> str:
    return _run_git(source_root, *args).stdout.strip()


def _profile_source_repository(tmp_path: Path) -> Path:
    source_root = tmp_path / "source"
    source_root.mkdir()
    _run_git(source_root, "init", "--quiet")
    _run_git(source_root, "config", "user.name", "Profile Conformance Test")
    _run_git(source_root, "config", "user.email", "profile-conformance@example.invalid")
    runtime_source = source_root / "src" / "albumentationsx_mcp" / "runtime.py"
    runtime_source.parent.mkdir(parents=True)
    runtime_source.write_text("STATE = 'before'\n", encoding="utf-8")
    _run_git(source_root, "add", "--", "src/albumentationsx_mcp/runtime.py")
    _run_git(source_root, "commit", "--quiet", "-m", "test: baseline")
    return source_root
