"""Export distribution readiness commands gated by the RC cutover state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_v1_rc_cutover_gate import build_v1_rc_cutover_gate


def build_distribution_readiness_pack() -> dict[str, Any]:
    """Build distribution readiness without calling live registries."""
    rc_gate = build_v1_rc_cutover_gate()
    post_rc_checks = [
        "uv run python scripts/check_published_package_smoke.py --version 1.15.0",
        "uv run python scripts/check_mcp_registry_status.py",
        "uv run python scripts/check_directory_presence.py",
    ]
    return {
        "package": rc_gate["package"],
        "package_version": rc_gate["package_version"],
        "release_tag": rc_gate["release_tag"],
        "distribution_status": (
            "ready_for_rc_distribution" if rc_gate["cutover_allowed"] else "blocked_until_rc_cutover"
        ),
        "rc_cutover_allowed": rc_gate["cutover_allowed"],
        "publish_commands": rc_gate["publish_commands"],
        "blocked_publish_commands": rc_gate["blocked_publish_commands"],
        "post_rc_checks": post_rc_checks,
        "visibility_targets": [
            {
                "name": "PyPI package page",
                "url": "https://pypi.org/project/albumentationsx-mcp/",
                "check": "uv run python scripts/check_published_package_smoke.py --version 1.15.0",
            },
            {
                "name": "GitHub Release",
                "url": "https://github.com/dKosarevsky/albu-mcp/releases",
                "check": "gh release view vX.Y.Z-rc.1",
            },
            {
                "name": "MCP Registry server page",
                "url": "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp",
                "check": "uv run python scripts/check_mcp_registry_status.py",
            },
            {
                "name": "AlbumentationsX upstream docs link",
                "url": "https://github.com/albumentations-team/AlbumentationsX/blob/main/docs/integrations/mcp.md",
                "check": "Manual link check after upstream docs rebuild.",
            },
        ],
        "source_docs": [
            "docs/RELEASE.md",
            "docs/V1_RC_CUTOVER_GATE.md",
            "docs/NETWORK_GROWTH.md",
            "docs/UPSTREAM_PR_PACKET.md",
        ],
        "next_actions": _next_actions(rc_cutover_allowed=rc_gate["cutover_allowed"]),
    }


def render_distribution_readiness_pack_markdown(pack: dict[str, Any]) -> str:
    """Render distribution readiness as Markdown."""
    lines = [
        "# Distribution Readiness Pack",
        "",
        f"Package: `{pack['package']}=={pack['package_version']}`",
        f"Release tag: `{pack['release_tag']}`",
        f"Distribution status: `{pack['distribution_status']}`",
        f"RC cutover allowed: `{str(pack['rc_cutover_allowed']).lower()}`",
        "",
        "## Publish Commands",
        "",
    ]
    if pack["publish_commands"]:
        lines.extend(f"- `{command}`" for command in pack["publish_commands"])
    else:
        lines.append("- none")
    lines.extend(["", "## Blocked Publish Commands", ""])
    if pack["blocked_publish_commands"]:
        lines.extend(f"- `{command}`" for command in pack["blocked_publish_commands"])
    else:
        lines.append("- none")
    lines.extend(["", "## Post-RC Checks", ""])
    lines.extend(f"- `{command}`" for command in pack["post_rc_checks"])
    lines.extend(
        [
            "",
            "## Visibility Targets",
            "",
            "| Target | URL | Check |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| {target['name']} | {target['url']} | `{target['check']}` |" for target in pack["visibility_targets"]
    )
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in pack["source_docs"])
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in pack["next_actions"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for distribution readiness exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_distribution_readiness_pack_markdown(build_distribution_readiness_pack())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _next_actions(*, rc_cutover_allowed: bool) -> list[str]:
    if rc_cutover_allowed:
        return [
            "Run publish commands from a clean release worktree.",
            "Run post-RC visibility checks after GitHub Release and package publication.",
            "Update public adoption notes with the RC validation state.",
        ]
    return [
        "Keep distribution blocked until the hard RC cutover gate opens.",
        "Do not publish GitHub Release, PyPI package, or registry announcements before P0 evidence passes.",
        "Use this pack as the post-RC checklist once real-host evidence is recorded.",
    ]


if __name__ == "__main__":
    main()
