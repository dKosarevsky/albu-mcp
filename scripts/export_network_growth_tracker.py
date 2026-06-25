"""Export deterministic public distribution and network growth tracker."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_launch_kit import build_launch_kit
from scripts.export_v1_launch_report import build_v1_launch_report


def build_network_growth_tracker() -> dict[str, Any]:
    """Build a deterministic tracker for public distribution work."""
    launch_kit = build_launch_kit()
    launch_report = build_v1_launch_report()
    return {
        "package": launch_kit["package"],
        "version": launch_kit["version"],
        "ready_for_v1": launch_report["ready_for_v1"],
        "channels": [
            {
                "id": "pypi",
                "name": "PyPI",
                "status": "published",
                "url": launch_kit["pypi_url"],
                "next_action": "Keep package metadata aligned with README and server.json before every release.",
            },
            {
                "id": "official_registry",
                "name": "Official MCP Registry",
                "status": "listed",
                "url": launch_kit["registry_url"],
                "next_action": "Run scripts/check_mcp_registry_status.py after publishing a new package version.",
            },
            {
                "id": "glama",
                "name": "Glama",
                "status": "listed",
                "url": "https://glama.ai/mcp/servers/dKosarevsky/albu-mcp",
                "next_action": "Check title, categories, install command, and computer-vision wording after releases.",
            },
            {
                "id": "upstream_docs",
                "name": "AlbumentationsX Docs",
                "status": "merged",
                "url": launch_kit["upstream_pr_url"],
                "next_action": "Keep local onboarding and first-10-minutes docs aligned with the upstream guide.",
            },
            {
                "id": "github_feedback",
                "name": "GitHub Feedback Intake",
                "status": "ready",
                "url": "https://github.com/dKosarevsky/albu-mcp/issues/new/choose",
                "next_action": "Route host, workflow, dataset health, and feature feedback through issue templates.",
            },
        ],
        "proof_assets": [
            "docs/HOST_PROOF_SPRINT_CHECKLIST.md",
            "docs/V1_LAUNCH_REPORT.md",
            "docs/HOST_ACCEPTANCE_EVIDENCE.md",
        ],
        "launch_assets": [
            "docs/LAUNCH_KIT.md",
            "docs/ADOPTION_PACKET.md",
            "docs/DEMO.md",
            "examples/distortion_review_workflow.md",
        ],
        "feedback_templates": [
            ".github/ISSUE_TEMPLATE/host-acceptance.yml",
            ".github/ISSUE_TEMPLATE/workflow-feedback.yml",
            ".github/ISSUE_TEMPLATE/dataset-health.yml",
            ".github/ISSUE_TEMPLATE/feature-request.yml",
        ],
        "next_checks": [
            "uv run python scripts/check_directory_presence.py",
            "uv run python scripts/check_mcp_registry_status.py",
            "uv run python scripts/export_network_growth_tracker.py --output docs/NETWORK_GROWTH_TRACKER.md",
        ],
    }


def render_network_growth_tracker_markdown(tracker: dict[str, Any]) -> str:
    """Render the network growth tracker as Markdown."""
    lines = [
        "# Network Growth Tracker",
        "",
        f"Package: `{tracker['package']}=={tracker['version']}`",
        f"Ready for v1: `{str(tracker['ready_for_v1']).lower()}`",
        "",
        "## Channels",
        "",
        "| Channel | Status | URL | Next Action |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| {channel['name']} | `{channel['status']}` | {channel['url']} | {channel['next_action']} |"
        for channel in tracker["channels"]
    )
    lines.extend(["", "## Proof Assets", ""])
    lines.extend(f"- `{asset}`" for asset in tracker["proof_assets"])
    lines.extend(["", "## Launch Assets", ""])
    lines.extend(f"- `{asset}`" for asset in tracker["launch_assets"])
    lines.extend(["", "## Feedback Templates", ""])
    lines.extend(f"- `{template}`" for template in tracker["feedback_templates"])
    lines.extend(["", "## Next Checks", ""])
    lines.extend(f"- `{command}`" for command in tracker["next_checks"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for network growth tracker exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_network_growth_tracker_markdown(build_network_growth_tracker())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
