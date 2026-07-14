"""Export public launch kit copy and distribution checklist."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_adoption_packet import build_adoption_packet
from scripts.export_lifecycle_status import build_committed_lifecycle_status

_UPSTREAM_MCP_GUIDE_URL = "https://albumentations.ai/docs/integrations/mcp/"


def build_launch_kit() -> dict[str, Any]:
    """Build a deterministic launch kit from committed public metadata."""
    adoption = build_adoption_packet()
    lifecycle = build_committed_lifecycle_status()
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
        "lifecycle": lifecycle,
        "demo_assets": [
            "docs/assets/demo/contact_sheet.png",
            "docs/assets/demo/comparison_contact_sheet.png",
            "docs/assets/demo/demo_report.md",
        ],
        "proof_docs": [
            "docs/HOST_PROOF_SPRINT.md",
            "docs/HOST_PROOF_SPRINT_CHECKLIST.md",
            "docs/STATUS.md",
            "docs/HOST_ACCEPTANCE_EVIDENCE.md",
        ],
        "growth_docs": [
            "docs/GROWTH.md",
            "docs/NETWORK_GROWTH.md",
            "docs/NETWORK_GROWTH_TRACKER.md",
            "docs/PUBLIC_ADOPTION_LOOP.md",
        ],
        "feedback_templates": [
            ".github/ISSUE_TEMPLATE/host-acceptance.yml",
            ".github/ISSUE_TEMPLATE/workflow-feedback.yml",
            ".github/ISSUE_TEMPLATE/dataset-health.yml",
            ".github/ISSUE_TEMPLATE/feature-request.yml",
        ],
        "workflow_tools": adoption["workflow_tools"],
        "campaigns": _build_campaigns(),
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
        "## Audience Campaigns",
        "",
        "Automated preparation stops at this document. Publication: `manual only`. Run one campaign at a time, keep "
        "its destination fixed for seven days, and record only aggregate or voluntarily submitted evidence.",
        "",
        *_render_campaigns(kit["campaigns"]),
        "## Measurement",
        "",
        "Capture the aggregate baseline before publishing and again after seven days. Compare the non-overlapping "
        "PyPI weeks directly; treat GitHub's rolling 14-day Traffic window as directional context:",
        "",
        "```bash",
        'GH_TOKEN="$(gh auth token)" uv run python scripts/export_growth_report.py --output /tmp/albu-growth.md',
        "```",
        "",
        "## Demo Assets",
        "",
        *[f"- `{asset}`" for asset in kit["demo_assets"]],
        "",
        "## First Workflow To Show",
        "",
        *[f"1. `{tool}`" for tool in kit["workflow_tools"]],
        "",
        "## Lifecycle Status",
        "",
        f"- Release health: `{kit['lifecycle']['release_health']['status']}`",
        f"- Host evidence: `{kit['lifecycle']['host_evidence']['status']}`",
        f"- Adoption experiment: `{kit['lifecycle']['adoption_experiment']['status']}`",
        "- Details: `docs/STATUS.md`",
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
        "- Publish campaign copy manually; never automate third-party posts or imply upstream authorship.",
        "- Route host proof updates through `docs/HOST_MANUAL_RUNS.json` and regenerated reports.",
    ]
    return "\n".join(lines) + "\n"


def _build_campaigns() -> list[dict[str, str]]:
    return [
        {
            "id": "classification-robustness",
            "audience": "Classification practitioners testing robustness without destroying label semantics",
            "problem": "Random augmentation policies can make objects unrecognizable before anyone reviews them.",
            "prompt": (
                "Inspect a small allowed image folder, render several medium-intensity robustness variants, compare "
                "them, reduce any variant tagged too_noisy:high, and export only the accepted pipeline."
            ),
            "artifact": "docs/assets/demo/comparison_contact_sheet.png",
            "destination_url": _campaign_destination("classification-robustness"),
            "success_signal": (
                "One voluntary report of a user rendering, rejecting, adjusting, and accepting a first preview."
            ),
        },
        {
            "id": "detection-bbox-safety",
            "audience": "Object-detection teams reviewing COCO or Pascal VOC augmentation safety",
            "problem": "Geometric transforms can silently drop or misalign bounding boxes.",
            "prompt": (
                "Inspect a safe detection fixture, recommend a low-intensity image+bboxes recipe, render bbox "
                "overlays, compare quality with the detection profile, and export only if every reviewed box remains."
            ),
            "artifact": "docs/RECIPES.md#detection-annotation-review",
            "destination_url": _campaign_destination("detection-bbox-safety"),
            "success_signal": (
                "One voluntary report of an accepted bbox-aware preview with bbox_retention_ratio equal to 1.0."
            ),
        },
        {
            "id": "segmentation-mask-safety",
            "audience": "Segmentation teams validating mask-aware geometric augmentation",
            "problem": "A plausible-looking image preview can hide mask coverage loss or misalignment.",
            "prompt": (
                "Inspect a safe segmentation fixture, recommend a low-intensity image+mask recipe, render mask "
                "overlays, compare with the segmentation quality profile, and reject any candidate with coverage loss."
            ),
            "artifact": "docs/RECIPES.md#segmentation-mask-review",
            "destination_url": _campaign_destination("segmentation-mask-safety"),
            "success_signal": (
                "One voluntary report of an accepted mask-aware preview without candidate_mask_coverage_drop."
            ),
        },
    ]


def _campaign_destination(campaign_id: str) -> str:
    return f"{_UPSTREAM_MCP_GUIDE_URL}?utm_source=community&utm_medium=manual&utm_campaign={campaign_id}"


def _render_campaigns(campaigns: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for campaign in campaigns:
        lines.extend(
            [
                f"### {campaign['id']}",
                "",
                f"- Audience: {campaign['audience']}",
                f"- Problem: {campaign['problem']}",
                f'- Prompt: "{campaign["prompt"]}"',
                f"- Artifact: `{campaign['artifact']}`",
                f"- Destination: {campaign['destination_url']}",
                f"- Success signal: {campaign['success_signal']}",
                "",
            ]
        )
    return lines


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
