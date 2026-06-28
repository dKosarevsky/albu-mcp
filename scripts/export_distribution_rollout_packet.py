"""Export public distribution rollout steps gated by RC distribution readiness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_distribution_readiness_pack import build_distribution_readiness_pack
from scripts.export_network_growth_tracker import build_network_growth_tracker


def build_distribution_rollout_packet() -> dict[str, Any]:
    """Build a rollout packet without allowing announcements before RC distribution."""
    readiness = build_distribution_readiness_pack()
    growth_tracker = build_network_growth_tracker()
    public_allowed = readiness["distribution_status"] == "ready_for_rc_distribution"
    return {
        "package": readiness["package"],
        "package_version": readiness["package_version"],
        "release_tag": readiness["release_tag"],
        "distribution_status": readiness["distribution_status"],
        "rollout_status": "ready_for_public_rollout" if public_allowed else "blocked_until_rc_distribution",
        "public_announcement_allowed": public_allowed,
        "announcement_policy": "Announce only after RC tag, release, package, and visibility checks pass.",
        "rollout_channels": _rollout_channels(readiness=readiness, growth_tracker=growth_tracker),
        "post_rc_checks": readiness["post_rc_checks"],
        "announcement_sources": [
            "docs/LAUNCH_KIT.md",
            "docs/ADOPTION_PACKET.md",
            "docs/DEMO.md",
            "examples/distortion_review_workflow.md",
        ],
        "source_docs": [
            "docs/DISTRIBUTION_READINESS_PACK.md",
            "docs/NETWORK_GROWTH_TRACKER.md",
            "docs/V1_GROWTH_CUTOVER_REPORT.md",
        ],
        "next_actions": _next_actions(public_allowed=public_allowed),
    }


def render_distribution_rollout_packet_markdown(packet: dict[str, Any]) -> str:
    """Render the distribution rollout packet as Markdown."""
    lines = [
        "# Distribution Rollout Packet",
        "",
        f"Package: `{packet['package']}=={packet['package_version']}`",
        f"Release tag: `{packet['release_tag']}`",
        f"Distribution status: `{packet['distribution_status']}`",
        f"Rollout status: `{packet['rollout_status']}`",
        f"Public announcement allowed: `{str(packet['public_announcement_allowed']).lower()}`",
        "",
        "## Announcement Policy",
        "",
        packet["announcement_policy"],
        "",
        "## Rollout Channels",
        "",
        "| Channel | Status | URL | Check | Next Action |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        "| "
        f"{channel['name']} | "
        f"`{channel['status']}` | "
        f"{channel['url']} | "
        f"`{channel['check']}` | "
        f"{channel['next_action']} |"
        for channel in packet["rollout_channels"]
    )
    lines.extend(["", "## Post-RC Checks", ""])
    lines.extend(f"- `{command}`" for command in packet["post_rc_checks"])
    lines.extend(["", "## Announcement Sources", ""])
    lines.extend(f"- `{source}`" for source in packet["announcement_sources"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in packet["source_docs"])
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in packet["next_actions"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for distribution rollout packet exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_distribution_rollout_packet_markdown(build_distribution_rollout_packet())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _rollout_channels(*, readiness: dict[str, Any], growth_tracker: dict[str, Any]) -> list[dict[str, str]]:
    target_by_name = {target["name"]: target for target in readiness["visibility_targets"]}
    github_feedback = next(channel for channel in growth_tracker["channels"] if channel["id"] == "github_feedback")
    return [
        _visibility_channel(
            channel_id="pypi",
            target=target_by_name["PyPI package page"],
            status=readiness["distribution_status"],
        ),
        _visibility_channel(
            channel_id="github_release",
            target=target_by_name["GitHub Release"],
            status=readiness["distribution_status"],
        ),
        _visibility_channel(
            channel_id="official_registry",
            target=target_by_name["MCP Registry server page"],
            status=readiness["distribution_status"],
        ),
        _visibility_channel(
            channel_id="upstream_docs",
            target=target_by_name["AlbumentationsX upstream docs link"],
            status="ready_after_rc",
        ),
        {
            "id": github_feedback["id"],
            "name": github_feedback["name"],
            "status": github_feedback["status"],
            "url": github_feedback["url"],
            "check": "Manual issue template smoke check.",
            "next_action": github_feedback["next_action"],
        },
    ]


def _visibility_channel(*, channel_id: str, target: dict[str, str], status: str) -> dict[str, str]:
    return {
        "id": channel_id,
        "name": _channel_name(channel_id),
        "status": status,
        "url": target["url"],
        "check": target["check"],
        "next_action": f"Verify {target['name']} after RC publication.",
    }


def _channel_name(channel_id: str) -> str:
    names = {
        "pypi": "PyPI",
        "github_release": "GitHub Release",
        "official_registry": "Official MCP Registry",
        "upstream_docs": "AlbumentationsX upstream docs",
    }
    return names[channel_id]


def _next_actions(*, public_allowed: bool) -> list[str]:
    if public_allowed:
        return [
            "Run post-RC visibility checks before announcements.",
            "Use announcement sources for concise community updates.",
            "Route responses through GitHub feedback templates.",
        ]
    return [
        "Complete P0 host evidence and RC cutover before public rollout.",
        "Keep announcement copy prepared but unpublished.",
        "Regenerate this packet after RC distribution readiness changes.",
    ]


if __name__ == "__main__":
    main()
