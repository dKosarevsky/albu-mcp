"""Export an actionable Host Proof Sprint checklist from committed evidence state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_v1_launch_report import build_v1_launch_report


def build_host_proof_sprint_checklist() -> dict[str, Any]:
    """Build host-by-host proof sprint tasks from the current v1 launch report."""
    report = build_v1_launch_report()
    return {
        "package": report["package"],
        "package_version": report["package_version"],
        "ready_for_v1": report["ready_for_v1"],
        "blockers": report["blockers"],
        "hosts": report["evidence_plan"],
        "setup_commands": [
            (
                "uv run python scripts/export_manual_host_acceptance_packet.py "
                "--host '<host>' --output /tmp/albu-host-<host>.md"
            ),
            "uv run python scripts/check_host_proof_sprint.py",
        ],
        "record_after_each_host": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/check_first_10_minutes_replay.py --host '<host>'",
        ],
        "regenerate_after_sprint": [
            "uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md",
            "uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md",
            "uv run python scripts/export_host_proof_sprint_checklist.py --output docs/HOST_PROOF_SPRINT_CHECKLIST.md",
            "uv run python scripts/check_release_readiness.py",
        ],
    }


def render_host_proof_sprint_checklist_markdown(checklist: dict[str, Any]) -> str:
    """Render the Host Proof Sprint checklist as reviewable Markdown."""
    lines = [
        "# Host Proof Sprint Checklist",
        "",
        f"Package: `{checklist['package']}=={checklist['package_version']}`",
        f"Ready for v1: `{str(checklist['ready_for_v1']).lower()}`",
        "",
        "## Current Blockers",
        "",
    ]
    if checklist["blockers"]:
        lines.extend(f"- `{blocker['code']}`: {blocker['summary']}" for blocker in checklist["blockers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Setup", ""])
    lines.extend(f"- `{command}`" for command in checklist["setup_commands"])
    lines.extend(["", "## Host Runs", ""])
    for host in checklist["hosts"]:
        lines.extend(_host_lines(host))
    lines.extend(["", "## Record After Each Host", ""])
    lines.extend(f"- `{command}`" for command in checklist["record_after_each_host"])
    lines.extend(["", "## Regenerate After Sprint", ""])
    lines.extend(f"- `{command}`" for command in checklist["regenerate_after_sprint"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for Host Proof Sprint checklist exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_host_proof_sprint_checklist_markdown(build_host_proof_sprint_checklist())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _host_lines(host: dict[str, Any]) -> list[str]:
    return [
        f"### {host['host']}",
        "",
        f"- Manual UI status: `{host['manual_host_ui']['status']}`",
        f"- First 10 Minutes status: `{host['first_10_minutes_replay']['status']}`",
        "- Run the packet prompt in the real host UI before recording evidence.",
        f"- Manual UI record command: `{host['record_commands']['manual_host_ui']}`",
        f"- First 10 Minutes record command: `{host['record_commands']['first_10_minutes_replay']}`",
        "",
    ]


if __name__ == "__main__":
    main()
