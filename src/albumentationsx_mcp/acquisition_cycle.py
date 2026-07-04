"""No-write real evidence and beta acquisition cycle helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import build_beta_validation_report, validate_beta_validation_records
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.evidence_proof import build_evidence_proof_status


@dataclass(frozen=True)
class AcquisitionCycleRequest:
    """Inputs for a no-write real evidence and beta acquisition cycle."""

    host: HostName
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_acquisition_cycle(request: AcquisitionCycleRequest) -> dict[str, Any]:
    """Build one no-write acquisition cycle over real host and beta gates."""
    proof_status = build_evidence_proof_status(records_path=request.host_records_path)
    beta_report = build_beta_validation_report(validate_beta_validation_records(request.beta_records_path))
    lanes = [
        _real_evidence_acquisition_lane(request=request, proof_status=proof_status),
        _beta_acquisition_lane(beta_report=beta_report),
        _product_depth_gate_lane(),
    ]
    blocked = any(lane["status"].startswith("blocked") for lane in lanes)
    return {
        "cycle_status": "blocked" if blocked else "ready_for_product_depth",
        "writes_records": False,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "lane_count": len(lanes),
        "lanes": lanes,
        "next_action": "run_real_evidence_acquisition" if blocked else "run_product_depth_gate",
        "non_fabrication_policy": (
            "This cycle is report-only. Generated packets, templates, transcripts, and fixture output do not count "
            "as P0 host evidence or external beta validation."
        ),
    }


def _real_evidence_acquisition_lane(
    *,
    request: AcquisitionCycleRequest,
    proof_status: dict[str, Any],
) -> dict[str, Any]:
    blocked = proof_status["status"] != "ready_for_rc_reopen"
    return {
        "id": "real_evidence_acquisition",
        "title": "Real evidence acquisition",
        "status": "blocked_until_real_host_evidence" if blocked else "ready_for_gate_transition",
        "writes_records": False,
        "host": request.host,
        "proof_status": proof_status["status"],
        "blocked_host_count": proof_status["blocked_host_count"],
        "next_commands": [
            "albu-mcp evidence transcript-template",
            "albu-mcp evidence proof-runner",
            "albu-mcp evidence import-manifest",
        ],
    }


def _beta_acquisition_lane(*, beta_report: dict[str, Any]) -> dict[str, Any]:
    blocked = not beta_report["product_depth_allowed"]
    return {
        "id": "beta_acquisition",
        "title": "Beta acquisition",
        "status": "blocked_until_beta_validation" if blocked else "ready_for_product_depth_gate",
        "writes_records": False,
        "summary": beta_report["summary"],
    }


def _product_depth_gate_lane() -> dict[str, Any]:
    return {
        "id": "product_depth_gate",
        "title": "Product depth gate",
        "status": "blocked_until_external_gates",
        "implementation_allowed": False,
        "writes_records": False,
    }
