from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.export_governed_iteration_execution_report import (
    build_governed_iteration_execution_report,
    render_governed_iteration_execution_report_markdown,
)


def test_governed_iteration_execution_report_stops_after_eighth_blocked_iteration() -> None:
    report = build_governed_iteration_execution_report()

    assert report["requested_iteration_count"] == 100
    assert report["executed_iteration_count"] == 8
    assert report["stopped_at_iteration"] == 8
    assert report["stop_reason"] == "current_priority_gate_blocked"
    assert report["completed_path_count"] == 42
    assert report["completed_plan_point_count"] == 42
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
    ]


def test_governed_iteration_execution_report_markdown_explains_stop() -> None:
    markdown = render_governed_iteration_execution_report_markdown(build_governed_iteration_execution_report())

    assert markdown.startswith("# Governed 100-Iteration Execution Report\n")
    assert "Requested iterations: `100`" in markdown
    assert "Executed iterations: `8`" in markdown
    assert "`current_priority_gate_blocked`" in markdown
    assert "evidence execution-packet" in markdown
    assert "artifact-doctor" in markdown
    assert "beta trial-pack" in markdown
    assert "evidence operator-packet" in markdown
    assert "beta intake-wizard" in markdown
    assert "activation command-center" in markdown
    assert "evidence packet-bundle" in markdown
    assert "beta response-validate" in markdown
    assert "activation runbook" in markdown
    assert "evidence replay-fixture-pack" in markdown
    assert "beta response-template" in markdown
    assert "trust gate-transition" in markdown
    assert "rc release-owner-packet" in markdown
    assert "intake bundle" in markdown
    assert "evidence session-manifest" in markdown
    assert "beta response-import-dir" in markdown
    assert "rc review-pack" in markdown
    assert "rc go-check" in markdown
    assert "host setup-probe" in markdown
    assert "evidence collect" in markdown
    assert "preview first-pack" in markdown
    assert "README keeps only the short operator command path" in markdown
    assert "beta loop-pack" in markdown
    assert "evidence import-manifest" in markdown
    assert "evidence session-folder" in markdown
    assert "evidence close-host" in markdown
    assert "activation proof-sprint" in markdown
    assert "Combined Proof Sprint path" in markdown
    assert "host-onboarding depth implementation blocked" in markdown
    assert "`p0_host_evidence_missing_or_blocked`" in markdown
    assert "RC reopen rehearsal v2" in markdown
    assert "No blind implementation loop was executed." in markdown


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
