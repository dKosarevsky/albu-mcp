"""Ordered registration manifest for public CLI command groups."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass

from albumentationsx_mcp.adapters.cli.activation import SURFACE as ACTIVATION_SURFACE
from albumentationsx_mcp.adapters.cli.activation import build_activation_parser, run_activation
from albumentationsx_mcp.adapters.cli.beta import SURFACE as BETA_SURFACE
from albumentationsx_mcp.adapters.cli.beta import build_beta_parser, run_beta
from albumentationsx_mcp.adapters.cli.contracts import (
    CliGroupSurface,
    combine_cli_group_surfaces,
    validate_cli_group_surfaces,
)
from albumentationsx_mcp.adapters.cli.evidence import SURFACE as EVIDENCE_SURFACE
from albumentationsx_mcp.adapters.cli.evidence import build_evidence_parser, run_evidence
from albumentationsx_mcp.adapters.cli.intake import SURFACE as INTAKE_SURFACE
from albumentationsx_mcp.adapters.cli.intake import build_intake_parser, run_intake
from albumentationsx_mcp.adapters.cli.preview import SURFACE as PREVIEW_SURFACE
from albumentationsx_mcp.adapters.cli.preview import build_preview_parser, run_preview
from albumentationsx_mcp.adapters.cli.release import (
    DISTRIBUTION_SURFACE,
    RC_SURFACE,
    TRUST_SURFACE,
    build_distribution_parser,
    build_rc_parser,
    build_trust_parser,
    run_distribution,
    run_rc,
    run_trust,
)
from albumentationsx_mcp.adapters.cli.runtime import HOST_SURFACE, build_host_parser, run_host

CliRunner = Callable[[list[str]], None]
ParserFactory = Callable[[], argparse.ArgumentParser]


@dataclass(frozen=True, slots=True)
class CliGroupAdapter:
    """One declared CLI group with its parser and runner."""

    surface: CliGroupSurface
    build_parser: ParserFactory
    run: CliRunner


CLI_GROUP_ADAPTERS = (
    CliGroupAdapter(ACTIVATION_SURFACE, build_activation_parser, run_activation),
    CliGroupAdapter(BETA_SURFACE, build_beta_parser, run_beta),
    CliGroupAdapter(DISTRIBUTION_SURFACE, build_distribution_parser, run_distribution),
    CliGroupAdapter(EVIDENCE_SURFACE, build_evidence_parser, run_evidence),
    CliGroupAdapter(HOST_SURFACE, build_host_parser, run_host),
    CliGroupAdapter(INTAKE_SURFACE, build_intake_parser, run_intake),
    CliGroupAdapter(PREVIEW_SURFACE, build_preview_parser, run_preview),
    CliGroupAdapter(RC_SURFACE, build_rc_parser, run_rc),
    CliGroupAdapter(TRUST_SURFACE, build_trust_parser, run_trust),
)
CLI_GROUP_SURFACES = tuple(adapter.surface for adapter in CLI_GROUP_ADAPTERS)
validate_cli_group_surfaces(CLI_GROUP_SURFACES)
COMBINED_CLI_SURFACE = combine_cli_group_surfaces(CLI_GROUP_SURFACES)
GROUP_RUNNERS: dict[str, CliRunner] = {adapter.surface.group: adapter.run for adapter in CLI_GROUP_ADAPTERS}
GROUP_PARSER_FACTORIES: dict[str, ParserFactory] = {
    adapter.surface.group: adapter.build_parser for adapter in CLI_GROUP_ADAPTERS
}


def validate_cli_adapter_parsers() -> None:
    """Reject parser registrations that drift from declared command ownership."""
    for adapter in CLI_GROUP_ADAPTERS:
        actual = _direct_commands(adapter.build_parser())
        if actual != adapter.surface.commands:
            message = (
                f"CLI parser commands for {adapter.surface.group!r} do not match its surface: "
                f"expected {adapter.surface.commands!r}, got {actual!r}"
            )
            raise RuntimeError(message)


def _direct_commands(parser: argparse.ArgumentParser) -> tuple[str, ...]:
    subparsers = next(
        (action for action in parser._actions if type(action).__name__ == "_SubParsersAction"),  # noqa: SLF001
        None,
    )
    if subparsers is None or subparsers.choices is None:
        return ()
    return tuple(subparsers.choices)


validate_cli_adapter_parsers()
