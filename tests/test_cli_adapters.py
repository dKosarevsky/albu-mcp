from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from albumentationsx_mcp import cli as legacy_cli
from albumentationsx_mcp.adapters.cli import runtime as runtime_adapter
from albumentationsx_mcp.adapters.cli.activation import SURFACE as ACTIVATION_SURFACE
from albumentationsx_mcp.adapters.cli.activation import build_activation_parser, handle_activation_command
from albumentationsx_mcp.adapters.cli.beta import SURFACE as BETA_SURFACE
from albumentationsx_mcp.adapters.cli.beta import build_beta_parser, handle_beta_command
from albumentationsx_mcp.adapters.cli.contracts import (
    CliGroupSurface,
    combine_cli_group_surfaces,
    validate_cli_group_surfaces,
)
from albumentationsx_mcp.adapters.cli.evidence import SURFACE as EVIDENCE_SURFACE
from albumentationsx_mcp.adapters.cli.evidence import build_evidence_parser, handle_evidence_command
from albumentationsx_mcp.adapters.cli.evidence_capture import CAPTURE_COMMANDS
from albumentationsx_mcp.adapters.cli.evidence_guidance import GUIDANCE_COMMANDS
from albumentationsx_mcp.adapters.cli.intake import SURFACE as INTAKE_SURFACE
from albumentationsx_mcp.adapters.cli.intake import build_intake_parser
from albumentationsx_mcp.adapters.cli.preview import SURFACE as PREVIEW_SURFACE
from albumentationsx_mcp.adapters.cli.preview import build_preview_parser
from albumentationsx_mcp.adapters.cli.product_fix import PRODUCT_FIX_COMMANDS
from albumentationsx_mcp.adapters.cli.registration import COMBINED_CLI_SURFACE, GROUP_RUNNERS
from albumentationsx_mcp.adapters.cli.release import (
    DISTRIBUTION_SURFACE,
    RC_SURFACE,
    TRUST_SURFACE,
    build_distribution_parser,
    build_rc_parser,
    build_trust_parser,
    handle_rc_command,
    handle_trust_command,
)
from albumentationsx_mcp.adapters.cli.runtime import HOST_SURFACE, build_host_parser, build_server_parser, run_server
from albumentationsx_mcp.capabilities import CapabilityProfile
from albumentationsx_mcp.server import ServerSettings
from scripts.export_cli_contract import build_parser_contract

_SNAPSHOT_PATH = Path("tests/fixtures/snapshots/cli_contract.json")


def test_combine_cli_group_surfaces_preserves_declared_order() -> None:
    combined = combine_cli_group_surfaces(
        (
            CliGroupSurface(group="host", commands=("setup-probe", "next-action")),
            CliGroupSurface(group="preview", commands=("first-pack",)),
        )
    )

    assert combined.groups == ("host", "preview")
    assert combined.command_paths == (
        "host setup-probe",
        "host next-action",
        "preview first-pack",
    )


def test_cli_group_surface_rejects_empty_group() -> None:
    with pytest.raises(ValueError, match="CLI group name must not be empty"):
        CliGroupSurface(group="")


def test_validate_cli_group_surfaces_rejects_duplicate_group() -> None:
    surfaces = (
        CliGroupSurface(group="preview", commands=("first-pack",)),
        CliGroupSurface(group="preview", commands=("other",)),
    )

    with pytest.raises(ValueError, match="duplicate CLI group: preview"):
        validate_cli_group_surfaces(surfaces)


@pytest.mark.parametrize("command", ["", "first-pack"])
def test_validate_cli_group_surfaces_rejects_invalid_command(command: str) -> None:
    commands = (command,) if not command else (command, command)
    surface = CliGroupSurface(group="preview", commands=commands)

    expected = "empty CLI command" if not command else "duplicate CLI command 'first-pack'"
    with pytest.raises(ValueError, match=expected):
        validate_cli_group_surfaces((surface,))


