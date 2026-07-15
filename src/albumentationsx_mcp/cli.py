"""Compatibility facade for AlbumentationsX MCP command-line entrypoints."""

from __future__ import annotations

from albumentationsx_mcp.adapters.cli.activation import (
    handle_activation_command as _handle_activation_command,
)
from albumentationsx_mcp.adapters.cli.activation import run_activation as _run_activation_cli
from albumentationsx_mcp.adapters.cli.app import main
from albumentationsx_mcp.adapters.cli.app import run_cli_subcommand as _run_cli_subcommand
from albumentationsx_mcp.adapters.cli.beta import handle_beta_command as _handle_beta_command
from albumentationsx_mcp.adapters.cli.beta import run_beta as _run_beta_cli
from albumentationsx_mcp.adapters.cli.evidence import handle_evidence_command as _handle_evidence_command
from albumentationsx_mcp.adapters.cli.evidence import run_evidence as _run_evidence_cli
from albumentationsx_mcp.adapters.cli.intake import handle_intake_command as _handle_intake_command
from albumentationsx_mcp.adapters.cli.intake import run_intake as _run_intake_cli
from albumentationsx_mcp.adapters.cli.preview import handle_preview_command as _handle_preview_command
from albumentationsx_mcp.adapters.cli.preview import run_preview as _run_preview_cli
from albumentationsx_mcp.adapters.cli.registration import GROUP_RUNNERS
from albumentationsx_mcp.adapters.cli.release import (
    handle_distribution_command as _handle_distribution_command,
)
from albumentationsx_mcp.adapters.cli.release import handle_rc_command as _handle_rc_command
from albumentationsx_mcp.adapters.cli.release import handle_trust_command as _handle_trust_command
from albumentationsx_mcp.adapters.cli.release import run_distribution as _run_distribution_cli
from albumentationsx_mcp.adapters.cli.release import run_rc as _run_rc_cli
from albumentationsx_mcp.adapters.cli.release import run_trust as _run_trust_cli
from albumentationsx_mcp.adapters.cli.runtime import handle_host_command as _handle_host_command
from albumentationsx_mcp.adapters.cli.runtime import run_host as _run_host_cli
from albumentationsx_mcp.adapters.cli.runtime import run_server as _run_server

_SUBCOMMANDS = frozenset(GROUP_RUNNERS)

__all__ = [
    "_handle_activation_command",
    "_handle_beta_command",
    "_handle_distribution_command",
    "_handle_evidence_command",
    "_handle_host_command",
    "_handle_intake_command",
    "_handle_preview_command",
    "_handle_rc_command",
    "_handle_trust_command",
    "_run_activation_cli",
    "_run_beta_cli",
    "_run_cli_subcommand",
    "_run_distribution_cli",
    "_run_evidence_cli",
    "_run_host_cli",
    "_run_intake_cli",
    "_run_preview_cli",
    "_run_rc_cli",
    "_run_server",
    "_run_trust_cli",
    "main",
]


if __name__ == "__main__":
    main()
