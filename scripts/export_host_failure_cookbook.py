"""Export host failure triage guidance for real MCP UI evidence runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def build_host_failure_cookbook() -> dict[str, Any]:
    """Build deterministic host failure guidance without reading private host logs."""
    return {
        "title": "Host Failure Cookbook",
        "privacy_policy": (
            "Keep private datasets, prompts, screenshots, local home paths, tokens, "
            "and full host logs out of committed evidence. Record only redacted symptoms "
            "and the first failing gate."
        ),
        "failure_cases": [
            {
                "code": "tools_not_visible",
                "symptom": "The host starts but does not show AlbumentationsX MCP tools.",
                "first_check": "Ask the host to read `albumentationsx://examples/client-smoke`.",
                "fix": "Restart the host, verify MCP config shape, then run `run_host_smoke_check` after tools appear.",
                "record_status": "blocked",
                "record_note": "Host could not list AlbumentationsX MCP tools after config reload.",
            },
            {
                "code": "stale_tool_cache",
                "symptom": "The host shows an older tool list after package or config changes.",
                "first_check": "Restart the host and clear client-side MCP server discovery cache.",
                "fix": "Confirm the host sees the current `albumentationsx-mcp` version and rerun client smoke.",
                "record_status": "blocked",
                "record_note": "Host kept stale MCP tool discovery after package upgrade.",
            },
            {
                "code": "path_policy_rejected",
                "symptom": "Preview validation rejects local images or directories.",
                "first_check": "Run `diagnose_environment` and inspect `fix_allowed_root` remediation.",
                "fix": "Restart the server with an existing absolute `--allowed-root` that contains the sample image.",
                "record_status": "blocked",
                "record_note": "Host path policy rejected the configured allowed root or sample image.",
            },
            {
                "code": "artifact_root_unwritable",
                "symptom": "Preview rendering starts but artifacts, manifests, or contact sheets are missing.",
                "first_check": "Check artifact root permissions outside the host.",
                "fix": "Restart with a writable absolute `--artifact-root` and rerun `render_preview_batch`.",
                "record_status": "blocked",
                "record_note": "Host could not write preview artifacts under the configured artifact root.",
            },
            {
                "code": "uvx_startup_failed",
                "symptom": "The host cannot start the MCP server process.",
                "first_check": "Run the exact `uvx` command in a terminal.",
                "fix": "Fix terminal startup errors first, then paste the same command back into host config.",
                "record_status": "blocked",
                "record_note": "Host could not start the `uvx` MCP server command.",
            },
        ],
        "triage_commands": [
            "uv run python scripts/export_manual_host_acceptance_packet.py --host '<host>' "
            "--output /tmp/albu-host-<host>.md",
            "uv run python scripts/record_host_manual_run.py --host '<host>' --status blocked "
            "--date YYYY-MM-DD --evidence '<redacted blocker note>'",
            "uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md",
            "uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md",
            "uv run python scripts/export_host_evidence_sprint_board.py --output docs/HOST_EVIDENCE_SPRINT_BOARD.md",
        ],
    }


def render_host_failure_cookbook_markdown(cookbook: dict[str, Any]) -> str:
    """Render host failure guidance as Markdown."""
    lines = [
        f"# {cookbook['title']}",
        "",
        "## Privacy Policy",
        "",
        cookbook["privacy_policy"],
        "",
        "## Failure Cases",
        "",
    ]
    for item in cookbook["failure_cases"]:
        lines.extend(
            [
                f"### {item['code']}",
                "",
                f"- Symptom: {item['symptom']}",
                f"- First check: {item['first_check']}",
                f"- Fix: {item['fix']}",
                f"- Record status: `{item['record_status']}`",
                f"- Evidence note: {item['record_note']}",
                "",
            ]
        )
    lines.extend(["## Record Blocked Evidence", ""])
    lines.extend(f"- `{command}`" for command in cookbook["triage_commands"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for host failure cookbook exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_host_failure_cookbook_markdown(build_host_failure_cookbook())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
