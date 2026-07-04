from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_governed_iteration_execution_report import (
    build_governed_iteration_execution_report,
    render_governed_iteration_execution_report_markdown,
)


def test_governed_iteration_execution_report_stops_after_fifteenth_blocked_iteration() -> None:
    report = build_governed_iteration_execution_report()

    assert report["requested_iteration_count"] == 100
    assert report["executed_iteration_count"] == 15
    assert report["stopped_at_iteration"] == 15
    assert report["stop_reason"] == "current_priority_gate_blocked"
    assert report["completed_path_count"] == 73
    assert report["completed_plan_point_count"] == 73
    assert report["completed_plan_points"] == [
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
        "Added activation evidence-first-cycle for one no-write five-track product cycle.",
        "Added evidence-first result handoff for validated manifest import and host closure.",
        "Added gate transition readiness summary for release and distribution commands.",
        "Added distribution adoption handoff gated behind release readiness.",
        "Kept P1 host-onboarding depth behind real host and beta evidence gates.",
        "Stopped the eleventh 100-iteration follow-up loop at the same external evidence and beta gates.",
        "Added evidence proof-runner for no-write manifest validation and import sequencing.",
        "Added evidence proof-status for required P0 host gap review.",
        "Added evidence transition-pack for trust transition and RC go-check artifacts.",
        "Added rc-unblock-preview for release blocker and unlock command review.",
        "Added operator transcript template for privacy-safe reviewer notes.",
        "Stopped the twelfth 100-iteration follow-up loop at the same external evidence and beta gates.",
        "Added activation acquisition-cycle for one real evidence and beta acquisition control surface.",
        "Added acquisition-cycle artifact pack for real evidence, beta acquisition, and product-depth gate handoff.",
        "Added product-depth gate reasons to keep P1 work blocked until external records exist.",
        "Stopped the thirteenth 100-iteration follow-up loop at the same external evidence and beta gates.",
        "Added activation evidence-cockpit for one real host evidence execution control surface.",
        "Added evidence-cockpit artifact pack for setup, session capture, manifest import, and post-import review.",
        "Added post-import review handoff for proof status, transition pack, and RC unblock preview.",
        "Stopped the fourteenth 100-iteration follow-up loop at the same external evidence and beta gates.",
        "Added activation evidence-product-loop for one no-write evidence-to-product friction summary.",
        "Added evidence-product-loop artifact pack for real host, beta validation, and product backlog handoffs.",
        "Stopped the fifteenth 100-iteration follow-up loop at the same external evidence and beta gates.",
    ]


def test_governed_iteration_execution_report_markdown_explains_stop() -> None:
    markdown = render_governed_iteration_execution_report_markdown(build_governed_iteration_execution_report())
    expected_terms = [
        "Requested iterations: `100`",
        "Executed iterations: `15`",
        "`current_priority_gate_blocked`",
        "evidence execution-packet",
        "artifact-doctor",
        "beta trial-pack",
        "evidence operator-packet",
        "beta intake-wizard",
        "activation command-center",
        "evidence packet-bundle",
        "beta response-validate",
        "activation runbook",
        "evidence replay-fixture-pack",
        "beta response-template",
        "trust gate-transition",
        "rc release-owner-packet",
        "intake bundle",
        "evidence session-manifest",
        "beta response-import-dir",
        "rc review-pack",
        "rc go-check",
        "host setup-probe",
        "evidence collect",
        "preview first-pack",
        "README keeps only the short operator command path",
        "beta loop-pack",
        "evidence import-manifest",
        "evidence session-folder",
        "evidence close-host",
        "activation proof-sprint",
        "Combined Proof Sprint path",
        "host-onboarding depth implementation blocked",
        "activation execution-workspace",
        "Proof Execution Workspace path",
        "real-host execution handoff",
        "beta execution handoff",
        "activation real-proof-run",
        "Real Proof Run path",
        "Beta Acquisition Loop path",
        "P1 Host Onboarding Gate path",
        "activation evidence-first-cycle",
        "Evidence First Cycle path",
        "Evidence-First Result path",
        "Gate Transition Readiness path",
        "Distribution Adoption path",
        "evidence proof-runner",
        "Evidence Proof Runner path",
        "Evidence Proof Status path",
        "Evidence Transition Pack path",
        "RC Unblock Preview path",
        "Operator Transcript Template path",
        "activation acquisition-cycle",
        "Real Evidence Beta Acquisition path",
        "Acquisition Artifact Pack path",
        "Product Depth Gate Reasons path",
        "activation evidence-cockpit",
        "Evidence Cockpit Control path",
        "Evidence Cockpit Artifact path",
        "Post-Import Review path",
        "activation evidence-product-loop",
        "Evidence-to-Product Summary path",
        "Evidence-to-Product Artifact path",
        "`p0_host_evidence_missing_or_blocked`",
        "RC reopen rehearsal v2",
        "No blind implementation loop was executed.",
    ]

    assert markdown.startswith("# Governed 100-Iteration Execution Report\n")
    for term in expected_terms:
        assert term in markdown


def test_committed_governed_iteration_execution_report_is_current() -> None:
    path = Path("docs/GOVERNED_100_ITERATION_REPORT.md")

    assert path.read_text(encoding="utf-8") == render_governed_iteration_execution_report_markdown(
        build_governed_iteration_execution_report()
    )


def test_governed_iteration_execution_report_cli_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "governed-100-iteration-report.md"

    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/export_governed_iteration_execution_report.py", "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_text(encoding="utf-8").startswith("# Governed 100-Iteration Execution Report\n")
