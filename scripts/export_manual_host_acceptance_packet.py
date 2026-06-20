"""Export a local manual MCP host acceptance packet."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_host_manual_runs import HOST_NAMES, HostName

_DEFAULT_ALLOWED_ROOT = Path("docs/assets/demo/inputs")
_DEFAULT_ARTIFACT_ROOT = Path(tempfile.gettempdir()) / "albu-mcp-host-acceptance-artifacts"
_PROJECT_VERSION_PATTERN = re.compile(r'(?m)^version\s*=\s*"([^"]+)"\s*$')


@dataclass(frozen=True)
class ManualHostAcceptancePacketConfig:
    """Inputs used to render one local manual host acceptance packet."""

    allowed_root: Path
    artifact_root: Path
    sample_image: Path
    package_version: str
    run_date: str


def build_manual_host_acceptance_packet(config: ManualHostAcceptancePacketConfig) -> str:
    """Return Markdown instructions for one manual host acceptance run."""
    args = _server_args(config)
    return "\n".join(
        [
            "# Manual Host Acceptance Packet",
            "",
            "Use this local packet to run real MCP host UI checks without changing committed evidence prematurely.",
            "",
            "## Local Inputs",
            "",
            f"- Package: `albumentationsx-mcp=={config.package_version}`",
            f"- Allowed root: `{config.allowed_root}`",
            f"- Artifact root: `{config.artifact_root}`",
            f"- Sample image: `{config.sample_image}`",
            f"- Run date: `{config.run_date}`",
            "",
            "## Claude Desktop",
            "",
            "```json",
            _desktop_json(args),
            "```",
            "",
            "Restart Claude Desktop after editing the MCP config, then run the prompt below.",
            "",
            "## Claude Code",
            "",
            "```bash",
            _claude_code_command(args),
            "```",
            "",
            "## Cursor",
            "",
            "```json",
            _desktop_json(args),
            "```",
            "",
            "Refresh MCP discovery after editing the Cursor MCP config, then run the prompt below.",
            "",
            "## Codex",
            "",
            "```toml",
            _codex_toml(args),
            "```",
            "",
            "Restart or reload the Codex MCP server config, then run the prompt below.",
            "",
            "## Copyable Host Prompt",
            "",
            "```text",
            _host_prompt(config),
            "```",
            "",
            "## Record Evidence",
            "",
            "Only record `passed` after the host UI actually completed the flow. If a host cannot be tested, keep it",
            "`pending` or record `blocked` with the concrete blocker.",
            "",
            *(_record_command(host, config.run_date) for host in HOST_NAMES),
            "",
            "After recording all completed hosts:",
            "",
            "```bash",
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md",
            "uv run python scripts/check_host_acceptance_report.py",
            "uv run python scripts/check_manual_host_acceptance.py",
            "```",
            "",
        ]
    )


def main() -> None:
    """CLI entrypoint for reviewers preparing host UI acceptance evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allowed-root", type=Path, default=_DEFAULT_ALLOWED_ROOT)
    parser.add_argument("--artifact-root", type=Path, default=_DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--sample-image", type=Path)
    parser.add_argument("--date", default=_today(), help="ISO date for record commands.")
    parser.add_argument("--package-version", default=_read_project_version(Path("pyproject.toml")))
    parser.add_argument("--output", type=Path, help="Write Markdown to this path instead of stdout.")
    args = parser.parse_args()

    allowed_root = args.allowed_root.resolve()
    sample_image = (args.sample_image or (allowed_root / "sample-grid.png")).resolve()
    config = ManualHostAcceptancePacketConfig(
        allowed_root=allowed_root,
        artifact_root=args.artifact_root.resolve(),
        sample_image=sample_image,
        package_version=args.package_version,
        run_date=args.date,
    )
    packet = build_manual_host_acceptance_packet(config)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(packet, encoding="utf-8")
        sys.stdout.write(f"wrote manual host acceptance packet: {args.output}\n")
        return
    sys.stdout.write(packet)


def _server_args(config: ManualHostAcceptancePacketConfig) -> list[str]:
    return [
        "--from",
        f"albumentationsx-mcp=={config.package_version}",
        "albumentationsx-mcp",
        "--allowed-root",
        str(config.allowed_root),
        "--artifact-root",
        str(config.artifact_root),
    ]


def _desktop_json(args: list[str]) -> str:
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


def _claude_code_command(args: list[str]) -> str:
    payload = json.dumps({"type": "stdio", "command": "uvx", "args": args}, separators=(",", ":"))
    return f"claude mcp add-json albumentationsx {shlex.quote(payload)}"


def _codex_toml(args: list[str]) -> str:
    rendered_args = ",\n  ".join(json.dumps(item) for item in args)
    return f'[mcp_servers.albumentationsx]\ncommand = "uvx"\nargs = [\n  {rendered_args},\n]'


def _host_prompt(config: ManualHostAcceptancePacketConfig) -> str:
    return f"""Run AlbumentationsX MCP manual acceptance for this host.

Use this exact sample image:
{config.sample_image}

Acceptance flow:
1. List the available albumentationsx MCP tools and resources.
2. Read albumentationsx://capabilities.
3. Read albumentationsx://examples/distortion-review.
4. Call run_host_smoke_check.
5. Call validate_preview_request for the sample image.
6. If validation is valid, call render_preview_batch.
7. Call adjust_pipeline to reduce excessive noise, then render a candidate preview.
8. Call compare_preview_runs for baseline vs candidate.
9. Call start_tuning_session, record_tuning_session_step, close_tuning_session, and export_tuning_session.
10. Call export_pipeline.

Finish with:
Host: <host name>
Status: passed or blocked
Evidence: <one sentence mentioning listed tools/resources, smoke check, preview render, compare, tuning export,
and any blocker>"""


def _record_command(host: HostName, run_date: str) -> str:
    return (
        "`"
        "uv run python scripts/record_host_manual_run.py "
        f"--host {shlex.quote(host)} "
        f"--status passed --date {run_date} "
        "--evidence '<paste host evidence note>'"
        "`"
    )


def _read_project_version(path: Path) -> str:
    project_block = path.read_text(encoding="utf-8").split("[project]", maxsplit=1)[1].split("[", maxsplit=1)[0]
    match = _PROJECT_VERSION_PATTERN.search(project_block)
    if match is None:
        msg = f"Could not find project version in {path}"
        raise ValueError(msg)
    return match.group(1)


def _today() -> str:
    return datetime.now(tz=timezone.utc).astimezone().date().isoformat()


if __name__ == "__main__":
    main()
