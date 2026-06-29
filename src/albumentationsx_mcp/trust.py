"""Unified trust audit for release and adoption gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import build_beta_campaign_plan, validate_beta_validation_records
from albumentationsx_mcp.distribution import build_distribution_readiness_report
from albumentationsx_mcp.evidence import build_evidence_unblock_plan

_READY_TRUST_SCORE = 100


def build_trust_audit_report(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
) -> dict[str, Any]:
    """Build one report-only trust audit across evidence, beta, and distribution gates."""
    evidence = build_evidence_unblock_plan(host_records_path)
    beta = build_beta_campaign_plan(validate_beta_validation_records(beta_records_path))
    distribution = build_distribution_readiness_report(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    passed_checks = sum(
        [
            evidence["plan_status"] == "ready_for_rc_reopen",
            beta["product_depth_allowed"],
            distribution["publish_allowed"],
        ]
    )
    trust_score = round((passed_checks / 3) * 100)
    return {
        "audit_status": "ready" if trust_score == _READY_TRUST_SCORE else "action_required",
        "trust_score": trust_score,
        "execution_policy": "report_only",
        "evidence": evidence,
        "beta": beta,
        "distribution": distribution,
        "recommended_next_command": _recommended_next_command(
            evidence_ready=evidence["plan_status"] == "ready_for_rc_reopen",
            beta_ready=beta["product_depth_allowed"],
            distribution_ready=distribution["publish_allowed"],
        ),
    }


def _recommended_next_command(*, evidence_ready: bool, beta_ready: bool, distribution_ready: bool) -> str:
    if not evidence_ready:
        return "albu-mcp evidence unblock-plan --format json"
    if not beta_ready:
        return "albu-mcp beta campaign-plan --format json"
    if not distribution_ready:
        return "albu-mcp rc reopen --format json"
    return "albu-mcp distribution readiness --format json"
