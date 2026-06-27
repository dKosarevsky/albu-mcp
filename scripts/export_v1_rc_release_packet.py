"""Export the gated v1 release-candidate packet."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_p0_evidence_status import build_p0_evidence_status
from scripts.export_v1_rc_readiness_report import build_v1_rc_readiness_report


def build_v1_rc_release_packet() -> dict[str, Any]:
    """Build deterministic v1 RC packet from current RC evidence gates."""
    rc_report = build_v1_rc_readiness_report()
    p0_status = build_p0_evidence_status()
    return {
        "package": rc_report["package"],
        "package_version": rc_report["package_version"],
        "rc_decision": rc_report["rc_decision"],
        "release_candidate_allowed": rc_report["rc_release_candidate_allowed"],
        "required_hosts": rc_report["required_rc_hosts"],
        "p0_summary": p0_status["summary"],
        "blocked_release_steps": _blocked_release_steps(rc_report["rc_release_candidate_allowed"]),
        "ready_release_steps": [
            "uv run pytest -q",
            "uv run ruff check .",
            "uv run ruff format --check .",
            "uv run ty check",
            "uv run python scripts/check_release_readiness.py",
            "uv build",
            "git tag vX.Y.Z-rc.1",
        ],
        "source_reports": ["docs/V1_RC_READINESS.md", "docs/P0_EVIDENCE_STATUS.md"],
    }


def render_v1_rc_release_packet_markdown(packet: dict[str, Any]) -> str:
    """Render the v1 RC packet as Markdown."""
    lines = [
        "# V1 RC Release Packet",
        "",
        f"Package: `{packet['package']}=={packet['package_version']}`",
        f"Required hosts: `{', '.join(packet['required_hosts'])}`",
        f"RC decision: `{packet['rc_decision']}`",
        f"Release candidate allowed: `{str(packet['release_candidate_allowed']).lower()}`",
        "",
        "## P0 Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in packet["p0_summary"].items())
    lines.extend(["", "## Blocked Release Steps", ""])
    lines.extend(f"- {item}" for item in packet["blocked_release_steps"])
    lines.extend(["", "## Ready Release Steps", ""])
    lines.extend(f"- `{item}`" for item in packet["ready_release_steps"])
    lines.extend(["", "## Source Reports", ""])
    lines.extend(f"- `{source}`" for source in packet["source_reports"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for v1 RC release packet exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_v1_rc_release_packet_markdown(build_v1_rc_release_packet())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _blocked_release_steps(release_candidate_allowed: bool) -> list[str]:
    if release_candidate_allowed:
        return ["No RC blockers remain."]
    return [
        "Do not tag v1 RC until P0 real host evidence passes.",
        "Run docs/P0_HOST_RUNBOOK.md for Codex and Claude Code.",
        "Record evidence through docs/P0_EVIDENCE_RECORDER.md.",
        "Regenerate docs/P0_EVIDENCE_STATUS.md and docs/V1_RC_READINESS.md.",
    ]


if __name__ == "__main__":
    main()
