"""Export a privacy-safe beta campaign pack."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_beta_feedback_intake import build_beta_feedback_intake
from scripts.export_beta_feedback_status import build_beta_feedback_status
from scripts.export_beta_workflow_pack import build_beta_workflow_pack

_TARGET_BETA_RECORDS = 5


def build_beta_campaign_pack() -> dict[str, Any]:
    """Build a campaign pack for collecting real, redacted beta feedback."""
    workflow_pack = build_beta_workflow_pack()
    intake = build_beta_feedback_intake()
    status = build_beta_feedback_status()
    triage_by_workflow = {workflow["workflow_id"]: workflow["triage_hint"] for workflow in intake["workflow_intake"]}
    return {
        "campaign_status": "ready_to_invite",
        "feedback_status": status["feedback_status"],
        "target_beta_records": _TARGET_BETA_RECORDS,
        "privacy_guard": "Do not request private datasets, raw images, private paths, or credentials.",
        "outreach_copy": (
            "Try AlbumentationsX MCP on a small local image folder, keep data private, and share only redacted "
            "workflow symptoms plus generated artifact references."
        ),
        "workflow_cards": [
            _workflow_card(workflow=workflow, triage_bucket=triage_by_workflow[workflow["id"]])
            for workflow in workflow_pack["workflows"]
        ],
        "triage_loop": [
            "Collect redacted workflow symptoms until at least five beta records exist.",
            "Group repeated reports by workflow_id and triage_bucket.",
            "Convert repeated reports into failing tests before changing runtime behavior.",
            "Regenerate beta status, Review Agent v3 plan, and Dataset Quality plan after each accepted record batch.",
        ],
        "source_docs": [
            "docs/BETA_WORKFLOW_PACK.md",
            "docs/BETA_FEEDBACK_INTAKE.md",
            "docs/BETA_FEEDBACK_STATUS.md",
            "docs/BETA_FEEDBACK_RECORDS.json",
        ],
    }


def render_beta_campaign_pack_markdown(pack: dict[str, Any]) -> str:
    """Render the beta campaign pack as Markdown."""
    lines = [
        "# Beta Campaign Pack",
        "",
        f"Campaign status: `{pack['campaign_status']}`",
        f"Feedback status: `{pack['feedback_status']}`",
        f"Target beta records: `{pack['target_beta_records']}`",
        "",
        "## Privacy Guard",
        "",
        pack["privacy_guard"],
        "",
        "## Outreach Copy",
        "",
        pack["outreach_copy"],
        "",
        "## Workflow Cards",
        "",
    ]
    for workflow in pack["workflow_cards"]:
        lines.extend(
            [
                f"### {workflow['workflow_id']}",
                "",
                f"- Title: {workflow['title']}",
                f"- Target user: {workflow['target_user']}",
                f"- Triage bucket: `{workflow['triage_bucket']}`",
                f"- Done when: {workflow['done_when']}",
                f"- Record command: `{workflow['record_command']}`",
                "- MCP flow:",
            ]
        )
        lines.extend(f"  - `{tool}`" for tool in workflow["mcp_flow"])
        lines.append("")
    lines.extend(["## Triage Loop", ""])
    lines.extend(f"- {item}" for item in pack["triage_loop"])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in pack["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for beta campaign pack exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_beta_campaign_pack_markdown(build_beta_campaign_pack())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _workflow_card(*, workflow: dict[str, Any], triage_bucket: str) -> dict[str, Any]:
    return {
        "workflow_id": workflow["id"],
        "title": workflow["title"],
        "target_user": workflow["target_user"],
        "done_when": workflow["done_when"],
        "mcp_flow": workflow["mcp_flow"],
        "triage_bucket": triage_bucket,
        "record_command": _record_command(workflow_id=workflow["id"], triage_bucket=triage_bucket),
    }


def _record_command(*, workflow_id: str, triage_bucket: str) -> str:
    args = [
        "uv",
        "run",
        "python",
        "scripts/record_beta_feedback.py",
        "--feedback-id",
        f"beta-YYYYMMDD-{workflow_id}",
        "--workflow-id",
        workflow_id,
        "--triage-bucket",
        triage_bucket,
        "--report-date",
        "YYYY-MM-DD",
        "--reporter-role",
        "<redacted role>",
        "--summary",
        "<redacted workflow symptom>",
        "--artifact-ref",
        "docs/assets/demo/demo_report.md",
        "--status",
        "new",
    ]
    return " ".join(shlex.quote(arg) for arg in args)


if __name__ == "__main__":
    main()
