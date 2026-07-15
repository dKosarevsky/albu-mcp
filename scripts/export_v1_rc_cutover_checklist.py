"""Export a gated v1 RC cutover checklist."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_v1_rc_release_packet import build_v1_rc_release_packet
from scripts.historical_status import add_historical_status_banner


def build_v1_rc_cutover_checklist() -> dict[str, Any]:
    """Build the v1 RC cutover checklist from the current release packet."""
    packet = build_v1_rc_release_packet()
    return {
        "package": packet["package"],
        "package_version": packet["package_version"],
        "required_hosts": packet["required_hosts"],
        "rc_decision": packet["rc_decision"],
        "release_candidate_allowed": packet["release_candidate_allowed"],
        "cutover_status": "ready" if packet["release_candidate_allowed"] else "blocked",
        "hard_gates": [
            "P0 real host evidence passed for Codex and Claude Code.",
            "Generated P0 evidence status and v1 RC release packet are current.",
            "Local release readiness, type checks, lint, tests, and build pass.",
            "CI passes on the supported Python matrix.",
        ],
        "no_go_rules": [
            "Do not create or push an RC tag while cutover_status is blocked.",
            "Do not use synthetic host evidence to satisfy P0 gates.",
            "Do not publish a GitHub Release or PyPI build before the RC tag exists.",
        ],
        "ready_commands": packet["ready_release_steps"]
        + [
            "git push origin vX.Y.Z-rc.1",
            "gh release create vX.Y.Z-rc.1 --prerelease --generate-notes",
        ],
        "source_reports": packet["source_reports"]
        + [
            "docs/P0_HOST_EXECUTION_SPRINT.md",
            "docs/P0_BLOCKER_TRIAGE.md",
        ],
    }


def render_v1_rc_cutover_checklist_markdown(checklist: dict[str, Any]) -> str:
    """Render the v1 RC cutover checklist as Markdown."""
    lines = [
        "# V1 RC Cutover Checklist",
        "",
        f"Package: `{checklist['package']}=={checklist['package_version']}`",
        f"Required hosts: `{', '.join(checklist['required_hosts'])}`",
        f"RC decision: `{checklist['rc_decision']}`",
        f"Release candidate allowed: `{str(checklist['release_candidate_allowed']).lower()}`",
        f"Cutover status: `{checklist['cutover_status']}`",
        "",
        "## Hard Gates",
        "",
    ]
    lines.extend(f"- {gate}" for gate in checklist["hard_gates"])
    lines.extend(["", "## No-Go Rules", ""])
    lines.extend(f"- {rule}" for rule in checklist["no_go_rules"])
    lines.extend(["", "## Ready Commands", ""])
    lines.extend(f"- `{command}`" for command in checklist["ready_commands"])
    lines.extend(["", "## Source Reports", ""])
    lines.extend(f"- `{source}`" for source in checklist["source_reports"])
    return add_historical_status_banner("\n".join(lines) + "\n")


def main() -> None:
    """CLI entrypoint for v1 RC cutover checklist exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_v1_rc_cutover_checklist_markdown(build_v1_rc_cutover_checklist())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
