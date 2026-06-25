"""Export public launch kit copy and distribution checklist."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_adoption_packet import build_adoption_packet
from scripts.export_v1_launch_report import build_v1_launch_report


def build_launch_kit() -> dict[str, Any]:
    """Build a deterministic launch kit from committed public metadata."""
    adoption = build_adoption_packet()
    launch_report = build_v1_launch_report()
    return {
        "title": "AlbumentationsX MCP Launch Kit",
        "package": adoption["package"],
        "version": adoption["version"],
        "repository": adoption["repository"],
        "pypi_url": adoption["pypi_url"],
        "registry_url": adoption["registry_url"],
        "upstream_pr_url": adoption["upstream_pr_url"],
        "install_command": adoption["install_command"],
        "preview_command": adoption["preview_command"],
        "ready_for_v1": launch_report["ready_for_v1"],
        "blockers": launch_report["blockers"],
        "demo_assets": [
            "docs/assets/demo/contact_sheet.png",
            "docs/assets/demo/comparison_contact_sheet.png",
            "docs/assets/demo/demo_report.md",
        ],
        "proof_docs": [
            "docs/HOST_PROOF_SPRINT.md",
            "docs/HOST_PROOF_SPRINT_CHECKLIST.md",
            "docs/V1_LAUNCH_REPORT.md",
            "docs/HOST_ACCEPTANCE_EVIDENCE.md",
        ],
        "growth_docs": [
            "docs/NETWORK_GROWTH.md",
            "docs/NETWORK_GROWTH_TRACKER.md",
        ],
        "feedback_templates": [
            ".github/ISSUE_TEMPLATE/host-acceptance.yml",
            ".github/ISSUE_TEMPLATE/workflow-feedback.yml",
            ".github/ISSUE_TEMPLATE/dataset-health.yml",
            ".github/ISSUE_TEMPLATE/feature-request.yml",
        ],
        "workflow_tools": adoption["workflow_tools"],
    }


def render_launch_kit_markdown(kit: dict[str, Any]) -> str:
    """Render a concise public launch kit for distribution and outreach."""
    lines = [
        "# AlbumentationsX MCP Launch Kit",
        "",
        "Use this packet when publishing, submitting, or sharing AlbumentationsX MCP.",
        "",
        "## Primary Links",
        "",
        f"- Repository: {kit['repository']}",
        f"- PyPI: {kit['pypi_url']}",
        f"- MCP Registry: {kit['registry_url']}",
        f"- Upstream docs PR: AlbumentationsX#289 ({kit['upstream_pr_url']})",
        "",
        "## Install",
        "",
        "```bash",
        kit["install_command"],
        "```",
        "",
        "Preview-safe local run:",
        "",
        "```bash",
        kit["preview_command"],
        "```",
        "",
        "## Short Launch Copy",
        "",
        (
            "AlbumentationsX MCP connects MCP hosts to local computer-vision augmentation workflows: inspect dataset "
            "health, render bounded preview contact sheets, compare candidates, capture feedback, and export "
            "reproducible AlbumentationsX pipelines without arbitrary Python execution."
        ),
        "",
        "## Demo Assets",
        "",
        *[f"- `{asset}`" for asset in kit["demo_assets"]],
        "",
        "## First Workflow To Show",
        "",
        *[f"1. `{tool}`" for tool in kit["workflow_tools"]],
        "",
        "## Proof Status",
        "",
        f"- Ready for v1: `{str(kit['ready_for_v1']).lower()}`",
        *[f"- Blocker `{blocker['code']}`: {blocker['summary']}" for blocker in kit["blockers"]],
        "",
        "## Proof Docs",
        "",
        *[f"- `{doc}`" for doc in kit["proof_docs"]],
        "",
        "## Growth Docs",
        "",
        *[f"- `{doc}`" for doc in kit["growth_docs"]],
        "",
        "## Feedback Intake",
        "",
        *[f"- `{template}`" for template in kit["feedback_templates"]],
        "",
        "## Distribution Checklist",
        "",
        "- Keep `server.json`, PyPI, README, and MCP Registry copy aligned.",
        "- Share demo assets only when they are synthetic or safe to publish.",
        "- Link upstream AlbumentationsX documentation instead of duplicating long setup prose.",
        "- Route host proof updates through `docs/HOST_MANUAL_RUNS.json` and regenerated reports.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for launch kit exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_launch_kit_markdown(build_launch_kit())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
