"""Export an operator runner for real P0 MCP host evidence sessions."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p0_host_run_preflight import check_p0_host_run_preflight
from scripts.export_p0_host_unblock_pack import build_p0_host_unblock_pack


def build_host_evidence_runner() -> dict[str, Any]:
    """Build a deterministic host evidence runner pack without fabricating host evidence."""
    preflight = check_p0_host_run_preflight()
    unblock_pack = build_p0_host_unblock_pack()
    lanes = unblock_pack["recovery_lanes"]
    target_hosts = _target_hosts(lanes)
    return {
        "runner_status": "blocked_until_p0_evidence_passes" if lanes else "ready_for_rc_recheck",
        "preflight_status": "passed" if preflight.ok else "failed",
        "rc_reopen_allowed": unblock_pack["rc_reopen_allowed"],
        "summary": {
            "target_host_count": len(target_hosts),
            "runner_lane_count": len(lanes),
            "blocked_lane_count": sum(lane["evidence_status"] == "blocked" for lane in lanes),
            "preflight_check_count": len(preflight.checks),
        },
        "runner_policy": (
            "Run this packet in real MCP host UI sessions only; generated smoke output is not accepted as passed "
            "host evidence."
        ),
        "preflight_commands": [
            "uv run python scripts/check_p0_host_run_preflight.py",
            "uv run python scripts/export_manual_host_acceptance_packet.py --host '<host>' "
            "--output /tmp/albu-host-<host>.md",
        ],
        "host_lanes": [_host_lane(host=host, lanes=lanes) for host in target_hosts],
        "post_run_commands": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_host_evidence_runner.py --output docs/HOST_EVIDENCE_RUNNER.md",
            "uv run python scripts/export_p0_host_unblock_pack.py --output docs/P0_HOST_UNBLOCK_PACK.md",
            "uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md",
            "uv run python scripts/export_rc_cutover_recovery_plan.py --output docs/RC_CUTOVER_RECOVERY_PLAN.md",
            "uv run python scripts/check_release_readiness.py",
        ],
        "source_docs": [
            "docs/P0_HOST_UNBLOCK_PACK.md",
            "docs/P0_HOST_RUN_PREFLIGHT.md",
            "docs/P0_HOST_RUN_SESSION.md",
            "docs/HOST_MANUAL_RUNS.json",
        ],
    }


def render_host_evidence_runner_markdown(runner: dict[str, Any]) -> str:
    """Render the host evidence runner pack as Markdown."""
    lines = [
        "# Host Evidence Runner",
        "",
        f"Runner status: `{runner['runner_status']}`",
        f"Preflight status: `{runner['preflight_status']}`",
        f"RC reopen allowed: `{str(runner['rc_reopen_allowed']).lower()}`",
        "",
        "## Runner Policy",
        "",
        runner["runner_policy"],
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in runner["summary"].items())
    lines.extend(["", "## Preflight Commands", ""])
    lines.extend(f"- `{command}`" for command in runner["preflight_commands"])
    lines.extend(
        [
            "",
            "## Host Lanes",
            "",
            "| Host | Lane Status | Gates | Prompt |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        "| "
        f"{lane['host']} | "
        f"`{lane['lane_status']}` | "
        f"{', '.join(f'`{gate}`' for gate in lane['gates'])} | "
        f"{lane['operator_prompt']} |"
        for lane in runner["host_lanes"]
    )
    lines.extend(["", "## Record Commands", ""])
    for lane in runner["host_lanes"]:
        lines.extend([f"### {lane['host']}", "", "Passed evidence:"])
        lines.extend(f"- `{command}`" for command in lane["passed_record_commands"])
        lines.extend(["", "Blocked evidence:"])
        lines.extend(f"- `{command}`" for command in lane["blocked_record_commands"])
        lines.append("")
    lines.extend(["## Post-Run Commands", ""])
    lines.extend(f"- `{command}`" for command in runner["post_run_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in runner["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for host evidence runner exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_host_evidence_runner_markdown(build_host_evidence_runner())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _target_hosts(lanes: list[dict[str, Any]]) -> list[str]:
    order = ("Codex", "Claude Code")
    hosts = {lane["host"] for lane in lanes}
    return [host for host in order if host in hosts]


def _host_lane(*, host: str, lanes: list[dict[str, Any]]) -> dict[str, Any]:
    host_lanes = [lane for lane in lanes if lane["host"] == host]
    gates = [lane["gate"] for lane in host_lanes]
    return {
        "host": host,
        "lane_status": "blocked_evidence_required" if host_lanes else "ready",
        "gates": gates,
        "operator_prompt": _operator_prompt(host=host),
        "passed_record_commands": [lane["record_command"] for lane in host_lanes],
        "blocked_record_commands": [_blocked_record_command(host=host, gate=gate) for gate in gates],
    }


def _operator_prompt(*, host: str) -> str:
    return (
        f"In {host}, list AlbumentationsX MCP tools, read albumentationsx://examples/client-smoke, "
        "call run_host_smoke_check, then run the First 10 Minutes workflow only if preview_ready is true."
    )


def _blocked_record_command(*, host: str, gate: str) -> str:
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
            host,
            "--status",
            "blocked",
            "--date",
            "YYYY-MM-DD",
            "--evidence",
            f"{host} could not complete {gate}; record the first reviewer-observed blocker only.",
        ]
    )
    return " ".join(shlex.quote(arg) for arg in args)


if __name__ == "__main__":
    main()
