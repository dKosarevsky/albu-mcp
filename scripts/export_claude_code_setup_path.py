"""Export a Claude Code setup path for unblocking P0 MCP host evidence."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_p0_host_unblock_pack import build_p0_host_unblock_pack

_HOST = "Claude Code"
_FAILURE_CLASS = "claude_cli_missing"


def build_claude_code_setup_path() -> dict[str, Any]:
    """Build the Claude Code setup path from the current P0 unblock state."""
    unblock_pack = build_p0_host_unblock_pack()
    lanes = [lane for lane in unblock_pack["recovery_lanes"] if lane["host"] == _HOST]
    mcp_config = _preview_mcp_config()
    return {
        "setup_status": "blocked_until_claude_cli_visible" if lanes else "ready_for_claude_code_host_run",
        "host": _HOST,
        "failure_class": _FAILURE_CLASS,
        "cli_required": True,
        "rc_reopen_allowed": unblock_pack["rc_reopen_allowed"] and not lanes,
        "summary": {
            "affected_gate_count": len(lanes),
            "blocked_gate_count": sum(lane["evidence_status"] == "blocked" for lane in lanes),
            "setup_check_count": 6,
        },
        "setup_policy": (
            "Do not replay Claude Code P0 gates until the `claude` CLI is visible in the same shell/session that "
            "will own MCP configuration and tool discovery."
        ),
        "mcp_config": mcp_config,
        "setup_checks": [
            "command -v claude",
            "claude --version",
            "uvx --from albumentationsx-mcp albumentationsx-mcp --help",
            f"claude mcp add-json albumentationsx {_shell_json(mcp_config)}",
            "claude mcp get albumentationsx",
            "claude mcp list",
        ],
        "run_order": [
            "Install or expose Claude Code CLI on PATH.",
            "Verify `claude --version` from the same terminal profile used for MCP setup.",
            "Import the AlbumentationsX MCP stdio config with bounded roots.",
            "Restart or refresh Claude Code MCP discovery.",
            "List MCP tools and read albumentationsx://examples/client-smoke.",
            "Call run_host_smoke_check, then run First 10 Minutes only if preview_ready=true.",
        ],
        "affected_gates": [_affected_gate(lane) for lane in lanes],
        "record_commands": {
            "passed": [lane["record_command"] for lane in lanes],
            "blocked": [_blocked_record_command(gate=lane["gate"]) for lane in lanes],
        },
        "acceptance_criteria": [
            "`claude --version` succeeds in the operator shell.",
            "`claude mcp list` shows the AlbumentationsX MCP server.",
            "Claude Code can read albumentationsx://examples/client-smoke.",
            "run_host_smoke_check completes in Claude Code with preview_ready=true.",
            "Affected P0 gates have dated real-host evidence notes or artifacts.",
        ],
        "source_docs": [
            "docs/INSTALL.md",
            "examples/claude_code_preview_command.md",
            "docs/P0_HOST_UNBLOCK_PACK.md",
            "docs/HOST_EVIDENCE_RUNNER.md",
        ],
    }


def render_claude_code_setup_path_markdown(setup: dict[str, Any]) -> str:
    """Render the Claude Code setup path as Markdown."""
    lines = [
        "# Claude Code Setup Path",
        "",
        f"Setup status: `{setup['setup_status']}`",
        f"Host: `{setup['host']}`",
        f"Failure class: `{setup['failure_class']}`",
        f"CLI required: `{str(setup['cli_required']).lower()}`",
        f"RC reopen allowed: `{str(setup['rc_reopen_allowed']).lower()}`",
        "",
        "## Setup Policy",
        "",
        setup["setup_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in setup["summary"].items())
    lines.extend(["", "## MCP Config", "", "```json"])
    lines.append(json.dumps(setup["mcp_config"], indent=2))
    lines.extend(["```", "", "## Setup Checks", ""])
    lines.extend(f"- `{command}`" for command in setup["setup_checks"])
    lines.extend(["", "## Run Order", ""])
    lines.extend(f"{index}. {step}" for index, step in enumerate(setup["run_order"], start=1))
    lines.extend(
        [
            "",
            "## Affected Gates",
            "",
            "| Gate | Evidence Status | Passed Command | Blocked Command |",
            "| --- | --- | --- | --- |",
        ]
    )
    if setup["affected_gates"]:
        lines.extend(
            "| "
            f"`{gate['gate']}` | "
            f"`{gate['evidence_status']}` | "
            f"`{gate['passed_record_command']}` | "
            f"`{gate['blocked_record_command']}` |"
            for gate in setup["affected_gates"]
        )
    else:
        lines.append("| `none` | `recorded` | `none` | `none` |")
    lines.extend(["", "## Acceptance Criteria", ""])
    lines.extend(f"- {item}" for item in setup["acceptance_criteria"])
    lines.extend(["", "## Record Commands", "", "Passed evidence:"])
    lines.extend(f"- `{command}`" for command in setup["record_commands"]["passed"])
    lines.extend(["", "Blocked evidence:"])
    lines.extend(f"- `{command}`" for command in setup["record_commands"]["blocked"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in setup["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for Claude Code setup path exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_claude_code_setup_path_markdown(build_claude_code_setup_path())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _preview_mcp_config() -> dict[str, Any]:
    return {
        "type": "stdio",
        "command": "uvx",
        "args": [
            "--from",
            "albumentationsx-mcp",
            "albumentationsx-mcp",
            "--allowed-root",
            "/absolute/path/to/images",
            "--artifact-root",
            "/absolute/path/to/albu-artifacts",
        ],
    }


def _affected_gate(lane: dict[str, Any]) -> dict[str, str]:
    return {
        "gate": lane["gate"],
        "evidence_status": lane["evidence_status"],
        "passed_record_command": lane["record_command"],
        "blocked_record_command": _blocked_record_command(gate=lane["gate"]),
    }


def _blocked_record_command(*, gate: str) -> str:
    args = [
        "uv",
        "run",
        "python",
        "scripts/record_host_manual_run.py",
    ]
    if gate == "first_10_minutes_replay":
        args.extend(["--kind", "first-10-minutes"])
    args.extend(
        [
            "--host",
            _HOST,
            "--status",
            "blocked",
            "--date",
            "YYYY-MM-DD",
            "--evidence",
            f"Claude Code CLI was not visible or could not start MCP before {gate} could pass.",
        ]
    )
    return " ".join(shlex.quote(arg) for arg in args)


def _shell_json(value: dict[str, Any]) -> str:
    return shlex.quote(json.dumps(value, separators=(",", ":")))


if __name__ == "__main__":
    main()
