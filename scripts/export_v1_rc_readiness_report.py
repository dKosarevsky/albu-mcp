"""Export v1 release-candidate readiness from current host evidence gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_v1_launch_report import build_v1_launch_report

_REQUIRED_RC_HOSTS = ["Codex", "Claude Code"]
_HOST_ORDER = ("Codex", "Claude Code", "Cursor", "Claude Desktop")
_GATE_ORDER = {"first_10_minutes_replay": 0, "manual_host_ui": 1}


def build_v1_rc_readiness_report() -> dict[str, Any]:
    """Build deterministic v1 RC readiness from host-level launch blockers."""
    launch_report = build_v1_launch_report()
    rc_blockers = _sorted_blockers(
        [item for item in launch_report["host_blockers"] if item["host"] in _REQUIRED_RC_HOSTS]
    )
    rc_allowed = not rc_blockers
    return {
        "package": launch_report["package"],
        "package_version": launch_report["package_version"],
        "required_rc_hosts": list(_REQUIRED_RC_HOSTS),
        "rc_decision": "cut_v1_rc" if rc_allowed else "hold_rc",
        "rc_release_candidate_allowed": rc_allowed,
        "stable_v1_allowed": launch_report["ready_for_v1"],
        "rc_blockers": rc_blockers,
        "policy": "RC requires real P0 host evidence; stable v1 requires every supported host gate.",
        "promotion_rule": "Stable v1 requires all supported hosts to pass.",
        "next_checks": [
            "uv run python scripts/export_real_host_evidence_execution_pack.py "
            "--output docs/REAL_HOST_EVIDENCE_EXECUTION.md",
            "uv run python scripts/export_host_ux_hardening_loop.py --output docs/HOST_UX_HARDENING_LOOP.md",
            "uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md",
            "uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md",
            "uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md",
            "uv run python scripts/check_release_readiness.py",
        ],
    }


def render_v1_rc_readiness_report_markdown(report: dict[str, Any]) -> str:
    """Render v1 RC readiness as Markdown."""
    lines = [
        "# V1 RC Readiness Report",
        "",
        f"Package: `{report['package']}=={report['package_version']}`",
        f"Required RC hosts: `{', '.join(report['required_rc_hosts'])}`",
        f"RC decision: `{report['rc_decision']}`",
        f"RC release candidate allowed: `{str(report['rc_release_candidate_allowed']).lower()}`",
        f"Stable v1 allowed: `{str(report['stable_v1_allowed']).lower()}`",
        "",
        "## Policy",
        "",
        report["policy"],
        "",
        "## RC Blockers",
        "",
        "| Host | Priority | Gate | Evidence Status | Next Action |",
        "| --- | --- | --- | --- | --- |",
    ]
    if report["rc_blockers"]:
        lines.extend(
            "| "
            f"{item['host']} | "
            f"`{item['priority']}` | "
            f"`{item['gate']}` | "
            f"`{item['evidence_status']}` | "
            f"`{item['next_action']}` |"
            for item in report["rc_blockers"]
        )
    else:
        lines.append("| none | `none` | `none` | `recorded` | `no_action` |")
    lines.extend(["", "## Promotion Rule", "", report["promotion_rule"], "", "## Next Checks", ""])
    lines.extend(f"- `{command}`" for command in report["next_checks"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for v1 RC readiness exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    report = build_v1_rc_readiness_report()
    content = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_v1_rc_readiness_report_markdown(report)
    )
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _sorted_blockers(items: list[dict[str, str]]) -> list[dict[str, str]]:
    host_rank = {host: index for index, host in enumerate(_HOST_ORDER)}
    return sorted(
        items,
        key=lambda item: (
            host_rank.get(item["host"], len(host_rank)),
            _GATE_ORDER.get(item["gate"], len(_GATE_ORDER)),
        ),
    )


if __name__ == "__main__":
    main()