def test_small_cli_adapter_surfaces_match_expected_ownership() -> None:
    assert CliGroupSurface(group="host", commands=("setup-probe", "next-action")) == HOST_SURFACE
    assert CliGroupSurface(group="preview", commands=("first-pack",)) == PREVIEW_SURFACE
    assert CliGroupSurface(group="intake", commands=("bundle",)) == INTAKE_SURFACE


@pytest.mark.parametrize(
    ("group", "builder"),
    [
        ("host", build_host_parser),
        ("preview", build_preview_parser),
        ("intake", build_intake_parser),
    ],
)
def test_small_cli_adapter_parser_matches_canonical_fragment(
    group: str,
    builder: Callable[[], argparse.ArgumentParser],
) -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert build_parser_contract(builder()) == snapshot["groups"][group]


def test_server_parser_matches_canonical_fragment() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert build_parser_contract(build_server_parser()) == snapshot["server"]


def test_server_parser_accepts_only_declared_capability_profiles(capsys: pytest.CaptureFixture[str]) -> None:
    args = build_server_parser().parse_args(["--capability-profile", "review"])

    assert args.capability_profile == "review"
    with pytest.raises(SystemExit):
        build_server_parser().parse_args(["--capability-profile", "unknown"])
    error = capsys.readouterr().err
    for profile in CapabilityProfile:
        assert profile.value in error


def test_server_cli_profile_override_preserves_environment_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class StubServer:
        def run(self, *, transport: str) -> None:
            captured["transport"] = transport

    monkeypatch.setattr(
        runtime_adapter,
        "settings_from_environment",
        lambda: ServerSettings(
            allowed_roots=[tmp_path / "environment-root"],
            artifact_root=tmp_path / "environment-artifacts",
            max_preview_runs=7,
            capability_profile=CapabilityProfile.CORE,
        ),
    )

    def create_stub(settings: ServerSettings) -> StubServer:
        captured["settings"] = settings
        return StubServer()

    monkeypatch.setattr(runtime_adapter, "create_mcp_server", create_stub)

    run_server(
        [
            "--transport",
            "stdio",
            "--allowed-root",
            str(tmp_path / "cli-root"),
            "--capability-profile",
            "review",
        ]
    )

    settings = captured["settings"]
    assert isinstance(settings, ServerSettings)
    assert settings.allowed_roots == [tmp_path / "cli-root"]
    assert settings.artifact_root == tmp_path / "environment-artifacts"
    assert settings.max_preview_runs == 7
    assert settings.capability_profile is CapabilityProfile.REVIEW
    assert captured["transport"] == "stdio"


def test_activation_adapter_declares_all_cycle_and_product_fix_commands() -> None:
    assert len(ACTIVATION_SURFACE.commands) == 24
    assert len(PRODUCT_FIX_COMMANDS) == 13
    product_fix_commands = tuple(
        command for command in ACTIVATION_SURFACE.commands if command in set(PRODUCT_FIX_COMMANDS)
    )
    assert product_fix_commands == PRODUCT_FIX_COMMANDS


def test_activation_adapter_parser_matches_canonical_fragment() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert build_parser_contract(build_activation_parser()) == snapshot["groups"]["activation"]


@pytest.mark.parametrize(
    "argv",
    [
        ["command-center", "--format", "json"],
        ["first-product-fix", "--host", "Codex", "--format", "json"],
        ["product-fix-implementation-plan", "--host", "Codex", "--format", "json"],
    ],
)
def test_activation_adapter_handler_matches_legacy_dispatch(argv: list[str]) -> None:
    args = build_activation_parser().parse_args(argv)

    assert handle_activation_command(args) == legacy_cli._handle_activation_command(args)


def test_evidence_and_beta_adapters_declare_complete_ownership() -> None:
    assert len(CAPTURE_COMMANDS) == 15
    assert len(GUIDANCE_COMMANDS) == 18
    assert EVIDENCE_SURFACE.commands == CAPTURE_COMMANDS + GUIDANCE_COMMANDS
    assert len(EVIDENCE_SURFACE.commands) == 33
    assert len(BETA_SURFACE.commands) == 12


