"""Export a privacy-safe adoption triage report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_adoption_packet import build_adoption_packet

_INTAKE_TEMPLATES = [
    ".github/ISSUE_TEMPLATE/host-acceptance.yml",
    ".github/ISSUE_TEMPLATE/workflow-feedback.yml",
    ".github/ISSUE_TEMPLATE/dataset-health.yml",
    ".github/ISSUE_TEMPLATE/feature-request.yml",
]


def build_adoption_triage_report() -> dict[str, Any]:
    """Build deterministic adoption triage guidance from committed public metadata."""
    adoption = build_adoption_packet()
    return {
        "package": adoption["package"],
        "version": adoption["version"],
        "telemetry_policy": "No automatic telemetry; use explicit GitHub issues and redacted artifacts.",
        "intake_templates": list(_INTAKE_TEMPLATES),
        "manual_metrics": [
            {
                "id": "host_acceptance_runs",
                "source": ".github/ISSUE_TEMPLATE/host-acceptance.yml",
                "measure": "Count real host UI runs by host and status.",
                "response": "Update docs/HOST_MANUAL_RUNS.json only after reviewer-confirmed evidence.",
            },
            {
                "id": "first_run_failures",
                "source": "docs/FIRST_10_MINUTES.md and host acceptance issues",
                "measure": "Track the last completed tool before failure.",
                "response": "Patch host UX packets, diagnostics guidance, or install docs.",
            },
            {
                "id": "review_feedback_tags",
                "source": ".github/ISSUE_TEMPLATE/workflow-feedback.yml",
                "measure": "Group free-form feedback by interpret_preview_feedback tags and severity.",
                "response": "Promote repeated tags into Review Agent tests or recipe adjustments.",
            },
            {
                "id": "dataset_health_findings",
                "source": ".github/ISSUE_TEMPLATE/dataset-health.yml",
                "measure": "Group reports by inspect_dataset_quality findings.",
                "response": (
                    "Add regression coverage for repeated findings such as dataset_unknown_category_annotations."
                ),
            },
            {
                "id": "release_response_items",
                "source": "docs/RELEASE.md and docs/CHANGELOG.md",
                "measure": "Count issues closed by docs, tests, host packets, or product code.",
                "response": "Link each release note to the corresponding issue class or explicit non-goal.",
            },
        ],
        "weekly_triage": [
            "Review new issues for private data and ask for redaction before analysis if needed.",
            "Assign one bucket: host setup, first-run flow, review feedback, dataset health, or feature request.",
            "Run interpret_preview_feedback on safe text excerpts when grouping preview review complaints.",
            "Convert repeated reports into tests, generated docs, or release-response notes.",
        ],
        "release_checks": [
            "uv run python scripts/export_adoption_triage_report.py --output docs/ADOPTION_TRIAGE_REPORT.md",
            "uv run python scripts/export_public_adoption_loop.py --output docs/PUBLIC_ADOPTION_LOOP.md",
            "uv run python scripts/check_release_readiness.py",
        ],
    }


def render_adoption_triage_report_markdown(report: dict[str, Any]) -> str:
    """Render adoption triage guidance as Markdown."""
    lines = [
        "# Adoption Triage Report",
        "",
        f"Package: `{report['package']}=={report['version']}`",
        f"Telemetry policy: {report['telemetry_policy']}",
        "",
        "## Intake Templates",
        "",
        *[f"- `{template}`" for template in report["intake_templates"]],
        "",
        "## Manual Metrics",
        "",
        "| Metric | Source | Measure | Response |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| `{metric['id']}` | {metric['source']} | {metric['measure']} | {metric['response']} |"
        for metric in report["manual_metrics"]
    )
    lines.extend(["", "## Weekly Triage", ""])
    lines.extend(f"- {item}" for item in report["weekly_triage"])
    lines.extend(["", "## Release Checks", ""])
    lines.extend(f"- `{command}`" for command in report["release_checks"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for adoption triage report exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_adoption_triage_report_markdown(build_adoption_triage_report())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
