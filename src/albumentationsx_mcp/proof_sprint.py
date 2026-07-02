"""Combined proof sprint orchestration for external evidence gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from albumentationsx_mcp.activation import build_activation_command_center
from albumentationsx_mcp.beta_validation import build_beta_validation_report, validate_beta_validation_records
from albumentationsx_mcp.host_setup import build_host_setup_probe

OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL = "https://albumentations.ai/docs/integrations/mcp/"


def build_combined_proof_sprint(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
) -> dict[str, Any]:
    """Build one report-only sprint over the remaining external proof gates."""
    command_center = build_activation_command_center(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    beta_report = build_beta_validation_report(validate_beta_validation_records(beta_records_path))
    host_probe = build_host_setup_probe()
    p0_blocked = "p0_host_evidence_missing_or_blocked" in command_center["rc_candidate"]["blocked_reasons"]
    beta_blocked = not beta_report["product_depth_allowed"]
    host_depth_allowed = not p0_blocked and not beta_blocked
    points = [
        _real_host_evidence_point(blocked=p0_blocked),
        _beta_validation_point(blocked=beta_blocked, beta_report=beta_report),
        _host_onboarding_depth_point(implementation_allowed=host_depth_allowed, host_probe=host_probe),
    ]
    blocked = any(point["status"].startswith("blocked") for point in points)
    return {
        "sprint_status": "blocked" if blocked else "ready",
        "writes_records": False,
        "release_tag": release_tag,
        "host_records_path": str(host_records_path),
        "beta_records_path": str(beta_records_path),
        "point_count": len(points),
        "points": points,
        "next_action": "collect_real_host_and_beta_evidence" if blocked else "run_rc_go_check",
        "non_fabrication_policy": (
            "Generated proof sprint packets do not count as P0 host evidence or beta validation records. "
            "Only reviewer-observed real MCP host UI sessions and redacted external beta attempts may close gates."
        ),
        "source_docs": [
            "docs/GOVERNED_100_ITERATION_REPORT.md",
            "docs/HOST_ONBOARDING_DEPTH_PLAN.md",
            "docs/BETA_VALIDATION_SPRINT.md",
            "docs/P0_EVIDENCE_IMPORT_GUIDE.md",
            OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL,
        ],
    }


def _real_host_evidence_point(*, blocked: bool) -> dict[str, Any]:
    return {
        "id": "real_host_evidence_sprint",
        "title": "Real host evidence sprint",
        "status": "blocked_until_real_host_evidence" if blocked else "ready",
        "implementation_allowed": False,
        "goal": "Close P0 host evidence with reviewer-observed MCP host UI sessions.",
        "success_signal": "Codex and Claude Code have passed manual_host_ui and first_10_minutes_replay records.",
        "next_commands": [
            "albu-mcp evidence session-folder",
            "albu-mcp evidence import-manifest",
            "albu-mcp evidence close-host",
        ],
        "source_links": [
            "docs/P0_EVIDENCE_IMPORT_GUIDE.md",
            "docs/HOST_EVIDENCE_CAPTURE_KIT.md",
            OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL,
        ],
    }


def _beta_validation_point(*, blocked: bool, beta_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "beta_validation_sprint",
        "title": "Beta validation sprint",
        "status": "blocked_until_beta_validation" if blocked else "ready",
        "implementation_allowed": False,
        "goal": "Collect privacy-safe external attempts from all required beta workflows.",
        "success_signal": "Every beta workflow has at least one redacted non-blocked validation record.",
        "summary": beta_report["summary"],
        "next_commands": [
            "albu-mcp beta loop-pack",
            "albu-mcp beta response-import-dir",
            "albu-mcp beta report",
        ],
        "source_links": [
            "docs/BETA_VALIDATION_SPRINT.md",
            "docs/BETA_FEEDBACK_INTAKE.md",
            OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL,
        ],
    }


def _host_onboarding_depth_point(*, implementation_allowed: bool, host_probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "host_onboarding_depth",
        "title": "Host onboarding depth",
        "status": "ready_for_depth_plan" if implementation_allowed else "blocked_until_p0_and_beta_gates",
        "implementation_allowed": implementation_allowed,
        "goal": "Improve setup recovery only after real host and beta evidence identify repeated setup gaps.",
        "success_signal": "A beta user can recover from setup failure without maintainer intervention.",
        "probe_summary": host_probe["summary"],
        "next_commands": [
            "albu-mcp host setup-probe",
            "albu-mcp evidence collect",
            "albu-mcp activation proof-sprint",
        ],
        "source_links": [
            "docs/HOST_ONBOARDING_DEPTH_PLAN.md",
            "docs/HOST_FAILURE_COOKBOOK.md",
            "docs/P0_HOST_UNBLOCK_PACK.md",
        ],
    }