@pytest.mark.parametrize(
    ("group", "builder"),
    [
        ("evidence", build_evidence_parser),
        ("beta", build_beta_parser),
    ],
)
def test_evidence_and_beta_parser_matches_canonical_fragment(
    group: str,
    builder: Callable[[], argparse.ArgumentParser],
) -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert build_parser_contract(builder()) == snapshot["groups"][group]


@pytest.mark.parametrize(
    ("builder", "handler", "legacy_handler", "argv"),
    [
        (
            build_evidence_parser,
            handle_evidence_command,
            legacy_cli._handle_evidence_command,
            ["doctor", "--format", "json"],
        ),
        (
            build_evidence_parser,
            handle_evidence_command,
            legacy_cli._handle_evidence_command,
            ["preflight", "--format", "json"],
        ),
        (build_beta_parser, handle_beta_command, legacy_cli._handle_beta_command, ["status"]),
        (build_beta_parser, handle_beta_command, legacy_cli._handle_beta_command, ["triage", "--format", "json"]),
    ],
)
def test_evidence_and_beta_handler_matches_legacy_dispatch(
    builder: Callable[[], argparse.ArgumentParser],
    handler: Callable[[argparse.Namespace], str],
    legacy_handler: Callable[[argparse.Namespace], str],
    argv: list[str],
) -> None:
    args = builder().parse_args(argv)

    assert handler(args) == legacy_handler(args)


def test_release_adapter_parsers_match_canonical_fragments() -> None:
    snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    builders = {
        "rc": build_rc_parser,
        "distribution": build_distribution_parser,
        "trust": build_trust_parser,
    }

    assert len(RC_SURFACE.commands) == 6
    assert len(DISTRIBUTION_SURFACE.commands) == 1
    assert len(TRUST_SURFACE.commands) == 4
    for group, builder in builders.items():
        assert build_parser_contract(builder()) == snapshot["groups"][group]


@pytest.mark.parametrize(
    ("builder", "handler", "legacy_handler", "argv"),
    [
        (
            build_rc_parser,
            handle_rc_command,
            legacy_cli._handle_rc_command,
            ["rehearse", "--format", "json"],
        ),
        (
            build_trust_parser,
            handle_trust_command,
            legacy_cli._handle_trust_command,
            ["audit", "--format", "json"],
        ),
    ],
)
def test_release_adapter_handler_matches_legacy_dispatch(
    builder: Callable[[], argparse.ArgumentParser],
    handler: Callable[[argparse.Namespace], str],
    legacy_handler: Callable[[argparse.Namespace], str],
    argv: list[str],
) -> None:
    args = builder().parse_args(argv)

    assert handler(args) == legacy_handler(args)


def test_cli_registry_preserves_complete_stable_dispatch_order() -> None:
    assert COMBINED_CLI_SURFACE.groups == (
        "activation",
        "beta",
        "distribution",
        "evidence",
        "host",
        "intake",
        "preview",
        "rc",
        "trust",
    )
    assert len(COMBINED_CLI_SURFACE.command_paths) == 84
    assert tuple(GROUP_RUNNERS) == COMBINED_CLI_SURFACE.groups


def test_cli_module_is_a_thin_compatibility_facade() -> None:
    source = Path("src/albumentationsx_mcp/cli.py").read_text(encoding="utf-8")

    assert "add_parser(" not in source
    assert "build_" not in source
    assert len(source.splitlines()) <= 120


def test_console_scripts_and_legacy_runner_aliases_remain_stable() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'albumentationsx-mcp = "albumentationsx_mcp.cli:main"' in pyproject
    assert 'albu-mcp = "albumentationsx_mcp.cli:main"' in pyproject
    for name in (
        "_run_server",
        "_run_activation_cli",
        "_run_beta_cli",
        "_run_distribution_cli",
        "_run_evidence_cli",
        "_run_host_cli",
        "_run_intake_cli",
        "_run_preview_cli",
        "_run_rc_cli",
        "_run_trust_cli",
    ):
        assert callable(getattr(legacy_cli, name))
