"""Export a go/no-go report for the next v1 RC tag."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_v1_rc_cutover_gate import build_v1_rc_cutover_gate
from scripts.export_beta_validation_status import build_beta_validation_status

_RELEASE_TAG = "v1.15.0-rc.1"


def build_rc_release_decision_report() -> dict[str, Any]:
    """Build a release decision report without mutating release state."""
    gate = build_v1_rc_cutover_gate(tag=_RELEASE_TAG)
    beta = build_beta_validation_status()
    blocked_reasons = _blocked_reasons(gate=gate, beta=beta)
    return {
        "decision": "go" if not blocked_reasons else "no_go",
        "release_tag": _RELEASE_TAG,
        "cutover_allowed": gate["cutover_allowed"],
        "publish_allowed": bool(gate["publish_commands"]),
        "blocked_reasons": blocked_reasons,
        "safe_commands": gate["preflight_commands"],
        "blocked_publish_commands": gate["blocked_publish_commands"],
        "release_policy": "Do not create tags, GitHub Releases, PyPI uploads, or public announcements.",
        "source_docs": [
            "docs/V1_RC_CUTOVER_GATE.md",
            "docs/BETA_VALIDATION_STATUS.md",
            "docs/HOST_MANUAL_RUNS.json",
        ],
    }


def render_rc_release_decision_report_markdown(report: dict[str, Any]) -> str:
    """Render the RC release decision report as Markdown."""
    lines = [
        "# RC Release Decision Report",
        "",
        f"Decision: `{report['decision']}`",
        f"Release tag: `{report['release_tag']}`",
        f"Cutover allowed: `{str(report['cutover_allowed']).lower()}`",
        f"Publish allowed: `{str(report['publish_allowed']).lower()}`",
        "",
        "## Release Policy",
        "",
        report["release_policy"],
        "",
        "## Blocked Reasons",
        "",
    ]
    if report["blocked_reasons"]:
        lines.extend(f"- `{reason}`" for reason in report["blocked_reasons"])
    else:
        lines.append("- none")
    lines.extend(["", "## Safe Commands", ""])
    lines.extend(f"- `{command}`" for command in report["safe_commands"])
    lines.extend(["", "## Blocked Publish Commands", ""])
    if report["blocked_publish_commands"]:
        lines.extend(f"- `{command}`" for command in report["blocked_publish_commands"])
    else:
        lines.append("- none")
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in report["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for RC release decision exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_rc_release_decision_report_markdown(build_rc_release_decision_report())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _blocked_reasons(*, gate: dict[str, Any], beta: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not gate["cutover_allowed"]:
        reasons.append(gate["blocked_reason"])
    if beta["validation_status"] != "ready_for_depth_triage":
        reasons.append("beta_validation_records_missing")
    return reasons


if __name__ == "__main__":
    main()
