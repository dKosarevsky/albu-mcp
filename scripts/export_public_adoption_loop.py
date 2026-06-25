"""Export the public adoption loop for AlbumentationsX MCP."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_launch_kit import build_launch_kit


def build_public_adoption_loop() -> dict[str, Any]:
    """Build a deterministic product adoption loop from committed launch metadata."""
    kit = build_launch_kit()
    return {
        "package": kit["package"],
        "version": kit["version"],
        "telemetry_policy": "No automatic telemetry; collect explicit, privacy-safe feedback only.",
        "stages": [
            {
                "id": "discover",
                "name": "Discover",
                "goal": "Help computer-vision users find the project from trusted public surfaces.",
                "channels": ["PyPI", "Official MCP Registry", "Glama", "AlbumentationsX docs"],
                "proof_assets": ["server.json", "README.md", "docs/ADOPTION_PACKET.md"],
                "success_metric": "A user can find the package, repo, install command, and local privacy model.",
                "next_action": "Keep package, registry, and docs copy aligned after every release.",
            },
            {
                "id": "first_run",
                "name": "First Run",
                "goal": "Turn discovery into a safe local preview within the first session.",
                "channels": ["docs/FIRST_10_MINUTES.md", "docs/INSTALL.md", "docs/USAGE.md"],
                "proof_assets": ["docs/HOST_PROOF_SPRINT_CHECKLIST.md", "docs/V1_TRUST_GATES.md"],
                "success_metric": "Host runs `run_host_smoke_check` and renders a contact sheet from allowed roots.",
                "next_action": "Route setup failures to diagnostics docs and the host-acceptance issue template.",
            },
            {
                "id": "review_decision",
                "name": "Review Decision",
                "goal": "Convert subjective preview review into structured, reproducible tuning actions.",
                "channels": ["plan_preview_review", "record_preview_feedback", "export_preview_report"],
                "proof_assets": ["tests/fixtures/snapshots/output_contracts.json", "docs/USAGE.md"],
                "success_metric": "User feedback maps to tags, a next tool, and an auditable tuning decision.",
                "next_action": "Use `plan_preview_review` before adjustment, audit, or export.",
            },
            {
                "id": "feedback_intake",
                "name": "Feedback Intake",
                "goal": "Collect actionable reports without asking users to expose private datasets.",
                "channels": [
                    ".github/ISSUE_TEMPLATE/host-acceptance.yml",
                    ".github/ISSUE_TEMPLATE/workflow-feedback.yml",
                    ".github/ISSUE_TEMPLATE/dataset-health.yml",
                    ".github/ISSUE_TEMPLATE/feature-request.yml",
                ],
                "proof_assets": ["docs/COMMUNITY_FEEDBACK.md", "docs/NETWORK_GROWTH_TRACKER.md"],
                "success_metric": "Issues include host, command, sanitized artifact, expected result, and actual result.",
                "next_action": "Label issues by host, workflow, dataset health, or feature request.",
            },
            {
                "id": "release_response",
                "name": "Release Response",
                "goal": "Close the loop by turning repeated feedback into docs, tests, or releases.",
                "channels": ["docs/CHANGELOG.md", "docs/RELEASE.md", "docs/V1_RELEASE_TRAIN.md"],
                "proof_assets": ["tests/test_golden_evals.py", "tests/test_output_contract_snapshots.py"],
                "success_metric": "Each repeated issue has a regression test, doc update, or explicit non-goal note.",
                "next_action": "Run weekly triage, batch low-risk fixes, and publish with release evidence.",
            },
        ],
        "weekly_operating_rhythm": [
            "Review new GitHub issues and directory comments during weekly triage.",
            "Group feedback by host setup, dataset health, review workflow, and export workflow.",
            "Promote repeated reports into tests, docs, or generated launch assets.",
            "Regenerate launch, network growth, and adoption loop docs before release candidates.",
        ],
        "next_checks": [
            "uv run python scripts/export_public_adoption_loop.py --output docs/PUBLIC_ADOPTION_LOOP.md",
            "uv run python scripts/export_network_growth_tracker.py --output docs/NETWORK_GROWTH_TRACKER.md",
            "uv run python scripts/export_launch_kit.py --output docs/LAUNCH_KIT.md",
        ],
    }


def render_public_adoption_loop_markdown(loop: dict[str, Any]) -> str:
    """Render the public adoption loop as Markdown."""
    lines = [
        "# Public Adoption Loop",
        "",
        f"Package: `{loop['package']}=={loop['version']}`",
        f"Telemetry policy: {loop['telemetry_policy']}",
        "",
        "## Loop Stages",
        "",
        "| Stage | Goal | Channels | Proof | Metric | Next Action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        "| "
        f"{stage['name']} | "
        f"{stage['goal']} | "
        f"{_join_inline(stage['channels'])} | "
        f"{_join_inline(stage['proof_assets'])} | "
        f"{stage['success_metric']} | "
        f"{stage['next_action']} |"
        for stage in loop["stages"]
    )
    lines.extend(["", "## Weekly Operating Rhythm", ""])
    lines.extend(f"- {item}" for item in loop["weekly_operating_rhythm"])
    lines.extend(["", "## Next Checks", ""])
    lines.extend(f"- `{command}`" for command in loop["next_checks"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for the public adoption loop."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_public_adoption_loop_markdown(build_public_adoption_loop())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _join_inline(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values)


if __name__ == "__main__":
    main()
