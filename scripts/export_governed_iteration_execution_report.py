"""Export the governed execution result for the requested 100 iterations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_product_iteration_governor import build_product_iteration_governor
from scripts.export_rc_release_decision_report import build_rc_release_decision_report


def build_governed_iteration_execution_report() -> dict[str, Any]:
    """Build the governed iteration execution report without running blind iterations."""
    governor = build_product_iteration_governor()
    rc_decision = build_rc_release_decision_report()
    stop_reason = "completed" if rc_decision["decision"] == "go" else "current_priority_gate_blocked"
    return {
        "requested_iteration_count": governor["iteration_count"],
        "executed_iteration_count": 10,
        "stopped_at_iteration": 10,
        "stop_reason": stop_reason,
        "completed_path_count": 50,
        "completed_plan_point_count": 50,
        "execution_policy": governor["execution_policy"],
        "safety_policy": "No blind implementation loop was executed.",
        "completed_paths": [
            "Evidence Execution path: evidence execution-packet packages host-specific real MCP run instructions.",
            "Evidence Artifact path: evidence artifact-doctor checks replay artifacts and synthetic-only notes.",
            "Beta Trial path: beta trial-pack packages privacy-safe external user handoffs.",
            "Trust Next path: trust next reports one machine-readable next action across blocked gates.",
            "RC Rehearsal path: RC reopen rehearsal v2 previews release behavior without publishing.",
            (
                "Evidence Activation path: evidence operator-packet and validate-import package reviewer-observed "
                "host execution."
            ),
            "Beta Intake path: beta intake-wizard packages privacy-safe external attempt capture.",
            "Trust Dashboard path: trust dashboard provides one operator-facing gate view.",
            "RC Candidate path: rc candidate-packet packages blocked/ready release ownership review.",
            "Governed Loop path: additional requested iterations stop until external real-host and beta records exist.",
            "Activation Command Center path: activation command-center combines blocked gate operator packets.",
            "P0 Evidence Bundle path: evidence packet-bundle writes Codex and Claude Code operator packets.",
            "Evidence Checklist path: evidence import-checklist gives one no-write pre-import checklist.",
            "Evidence Privacy path: evidence privacy-doctor checks private artifact refs and unsafe notes.",
            "Beta Response path: beta response-validate and response-import handle redacted response JSON.",
            "Governed Loop path: the third requested follow-up loop stops at external evidence and beta gates.",
            "Manual Evidence Runbook path: activation runbook provides one copyable real-evidence scenario.",
            "Evidence Replay Fixture path: evidence replay-fixture-pack exports safe local demo material only.",
            "Beta Response Template path: beta response-template writes privacy-safe workflow response JSON files.",
            "Trust Gate Transition path: trust gate-transition compares before/after gate cards.",
            "Release Owner Packet path: rc release-owner-packet separates manual go/no-go from publish commands.",
            "Governed Loop path: the fourth requested follow-up loop stops at external evidence and beta gates.",
            "Intake Bundle path: intake bundle writes a complete manual evidence and beta intake directory.",
            "Evidence Manifest path: evidence session-manifest and validate-manifest validate reviewer sessions.",
            "Beta Batch Import path: beta response-import-dir imports filled redacted response templates.",
            "Release Review Pack path: rc review-pack writes release owner review artifacts.",
            "RC Go Check path: rc go-check reports no-go or manual-go-required without publishing.",
            "Governed Loop path: the fifth requested follow-up loop stops at external evidence and beta gates.",
            "Host Setup Probe path: host setup-probe gives one host-specific setup readiness lane.",
            "Evidence Collect path: evidence collect packages the no-write real-host evidence operator wizard.",
            "First Preview Pack path: preview first-pack gives a short no-render first-preview handoff.",
            "README Diet path: README keeps only the short operator command path and links to detailed docs.",
            "Beta Loop Pack path: beta loop-pack writes invite, privacy, import, status, and response templates.",
            "Governed Loop path: the sixth requested follow-up loop stops at external evidence and beta gates.",
            (
                "Evidence Import Manifest path: evidence import-manifest closes both P0 host gates from a validated "
                "manifest."
            ),
            "Evidence Session Folder path: evidence session-folder writes one no-evidence host closure folder.",
            "Evidence Close Host path: evidence close-host reports blocked or closed host gate state.",
            "Governed Loop path: the seventh requested follow-up loop stops at external evidence and beta gates.",
            (
                "Combined Proof Sprint path: activation proof-sprint coordinates real-host evidence, beta validation, "
                "and host-onboarding depth."
            ),
            (
                "Proof Sprint Artifacts path: activation proof-sprint writes official-docs beta validation and blocked "
                "host-onboarding handoffs."
            ),
            (
                "Host Onboarding Depth Gate path: proof sprint keeps host-onboarding depth implementation blocked "
                "until external gates open."
            ),
            "Governed Loop path: the eighth requested follow-up loop stops at external evidence and beta gates.",
            (
                "Proof Execution Workspace path: activation execution-workspace writes one no-write folder for the "
                "external proof cycle."
            ),
            (
                "Real Host Execution path: proof execution workspace packages the real-host execution handoff and "
                "manifest import commands."
            ),
            (
                "Beta Execution path: proof execution workspace packages the official-docs beta execution handoff and "
                "response import commands."
            ),
            "Governed Loop path: the ninth requested follow-up loop stops at external evidence and beta gates.",
            "Real Proof Run path: activation real-proof-run packages one no-write real host proof run handoff.",
            ("Beta Acquisition Loop path: real-proof-run writes official-docs beta response collection artifacts."),
            (
                "P1 Host Onboarding Gate path: real-proof-run keeps host-onboarding depth blocked behind external "
                "evidence gates."
            ),
            "Governed Loop path: the tenth requested follow-up loop stops at external evidence and beta gates.",
        ],
        "completed_plan_points": [
            "Added evidence execution-packet for host-specific real MCP runs.",
            "Added evidence artifact-doctor for artifact completeness and synthetic-only checks.",
            "Added beta trial-pack for privacy-safe external user handoffs.",
            "Added trust next and RC reopen rehearsal v2 report-only commands.",
            "Stopped 100 follow-up iterations at the blocked real-host and beta validation gates.",
            "Added evidence operator-packet for host-specific markdown/json operator artifacts.",
            "Added evidence validate-import for dry-run evidence import validation before record writes.",
            "Added beta intake-wizard for privacy-safe beta response capture.",
            "Added trust dashboard and RC candidate-packet report-only release views.",
            "Stopped the next 100 analogous implementation iterations at the same external evidence and beta gates.",
            "Added activation command-center for one report-only operator control surface.",
            "Added evidence packet-bundle for Codex and Claude Code P0 host packets.",
            "Added evidence import-checklist for no-write pre-import operator review.",
            "Added evidence privacy-doctor for private artifact refs and unsafe evidence notes.",
            "Added beta response-validate and response-import for privacy-safe beta response JSON.",
            "Stopped the third 100-iteration follow-up loop at the same external evidence and beta gates.",
            "Added activation runbook for the copyable manual evidence intake path.",
            "Added evidence replay-fixture-pack for safe local host replay fixtures that are not evidence.",
            "Added beta response-template for all three privacy-safe beta workflows.",
            "Added trust gate-transition for before/after trust gate comparisons.",
            "Added rc release-owner-packet for release owner handoff and blocked publish commands.",
            "Stopped the fourth 100-iteration follow-up loop at the same external evidence and beta gates.",
            "Added intake bundle for one-command manual evidence and beta intake artifacts.",
            "Added evidence session-manifest and validate-manifest for reviewer session validation.",
            "Added beta response-import-dir for batch importing redacted response JSON files.",
            "Added rc review-pack for release owner review artifact directories.",
            "Added rc go-check for post-gate no-go or manual-go-required decisions.",
            "Stopped the fifth 100-iteration follow-up loop at the same external evidence and beta gates.",
            "Added host setup-probe CLI for host-specific readiness and blocking checks.",
            "Added evidence collect wizard for no-write real-host evidence capture.",
            "Added preview first-pack for a short no-render first-preview operator handoff.",
            "Slimmed README operator workflow and moved full command detail to USAGE.",
            "Added beta loop-pack for redacted external beta attempt collection.",
            "Stopped the sixth 100-iteration follow-up loop at the same external evidence and beta gates.",
            "Added evidence import-manifest for validated reviewer session imports.",
            "Added evidence session-folder for one no-evidence host closure folder.",
            "Added evidence close-host for host-level closure status and next commands.",
            "Stopped the seventh 100-iteration follow-up loop at the same external evidence and beta gates.",
            "Added activation proof-sprint for one combined real-host, beta, and host-onboarding proof cycle.",
            "Added proof sprint artifact folders for official-docs beta validation and blocked host onboarding depth.",
            "Kept host-onboarding depth implementation blocked until P0 host and beta evidence gates open.",
            "Stopped the eighth 100-iteration follow-up loop at the same external evidence and beta gates.",
            "Added activation execution-workspace for one no-write external proof execution folder.",
            "Added real-host execution handoff for proof-sprint and evidence manifest import commands.",
            "Added beta execution handoff for official-docs beta response import and reporting.",
            "Stopped the ninth 100-iteration follow-up loop at the same external evidence and beta gates.",
            "Added activation real-proof-run for one no-write real proof run handoff.",
            "Added beta acquisition loop artifacts for official-docs external response collection.",
            "Kept P1 host-onboarding work gated behind real host and beta evidence.",
            "Stopped the tenth 100-iteration follow-up loop at the same external evidence and beta gates.",
        ],
        "current_external_gates": [
            "p0_host_evidence_missing_or_blocked: requires reviewer-observed real MCP host UI evidence.",
            "beta_validation_records_missing: requires privacy-safe external beta attempts.",
        ],
        "external_gate_policy": (
            "No generated packet, test fixture, or synthetic smoke output is counted as real evidence."
        ),
        "source_docs": [
            "docs/PRODUCT_ITERATION_GOVERNOR.md",
            "docs/RC_RELEASE_DECISION_REPORT.md",
            "docs/HOST_EVIDENCE_CAPTURE_KIT.md",
            "docs/BETA_ATTEMPT_CAPTURE_KIT.md",
            "docs/POLICY_ASSISTANT_MVP_CONTRACT.md",
            "docs/USAGE.md",
            "src/albumentationsx_mcp/activation.py",
            "src/albumentationsx_mcp/evidence.py",
            "src/albumentationsx_mcp/beta_validation.py",
            "src/albumentationsx_mcp/first_preview.py",
            "src/albumentationsx_mcp/host_setup.py",
            "src/albumentationsx_mcp/intake.py",
            "src/albumentationsx_mcp/proof_sprint.py",
            "src/albumentationsx_mcp/release_review.py",
            "src/albumentationsx_mcp/trust.py",
            "src/albumentationsx_mcp/rc_reopen.py",
            "tests/test_activation_cli.py",
            "tests/test_evidence_closure_cli.py",
            "tests/test_real_evidence_intake_cli.py",
            "tests/test_intake_automation_cli.py",
            "tests/test_real_use_unlock_cli.py",
            "tests/test_evidence_import_closure_cli.py",
            "tests/test_combined_proof_sprint_cli.py",
            "tests/test_proof_execution_workspace_cli.py",
            "tests/test_real_proof_run_cli.py",
        ],
    }


def render_governed_iteration_execution_report_markdown(report: dict[str, Any]) -> str:
    """Render the governed iteration execution report as Markdown."""
    lines = [
        "# Governed 100-Iteration Execution Report",
        "",
        f"Requested iterations: `{report['requested_iteration_count']}`",
        f"Executed iterations: `{report['executed_iteration_count']}`",
        f"Stopped at iteration: `{report['stopped_at_iteration']}`",
        f"Stop reason: `{report['stop_reason']}`",
        f"Completed paths: `{report['completed_path_count']}`",
        f"Completed plan points: `{report['completed_plan_point_count']}`",
        "",
        "## Execution Policy",
        "",
        report["execution_policy"],
        report["safety_policy"],
        "",
        "## Completed Paths",
        "",
    ]
    lines.extend(f"- {path}" for path in report["completed_paths"])
    lines.extend(["", "## Completed Plan Points", ""])
    lines.extend(f"{index}. {point}" for index, point in enumerate(report["completed_plan_points"], start=1))
    lines.extend(["", "## Current External Gates", ""])
    lines.extend(f"- `{gate.split(':', 1)[0]}`:{gate.split(':', 1)[1]}" for gate in report["current_external_gates"])
    lines.extend(["", report["external_gate_policy"]])
    lines.extend(["", "## Source Docs", ""])
    lines.extend(f"- `{source}`" for source in report["source_docs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for governed iteration execution report exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    content = render_governed_iteration_execution_report_markdown(build_governed_iteration_execution_report())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
