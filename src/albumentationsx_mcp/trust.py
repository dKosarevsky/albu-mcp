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


def build_trust_next_action(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
) -> dict[str, Any]:
    """Return the single next safest operator action across trust gates."""
    audit = build_trust_audit_report(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    evidence_ready = audit["evidence"]["plan_status"] == "ready_for_rc_reopen"
    beta_ready = audit["beta"]["product_depth_allowed"]
    distribution_ready = audit["distribution"]["publish_allowed"]
    if not evidence_ready:
        first_blocker = audit["evidence"]["first_blocker"] or {"host": "Codex"}
        host = first_blocker["host"]
        return _next_action_payload(
            blocked_gate="p0_host_evidence",
            reason_code="p0_host_evidence_missing_or_blocked",
            recommended_command=f"albu-mcp evidence execution-packet --host {host} --format json",
            follow_up_command="albu-mcp evidence artifact-doctor --format json",
            audit=audit,
        )
    if not beta_ready:
        return _next_action_payload(
            blocked_gate="beta_validation",
            reason_code="beta_validation_records_missing",
            recommended_command="albu-mcp beta trial-pack --workflow-id noisy_preview_tuning --format json",
            follow_up_command="albu-mcp beta campaign-plan --format json",
            audit=audit,
        )
    if not distribution_ready:
        return _next_action_payload(
            blocked_gate="rc_reopen",
            reason_code="rc_reopen_not_allowed",
            recommended_command="albu-mcp rc rehearse --format json",
            follow_up_command="albu-mcp distribution readiness --format json",
            audit=audit,
        )
    return {
        "next_status": "ready",
        "blocked_gate": None,
        "reason_code": "all_trust_gates_ready",
        "recommended_command": "albu-mcp rc rehearse --format json",
        "follow_up_command": "albu-mcp distribution readiness --format json",
        "trust_score": audit["trust_score"],
        "execution_policy": "report_only",
    }


def build_trust_dashboard_report(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
) -> dict[str, Any]:
    """Build one operator-facing trust dashboard without mutating gates."""
    audit = build_trust_audit_report(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    next_action = build_trust_next_action(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    blocked_reasons = [] if next_action["reason_code"] == "all_trust_gates_ready" else [next_action["reason_code"]]
    return {
        "dashboard_status": audit["audit_status"],
        "release_tag": release_tag,
        "trust_score": audit["trust_score"],
        "execution_policy": "Report only; this dashboard does not tag, publish, or write evidence records.",
        "gate_cards": _dashboard_gate_cards(audit),
        "blocked_reasons": blocked_reasons,
        "recommended_command": next_action["recommended_command"],
        "follow_up_command": next_action["follow_up_command"],
    }


def render_trust_dashboard_markdown(report: dict[str, Any]) -> str:
    """Render a trust dashboard report as concise markdown."""
    rows = "\n".join(
        f"| `{card['gate']}` | `{card['status']}` | {card['detail']} |" for card in report["gate_cards"]
    )
    blocked = "\n".join(f"- `{reason}`" for reason in report["blocked_reasons"]) or "- none"
    return (
        "# AlbumentationsX MCP Trust Dashboard\n\n"
        f"Release tag: `{report['release_tag']}`\n\n"
        f"Dashboard status: `{report['dashboard_status']}`\n\n"
        f"Trust score: `{report['trust_score']}`\n\n"
        f"Execution policy: {report['execution_policy']}\n\n"
        "| Gate | Status | Detail |\n"
        "| --- | --- | --- |\n"
        f"{rows}\n\n"
        "## Blocked Reasons\n\n"
        f"{blocked}\n\n"
        "## Next Command\n\n"
        "```bash\n"
        f"{report['recommended_command']}\n"
        "```\n\n"
        "## Follow-Up Command\n\n"
        "```bash\n"
        f"{report['follow_up_command']}\n"
        "```\n"
    )


def _recommended_next_command(*, evidence_ready: bool, beta_ready: bool, distribution_ready: bool) -> str:
    if not evidence_ready:
        return "albu-mcp evidence unblock-plan --format json"
    if not beta_ready:
        return "albu-mcp beta campaign-plan --format json"
    if not distribution_ready:
        return "albu-mcp rc reopen --format json"
    return "albu-mcp distribution readiness --format json"


def _dashboard_gate_cards(audit: dict[str, Any]) -> list[dict[str, str]]:
    evidence = audit["evidence"]
    beta = audit["beta"]
    beta_summary = beta.get("summary", {})
    covered_workflow_count = beta_summary.get("covered_workflow_count", 0)
    workflow_count = beta_summary.get("workflow_count", beta["workflow_trial_count"])
    distribution = audit["distribution"]
    evidence_summary = evidence["first_blocker"] or {"host": "none"}
    return [
        {
            "gate": "p0_host_evidence",
            "status": "ready" if evidence["plan_status"] == "ready_for_rc_reopen" else "blocked",
            "detail": (
                f"{evidence['blocked_host_count']} blocked host(s); "
                f"first blocker `{evidence_summary['host']}`"
            ),
        },
        {
            "gate": "beta_validation",
            "status": "ready" if beta["product_depth_allowed"] else "blocked",
            "detail": (
                f"{covered_workflow_count}/{workflow_count} workflows covered"
            ),
        },
        {
            "gate": "distribution",
            "status": "ready" if distribution["publish_allowed"] else "blocked",
            "detail": f"publish_allowed=`{str(distribution['publish_allowed']).lower()}`",
        },
    ]


def _next_action_payload(
    *,
    blocked_gate: str,
    reason_code: str,
    recommended_command: str,
    follow_up_command: str,
    audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "next_status": "blocked",
        "blocked_gate": blocked_gate,
        "reason_code": reason_code,
        "recommended_command": recommended_command,
        "follow_up_command": follow_up_command,
        "trust_score": audit["trust_score"],
        "execution_policy": "report_only",
    }
