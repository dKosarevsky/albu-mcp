"""Export host-specific UX packets for first-run MCP setup."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_adoption_packet import build_adoption_packet
from scripts.validate_host_manual_runs import HOST_NAMES

_ALLOWED_ROOT = "/absolute/path/to/images"
_ARTIFACT_ROOT = "/absolute/path/to/albu-artifacts"
_EXPECTED_TOOLS = [
    "run_host_smoke_check",
    "inspect_dataset_quality",
    "build_review_packet",
    "validate_preview_request",
    "render_preview_batch",
    "compare_preview_runs",
    "interpret_preview_feedback",
    "plan_preview_review",
    "export_preview_report",
    "export_pipeline",
]


def build_host_ux_packets() -> dict[str, Any]:
    """Build deterministic host-specific first-run packets."""
    adoption = build_adoption_packet()
    args = [
        "--from",
        f"{adoption['package']}=={adoption['version']}",
        "albumentationsx-mcp",
        "--allowed-root",
        _ALLOWED_ROOT,
        "--artifact-root",
        _ARTIFACT_ROOT,
    ]
    return {
        "package": adoption["package"],
        "version": adoption["version"],
        "allowed_root": _ALLOWED_ROOT,
        "artifact_root": _ARTIFACT_ROOT,
        "first_run_prompt": _first_run_prompt(),
        "hosts": [_host_packet(host, args) for host in HOST_NAMES],
    }


def render_host_ux_packets_markdown(packets: dict[str, Any]) -> str:
    """Render host UX packets as Markdown."""
    lines = [
        "# Host UX Packets",
        "",
        f"Package: `{packets['package']}=={packets['version']}`",
        f"Allowed root placeholder: `{packets['allowed_root']}`",
        f"Artifact root placeholder: `{packets['artifact_root']}`",
        "",
        "Use these packets as copy-paste host setup guides. Replace placeholders before running.",
        "",
        "## First-Run Prompt",
        "",
        "```text",
        packets["first_run_prompt"],
        "```",
        "",
    ]
    for packet in packets["hosts"]:
        lines.extend(
            [
                f"## {packet['host']}",
                "",
                packet["setup_note"],
                "",
                f"```{packet['config_language']}",
                packet["config_snippet"],
                "```",
                "",
                "Expected tools:",
                "",
                *[f"- `{tool}`" for tool in packet["expected_tools"]],
                "",
                "Troubleshooting:",
                "",
                *[f"- {item}" for item in packet["troubleshooting"]],
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for host UX packet exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_host_ux_packets_markdown(build_host_ux_packets())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _host_packet(host: str, args: list[str]) -> dict[str, Any]:
    return {
        "host": host,
        "config_language": _config_language(host),
        "config_snippet": _config_snippet(host, args),
        "setup_note": _setup_note(host),
        "expected_tools": list(_EXPECTED_TOOLS),
        "troubleshooting": _troubleshooting(host),
    }


def _config_language(host: str) -> str:
    return "toml" if host == "Codex" else "json" if host in {"Claude Desktop", "Cursor"} else "bash"


def _config_snippet(host: str, args: list[str]) -> str:
    if host == "Claude Code":
        payload = json.dumps({"type": "stdio", "command": "uvx", "args": args}, separators=(",", ":"))
        return f"claude mcp add-json albumentationsx {shlex.quote(payload)}"
    if host == "Codex":
        rendered_args = ",\n  ".join(json.dumps(item) for item in args)
        return f'[mcp_servers.albumentationsx]\ncommand = "uvx"\nargs = [\n  {rendered_args},\n]'
    return json.dumps(
        {
            "mcpServers": {
                "albumentationsx": {
                    "command": "uvx",
                    "args": args,
                }
            }
        },
        indent=2,
    )


def _setup_note(host: str) -> str:
    if host == "Claude Desktop":
        return "Edit the Claude Desktop MCP config, then restart Claude Desktop."
    if host == "Claude Code":
        return "Run the command in a shell where Claude Code is authenticated."
    if host == "Cursor":
        return "Edit the Cursor MCP config, then Refresh MCP discovery."
    return "Edit the Codex MCP config, then restart or reload the Codex session."


def _troubleshooting(host: str) -> list[str]:
    return [
        "Run `diagnose_environment` if the host lists tools but preview setup fails.",
        "Check `--allowed-root` when local paths are rejected.",
        "Check `--artifact-root` permissions when preview artifacts are missing.",
        f"Record real host evidence for {host} only after the host UI completes the first-run prompt.",
    ]


def _first_run_prompt() -> str:
    return (
        "Run the AlbumentationsX MCP first-run flow.\n"
        "1. Read albumentationsx://examples/client-smoke.\n"
        "2. Call run_host_smoke_check.\n"
        "3. Call inspect_dataset_quality on the local image folder.\n"
        "4. Call build_review_packet.\n"
        "5. Validate the generated preview request.\n"
        "6. Render a small preview batch.\n"
        "7. Compare baseline and candidate previews.\n"
        "8. Interpret feedback such as 'example 8 is too noisy'.\n"
        "9. Plan the preview review action.\n"
        "10. Export the preview report or final pipeline."
    )


if __name__ == "__main__":
    main()
