"""No-write real adoption cycle helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import build_beta_validation_report, validate_beta_validation_records
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.evidence_proof import build_evidence_proof_status


@dataclass(frozen=True)
class RealAdoptionCycleRequest:
    """Inputs for one no-write real adoption cycle."""

    host: HostName
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_real_adoption_cycle(request: RealAdoptionCycleRequest) -> dict[str, Any]:
    """Build one no-write adoption cycle over real host and beta evidence gates."""
    proof_status = build_evidence_proof_status(records_path=request.host_records_path)
    beta_report = build_beta_validation_report(validate_beta_validation_records(request.beta_records_path))
    blocked_reasons = _blocked_reasons(proof_status=proof_status, beta_report=beta_report)
    lanes = [
        _real_evidence_intake_lane(request=request, proof_status=proof_status),
        _beta_signal_sprint_lane(beta_report=beta_report),
        _first_product_fix_gate_lane(blocked_reasons=blocked_reasons, beta_report=beta_report),
    ]
    return {
        "cycle_status": "blocked" if blocked_reasons else "ready_for_first_product_fix",
        "writes_records": False,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "lane_count": len(lanes),
        "lanes": lanes,
        "next_action": "collect_real_evidence_and_beta_signal" if blocked_reasons else "select_first_product_fix",
        "non_fabrication_policy": (
            "No generated packet, fixture, smoke output, transcript template, or report-only artifact is counted as "
            "real host evidence or external beta validation. First product fixes stay blocked until external records "
            "exist."
        ),
    }


def render_real_adoption_cycle_markdown(report: dict[str, Any]) -> str:
    """Render the real adoption cycle as Markdown."""
    lanes = "\n".join(
        f"- `{lane['id']}`: `{lane['status']}`; writes_records=`{str(lane['writes_records']).lower()}`"
        for lane in report["lanes"]
    )
    return (
        "# Real Adoption Cycle\n\n"
        f"Release tag: `{report['release_tag']}`\n\n"
        f"Host: `{report['host']}`\n\n"
        f"Cycle status: `{report['cycle_status']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Next action: `{report['next_action']}`\n\n"
        "## Lanes\n\n"
        f"{lanes}\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{report['non_fabrication_policy']}\n"
    )


def _real_evidence_intake_lane(
    *,
    request: RealAdoptionCycleRequest,
    proof_status: dict[str, Any],
) -> dict[str, Any]:
    blocked = proof_status["status"] != "ready_for_rc_reopen"
    return {
        "id": "real_evidence_intake",
        "title": "Real evidence intake",
        "status": "blocked_until_real_host_evidence" if blocked else "ready",
        "writes_records": False,
        "proof_status": proof_status["status"],
        "blocked_host_count": proof_status["blocked_host_count"],
        "blocked_reasons": ["p0_host_evidence_missing_or_blocked"] if blocked else [],
        "next_commands": [
            f"albu-mcp activation evidence-cockpit --host {request.host} --output-dir docs/evidence-cockpit "
            "--format markdown",
            "albu-mcp evidence proof-runner --input docs/operator-packets/codex-evidence-session-manifest.json "
            "--format json",
            "albu-mcp evidence import-manifest --input docs/operator-packets/codex-evidence-session-manifest.json "
            "--format json",
        ],
    }


def _beta_signal_sprint_lane(*, beta_report: dict[str, Any]) -> dict[str, Any]:
    blocked_reason = _beta_blocked_reason(beta_report)
    return {
        "id": "beta_signal_sprint",
        "title": "Beta signal sprint",
        "status": "blocked_until_beta_signal" if blocked_reason else "ready",
        "writes_records": False,
        "privacy_status": beta_report["privacy_status"],
        "summary": beta_report["summary"],
        "blocked_reasons": [blocked_reason] if blocked_reason else [],
        "next_commands": [
            "albu-mcp beta loop-pack --output-dir docs/beta-loop --format markdown",
            "albu-mcp beta response-template --output-dir docs/beta-response-templates --format json",
            "albu-mcp beta response-import-dir --input-dir docs/beta-response-templates --format json",
        ],
    }


def _first_product_fix_gate_lane(*, blocked_reasons: list[str], beta_report: dict[str, Any]) -> dict[str, Any]:
    implementation_allowed = not blocked_reasons
    return {
        "id": "first_product_fix_gate",
        "title": "First product fix gate",
        "status": "ready_for_first_product_fix" if implementation_allowed else "blocked_until_external_evidence",
        "writes_records": False,
        "implementation_allowed": implementation_allowed,
        "blocked_reasons": blocked_reasons,
        "candidate_backlog_item_count": beta_report["summary"]["candidate_backlog_item_count"],
        "next_commands": [
            "albu-mcp activation real-adoption-cycle --host Codex --format json",
            "albu-mcp activation evidence-product-loop --host Codex --format json",
            "albu-mcp beta triage --format json",
        ],
    }


def _blocked_reasons(*, proof_status: dict[str, Any], beta_report: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if proof_status["status"] != "ready_for_rc_reopen":
        reasons.append("p0_host_evidence_missing_or_blocked")
    beta_reason = _beta_blocked_reason(beta_report)
    if beta_reason is not None:
        reasons.append(beta_reason)
    return reasons


def _beta_blocked_reason(beta_report: dict[str, Any]) -> str | None:
    if beta_report["product_depth_allowed"]:
        return None
    if beta_report["summary"]["record_count"] == 0:
        return "beta_validation_records_missing"
    return "beta_validation_incomplete"
