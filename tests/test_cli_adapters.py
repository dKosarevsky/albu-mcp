from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from albumentationsx_mcp import cli as legacy_cli
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
from albumentationsx_mcp.adapters.cli.runtime import HOST_SURFACE, build_host_parser, build_server_parser
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
