from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from albumentationsx_mcp.adapters.cli.contracts import (
    CliGroupSurface,
    combine_cli_group_surfaces,
    validate_cli_group_surfaces,
)
from albumentationsx_mcp.adapters.cli.intake import SURFACE as INTAKE_SURFACE
from albumentationsx_mcp.adapters.cli.intake import build_intake_parser
from albumentationsx_mcp.adapters.cli.preview import SURFACE as PREVIEW_SURFACE
from albumentationsx_mcp.adapters.cli.preview import build_preview_parser
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
