"""No-write product development cycles over external evidence gates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import build_beta_validation_report, validate_beta_validation_records
from albumentationsx_mcp.distribution import build_distribution_readiness_report
from albumentationsx_mcp.evidence import HostName, build_evidence_close_host_report
from albumentationsx_mcp.proof_sprint import OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL, build_real_proof_run_1
from albumentationsx_mcp.trust import build_trust_gate_transition_report


@dataclass(frozen=True)
class EvidenceFirstCycleRequest:
    """Inputs for one no-write evidence-first product cycle."""

    host: HostName
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    before_host_records_path: Path | None = None
    before_beta_records_path: Path | None = None
    release_tag: str = "v1.15.0-rc.1"


def build_evidence_first_cycle(request: EvidenceFirstCycleRequest) -> dict[str, Any]:
    """Build one no-write product cycle for the next real evidence push."""
    before_host = request.before_host_records_path or request.host_records_path
    before_beta = request.before_beta_records_path or request.beta_records_path
    evidence = build_evidence_close_host_report(host=request.host, path=request.host_records_path)
    beta = build_beta_validation_report(validate_beta_validation_records(request.beta_records_path))
    gate_transition = build_trust_gate_transition_report(
        before_host_records_path=before_host,
        before_beta_records_path=before_beta,
        after_host_records_path=request.host_records_path,
        after_beta_records_path=request.beta_records_path,
        release_tag=request.release_tag,
    )
    distribution = build_distribution_readiness_report(
        host_records_path=request.host_records_path,
        beta_records_path=request.beta_records_path,
        release_tag=request.release_tag,
    )
    real_proof_run = build_real_proof_run_1(
        host_records_path=request.host_records_path,
        beta_records_path=request.beta_records_path,
        release_tag=request.release_tag,
    )
    external_gates_open = evidence["closure_status"] == "closed" and beta["product_depth_allowed"]
    tracks = [
        _evidence_first_result_track(host=request.host, evidence=evidence),
        _beta_acquisition_loop_track(beta),
        _gate_transition_release_readiness_track(gate_transition=gate_transition),
        _p1_host_onboarding_gate_track(real_proof_run=real_proof_run, implementation_allowed=external_gates_open),
        _distribution_adoption_handoff_track(distribution=distribution),
    ]
    blocked = any(track["status"].startswith("blocked") for track in tracks)
    return {
        "cycle_status": "blocked" if blocked else "ready",
        "writes_records": False,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "before_host_records_path": str(before_host),
        "before_beta_records_path": str(before_beta),
        "track_count": len(tracks),
        "tracks": tracks,
        "next_action": "run_evidence_first_result_pack" if blocked else "run_distribution_readiness",
        "non_fabrication_policy": (
            "Generated evidence-first-cycle files do not count as evidence. Only reviewer-observed real MCP host "
            "sessions and privacy-safe external beta attempts may close the remaining gates."
        ),
        "source_docs": [
            "docs/GOVERNED_100_ITERATION_REPORT.md",
            "docs/USAGE.md",
            "docs/P0_EVIDENCE_IMPORT_GUIDE.md",
            "docs/BETA_VALIDATION_SPRINT.md",
            "docs/HOST_ONBOARDING_DEPTH_PLAN.md",
            OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL,
        ],
    }


def _evidence_first_result_track(*, host: HostName, evidence: dict[str, Any]) -> dict[str, Any]:
    status = (
        "ready_for_gate_transition" if evidence["closure_status"] == "closed" else "blocked_until_real_host_evidence"
    )
    return {
        "id": "evidence_first_result_pack",
        "title": "Evidence-first result pack",
        "status": status,
        "implementation_allowed": False,
        "writes_records": False,
        "goal": "Turn one reviewer-observed real MCP host session into validated import commands.",
        "success_signal": "The selected host has both P0 gates closed from real reviewer-observed evidence.",
        "host": host,
        "current_closure_status": evidence["closure_status"],
        "next_commands": [
            f"albu-mcp evidence session-folder --host {host}",
            "albu-mcp evidence validate-manifest --input docs/operator-packets/codex-evidence-session-manifest.json",
            "albu-mcp evidence import-manifest --input docs/operator-packets/codex-evidence-session-manifest.json",
            f"albu-mcp evidence close-host --host {host} --format json",
        ],
        "source_links": [
            "docs/P0_EVIDENCE_IMPORT_GUIDE.md",
            "docs/HOST_EVIDENCE_CAPTURE_KIT.md",
            OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL,
        ],
    }


def _beta_acquisition_loop_track(beta: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "beta_acquisition_loop",
        "title": "Beta acquisition loop",
        "status": "ready_for_depth_gate" if beta["product_depth_allowed"] else "blocked_until_beta_validation",
        "implementation_allowed": False,
        "writes_records": False,
        "goal": "Collect privacy-safe external beta responses through official docs and import templates.",
        "success_signal": "Every required beta workflow has at least one non-blocked external validation attempt.",
        "summary": beta["summary"],
        "next_commands": [
            "albu-mcp beta loop-pack --output-dir docs/beta-loop --format markdown",
            "albu-mcp beta response-import-dir --input-dir docs/beta-loop --format json",
            "albu-mcp beta report --format json",
        ],
        "source_links": [
            "docs/BETA_VALIDATION_SPRINT.md",
            "docs/BETA_FEEDBACK_INTAKE.md",
            OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL,
        ],
    }


def _gate_transition_release_readiness_track(*, gate_transition: dict[str, Any]) -> dict[str, Any]:
    ready = gate_transition["transition_status"] == "ready_for_rc_reopen"
    return {
        "id": "gate_transition_release_readiness",
        "title": "Gate transition and release readiness",
        "status": "ready_for_release_owner_review" if ready else "blocked_until_gate_transition",
        "implementation_allowed": False,
        "writes_records": False,
        "goal": "Compare before/after gate records and expose the next release-readiness command.",
        "success_signal": "Trust gate transition reports ready_for_rc_reopen with no newly blocked gates.",
        "transition_status": gate_transition["transition_status"],
        "rc_progress_status": gate_transition["rc_progress_status"],
        "next_commands": [
            (
                "albu-mcp trust gate-transition --before-host-records docs/HOST_MANUAL_RUNS.json "
                "--before-beta-records docs/BETA_VALIDATION_RECORDS.json "
                "--after-host-records docs/HOST_MANUAL_RUNS.json "
                "--after-beta-records docs/BETA_VALIDATION_RECORDS.json --format markdown"
            ),
            "albu-mcp rc go-check --format markdown",
            "albu-mcp distribution readiness --format json",
        ],
        "source_links": [
            "docs/RC_RELEASE_DECISION_REPORT.md",
            "docs/V1_RC_RELEASE_PACKET.md",
            "docs/DISTRIBUTION_READINESS_PACK.md",
        ],
    }


def _p1_host_onboarding_gate_track(
    *,
    real_proof_run: dict[str, Any],
    implementation_allowed: bool,
) -> dict[str, Any]:
    return {
        "id": "p1_host_onboarding_gate",
        "title": "P1 host onboarding gate",
        "status": "ready_for_p1_depth" if implementation_allowed else "blocked_until_external_gates",
        "implementation_allowed": implementation_allowed,
        "writes_records": False,
        "goal": "Keep host-onboarding depth work behind real host evidence and beta validation gates.",
        "success_signal": "External gates are open before setup recovery UX depth starts.",
        "real_proof_run_status": real_proof_run["run_status"],
        "next_commands": [
            "albu-mcp activation evidence-first-cycle --host Codex --format json",
            "albu-mcp host setup-probe --host Codex --live --format json",
            "albu-mcp trust dashboard --format markdown",
        ],
        "source_links": [
            "docs/HOST_ONBOARDING_DEPTH_PLAN.md",
            "docs/HOST_FAILURE_COOKBOOK.md",
            "docs/PRODUCT_DEPTH_GATE.md",
        ],
    }


def _distribution_adoption_handoff_track(*, distribution: dict[str, Any]) -> dict[str, Any]:
    publish_allowed = bool(distribution["publish_allowed"])
    return {
        "id": "distribution_adoption_handoff",
        "title": "Distribution and adoption handoff",
        "status": "ready_for_public_distribution" if publish_allowed else "blocked_until_release_gates",
        "implementation_allowed": False,
        "writes_records": False,
        "publish_allowed": publish_allowed,
        "goal": "Prepare public distribution surfaces only after release gates open.",
        "success_signal": (
            "PyPI, GitHub release, MCP Registry, and upstream Albumentations docs can be updated together."
        ),
        "channels": distribution["channels"],
        "next_commands": [
            "albu-mcp distribution readiness --format json",
            "albu-mcp rc release-owner-packet --format markdown",
            "gh release create <tag> --notes-file docs/release-notes.md",
        ],
        "source_links": [
            "README.md",
            "docs/INSTALL.md",
            "docs/V1_LAUNCH_REPORT.md",
            OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL,
        ],
    }
