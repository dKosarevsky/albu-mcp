"""Export the gated v1 RC automation pack."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_v1_rc_cutover_checklist import build_v1_rc_cutover_checklist


def build_v1_rc_automation_pack() -> dict[str, Any]:
    """Build release automation commands from the current RC cutover state."""
    checklist = build_v1_rc_cutover_checklist()
    ready_commands = checklist["ready_commands"]
    preflight_commands = [command for command in ready_commands if not _is_publish_command(command)]
    publish_commands = [command for command in ready_commands if _is_publish_command(command)]
    return {
        "package": checklist["package"],
        "package_version": checklist["package_version"],
        "required_hosts": checklist["required_hosts"],
        "rc_decision": checklist["rc_decision"],
        "release_candidate_allowed": checklist["release_candidate_allowed"],
        "automation_status": "ready" if checklist["release_candidate_allowed"] else "blocked",
        "operator_warnings": [
            "Do not run publish commands while automation_status is blocked.",
            "Do not create an RC tag before P0 real host evidence is recorded.",
            "Run preflight commands from a clean worktree after regenerating release reports.",
        ],
        "preflight_commands": preflight_commands,
        "publish_commands": publish_commands,
        "source_docs": [
            "docs/V1_RC_CUTOVER_CHECKLIST.md",
            "docs/V1_RC_RELEASE_PACKET.md",
            "docs/P0_HOST_EVIDENCE_LEDGER.md",
        ],
    }


def render_v1_rc_automation_pack_markdown(pack: dict[str, Any]) -> str:
    """Render the v1 RC automation pack as Markdown."""
    lines = [
        "# V1 RC Automation Pack",
        "",
        f"Package: `{pack['package']}=={pack['package_version']}`",
        f"Required hosts: `{', '.join(pack['required_hosts'])}`",
        f"RC decision: `{pack['rc_decision']}`",
        f"Release candidate allowed: `{str(pack['release_candidate_allowed']).lower()}`",
        f"Automation status: `{pack['automation_status']}`",
        "",
        "## Operator Warnings",
        "",
    ]
    lines.extend(f"- {warning}" for warning in pack["operator_warnings"])
    lines.extend(["", "## Preflight Commands", ""])
    lines.extend(f"- `{command}`" for command in pack["preflight_commands"])
    lines.extend(["", "## Publish Commands", ""])
    lines.extend(f"- `{command}`" for command in pack["publish_commands"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in pack["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for v1 RC automation pack exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_v1_rc_automation_pack_markdown(build_v1_rc_automation_pack())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _is_publish_command(command: str) -> bool:
    return command.startswith(("git tag ", "git push origin v", "gh release create "))


if __name__ == "__main__":
    main()
