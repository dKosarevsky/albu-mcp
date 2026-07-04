from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.validate_beta_validation_records import validate_beta_validation_records
from scripts.validate_host_manual_runs import validate_host_manual_runs


def test_package_cli_records_host_evidence_and_prints_status(tmp_path: Path) -> None:
    evidence_path = tmp_path / "HOST_MANUAL_RUNS.json"

    host_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "record-host-ui",
            "--path",
            str(evidence_path),
            "--host",
            "Codex",
            "--status",
            "passed",
            "--date",
            "2026-06-28",
            "--evidence",
            "Codex listed MCP tools and completed run_host_smoke_check in a reviewer-observed session.",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    replay_result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "record-first-10-minutes",
            "--path",
            str(evidence_path),
            "--host",
            "Codex",
            "--status",
            "passed",
            "--date",
            "2026-06-28",
            "--evidence",
            "Codex completed the first-10-minutes replay from install to preview comparison.",
            "--artifact",
            "docs/assets/demo/demo_report.md",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    status_result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "evidence",
            "status",
            "--path",
            str(evidence_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    records = validate_host_manual_runs(evidence_path)
    assert "recorded Codex passed" in host_result.stdout
    assert "recorded first-10-minutes Codex passed" in replay_result.stdout
    assert status_result.stdout == "host evidence records are valid (manual_host_ui=1, first_10_minutes_replay=1)\n"
    assert records.manual_host_ui[0].host == "Codex"
    assert records.first_10_minutes_replay[0].artifacts == ["docs/assets/demo/demo_report.md"]


def test_package_cli_records_beta_attempt_and_prints_status(tmp_path: Path) -> None:
    records_path = tmp_path / "BETA_VALIDATION_RECORDS.json"

    record_result = subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "record-attempt",
            "--path",
            str(records_path),
            "--workflow-id",
            "robustness_distortion_variants",
            "--status",
            "needs_followup",
            "--attempt-date",
            "2026-06-28",
            "--participant-role",
            "CV engineer",
            "--summary",
            "Generated distorted variants, but one example was too noisy for object recognition.",
            "--triage-bucket",
            "review_agent_v3_gap",
            "--artifact-ref",
            "docs/assets/demo/contact_sheet.png",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    status_result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "status",
            "--path",
            str(records_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    records = validate_beta_validation_records(records_path)
    assert "recorded beta validation attempt robustness_distortion_variants" in record_result.stdout
    assert status_result.stdout == "beta validation records are valid (records=1)\n"
    assert records.records[0].private_data_included is False
    assert records.records[0].triage_bucket == "review_agent_v3_gap"


def test_package_cli_triages_beta_attempts_to_backlog_lanes(tmp_path: Path) -> None:
    records_path = tmp_path / "BETA_VALIDATION_RECORDS.json"
    subprocess.run(  # noqa: S603 - package CLI under test with controlled fixture paths.
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "record-attempt",
            "--path",
            str(records_path),
            "--workflow-id",
            "noisy_preview_tuning",
            "--status",
            "needs_followup",
            "--attempt-date",
            "2026-06-28",
            "--participant-role",
            "ML practitioner",
            "--summary",
            "Noisy candidate feedback mapped to tags, but the adjusted pipeline still needs review.",
            "--triage-bucket",
            "review_agent_v3_gap",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    triage_result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "albumentationsx_mcp",
            "beta",
            "triage",
            "--path",
            str(records_path),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(triage_result.stdout)
    lane = next(item for item in payload["triage_lanes"] if item["triage_bucket"] == "review_agent_v3_gap")

    assert payload["triage_status"] == "beta_signal_recorded"
    assert payload["product_depth_allowed"] is False
    assert payload["summary"]["record_count"] == 1
    assert lane["signal_count"] == 1
    assert lane["recommendation_status"] == "candidate_backlog_item"


def test_readme_and_usage_document_operator_cli() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    usage = Path("docs/USAGE.md").read_text(encoding="utf-8")

    readme_expected = [
        "albu-mcp host setup-probe",
        "albu-mcp preview first-pack",
        "albu-mcp evidence collect",
        "albu-mcp intake bundle",
        "albu-mcp beta loop-pack",
        "albu-mcp rc go-check",
        "`plan_augmentation_policy`",
        "`plan_policy_iteration`",
    ]
    usage_expected = [
        "albu-mcp host setup-probe",
        "albu-mcp preview first-pack",
        "albu-mcp intake bundle",
        "albu-mcp activation command-center",
        "albu-mcp activation runbook",
        "albu-mcp activation acquisition-cycle",
        "albu-mcp activation evidence-cockpit",
        "albu-mcp evidence collect",
        "albu-mcp evidence status",
        "albu-mcp evidence run-session",
        "albu-mcp evidence execution-packet",
        "albu-mcp evidence operator-packet",
        "albu-mcp evidence packet-bundle",
        "albu-mcp evidence replay-fixture-pack",
        "albu-mcp evidence session-manifest",
        "albu-mcp evidence validate-manifest",
        "albu-mcp evidence proof-runner",
        "albu-mcp evidence import-checklist",
        "albu-mcp evidence proof-status",
        "albu-mcp evidence transition-pack",
        "albu-mcp evidence rc-unblock-preview",
        "albu-mcp evidence transcript-template",
        "albu-mcp evidence validate-import",
        "albu-mcp evidence import-artifacts",
        "albu-mcp evidence privacy-doctor",
        "albu-mcp evidence artifact-doctor",
        "albu-mcp evidence unblock-plan",
        "albu-mcp evidence doctor",
        "albu-mcp beta record-attempt",
        "albu-mcp beta report",
        "albu-mcp beta campaign-plan",
        "albu-mcp beta loop-pack",
        "albu-mcp beta trial-pack",
        "albu-mcp beta intake-wizard",
        "albu-mcp beta response-validate",
        "albu-mcp beta response-import",
        "albu-mcp beta response-import-dir",
        "albu-mcp beta response-template",
        "albu-mcp rc reopen",
        "albu-mcp rc rehearse",
        "albu-mcp rc candidate-packet",
        "albu-mcp rc release-owner-packet",
        "albu-mcp rc review-pack",
        "albu-mcp rc go-check",
        "albu-mcp distribution readiness",
        "albu-mcp trust audit",
        "albu-mcp trust next",
        "albu-mcp trust dashboard",
        "albu-mcp trust gate-transition",
        "`plan_augmentation_policy`",
        "`plan_policy_iteration`",
    ]

    for expected in readme_expected:
        assert expected in readme
    for expected in usage_expected:
        assert expected in usage
