"""No-write real evidence execution cockpit helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.evidence_proof import build_evidence_proof_status


@dataclass(frozen=True)
class EvidenceCockpitRequest:
    """Inputs for one no-write real evidence execution cockpit."""

    host: HostName
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_evidence_cockpit(request: EvidenceCockpitRequest) -> dict[str, Any]:
    """Build one no-write cockpit for a reviewer-observed host evidence run."""
    proof_status = build_evidence_proof_status(records_path=request.host_records_path)
    phases = [
        _setup_probe_phase(request),
        _session_capture_phase(request),
        _manifest_import_phase(request),
        _post_import_review_phase(request, proof_status=proof_status),
    ]
    blocked = proof_status["status"] != "ready_for_rc_reopen"
    return {
        "cockpit_status": "blocked" if blocked else "ready_for_rc_reopen",
        "writes_records": False,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "phase_count": len(phases),
        "phases": phases,
        "next_action": "run_setup_probe" if blocked else "run_transition_pack",
        "non_fabrication_policy": (
            "The cockpit only sequences commands and writes optional generated handoffs. It does not record P0 "
            "evidence; import commands must be run only after reviewer-observed real MCP host UI evidence exists."
        ),
    }


def _setup_probe_phase(request: EvidenceCockpitRequest) -> dict[str, Any]:
    return {
        "id": "setup_probe",
        "title": "Setup probe",
        "status": "ready_to_run",
        "writes_records": False,
        "goal": "Verify the selected MCP host can see the local server and allowed roots before evidence capture.",
        "next_commands": [
            f"albu-mcp host setup-probe --host {request.host} --live --format json",
            "albu-mcp activation acquisition-cycle --host Codex --format json",
        ],
    }


def _session_capture_phase(request: EvidenceCockpitRequest) -> dict[str, Any]:
    return {
        "id": "session_capture",
        "title": "Session capture",
        "status": "blocked_until_setup_probe",
        "writes_records": False,
        "goal": "Prepare privacy-safe reviewer notes and a manifest template for the real host session.",
        "next_commands": [
            "albu-mcp evidence transcript-template",
            f"albu-mcp evidence session-manifest --host {request.host} --date YYYY-MM-DD --reviewer 'Release operator'",
            f"albu-mcp evidence session-folder --host {request.host} --date YYYY-MM-DD --reviewer 'Release operator'",
        ],
    }


def _manifest_import_phase(request: EvidenceCockpitRequest) -> dict[str, Any]:
    return {
        "id": "manifest_import",
        "title": "Manifest import",
        "status": "blocked_until_reviewer_observed_real_host",
        "writes_records": False,
        "goal": "Validate and import a filled manifest only after real host evidence is observed by a reviewer.",
        "next_commands": [
            "albu-mcp evidence proof-runner",
            "albu-mcp evidence validate-manifest",
            "albu-mcp evidence import-manifest",
            f"albu-mcp evidence close-host --host {request.host} --format json",
        ],
    }


def _post_import_review_phase(
    request: EvidenceCockpitRequest,
    *,
    proof_status: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": "post_import_review",
        "title": "Post-import review",
        "status": "blocked_until_host_closed" if proof_status["status"] != "ready_for_rc_reopen" else "ready",
        "writes_records": False,
        "goal": "Review proof status, trust transition, and RC blockers after real evidence records change.",
        "proof_status": proof_status["status"],
        "blocked_host_count": proof_status["blocked_host_count"],
        "next_commands": [
            "albu-mcp evidence proof-status --format json",
            (
                f"albu-mcp evidence transition-pack --before-host-records {request.host_records_path} "
                f"--after-host-records {request.host_records_path} --beta-records {request.beta_records_path} "
                "--output-dir docs/operator-packets --format markdown"
            ),
            "albu-mcp evidence rc-unblock-preview --format json",
        ],
    }
