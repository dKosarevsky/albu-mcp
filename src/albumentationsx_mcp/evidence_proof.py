"""No-write evidence proof-loop orchestration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.evidence import (
    P0_REQUIRED_HOSTS,
    EvidenceSessionManifest,
    HostName,
    build_evidence_close_host_report,
    load_evidence_session_manifest,
    validate_evidence_session_manifest,
)


@dataclass(frozen=True)
class EvidenceProofRequest:
    """Inputs for one no-write evidence proof runner."""

    manifest_path: Path
    records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")


def build_evidence_proof_runner(request: EvidenceProofRequest) -> dict[str, Any]:
    """Build a no-write proof runner for one filled evidence session manifest."""
    manifest = load_evidence_session_manifest(request.manifest_path)
    validation = validate_evidence_session_manifest(manifest=manifest, records_path=request.records_path)
    return {
        "runner_status": validation["validation_status"],
        "writes_records": False,
        "host": manifest.host,
        "records_path": str(request.records_path),
        "manifest_path": str(request.manifest_path),
        "manifest": _manifest_summary(manifest),
        "manifest_validation": validation,
        "next_commands": _proof_runner_next_commands(request=request, manifest=manifest),
        "non_fabrication_policy": (
            "The proof runner validates and sequences commands only. It does not write P0 evidence records; "
            "only evidence import-manifest writes records after reviewer-observed real host evidence is confirmed."
        ),
    }


def build_evidence_proof_status(*, records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")) -> dict[str, Any]:
    """Build a no-write status report for required P0 host evidence gates."""
    hosts = [_proof_status_host(host=host, records_path=records_path) for host in P0_REQUIRED_HOSTS]
    blocked_hosts = [host for host in hosts if host["closure_status"] != "closed"]
    return {
        "status": "blocked" if blocked_hosts else "ready_for_rc_reopen",
        "writes_records": False,
        "records_path": str(records_path),
        "required_hosts": list(P0_REQUIRED_HOSTS),
        "host_count": len(hosts),
        "blocked_host_count": len(blocked_hosts),
        "hosts": hosts,
        "next_action": ("run_proof_runner_for_first_blocked_host" if blocked_hosts else "run_trust_gate_transition"),
        "non_fabrication_policy": (
            "Proof status reads host evidence records only. It does not mark generated files or synthetic smoke output "
            "as P0 evidence."
        ),
    }


def _manifest_summary(manifest: EvidenceSessionManifest) -> dict[str, Any]:
    return {
        "manifest_status": manifest.manifest_status,
        "host": manifest.host,
        "status": manifest.status,
        "date": manifest.date.isoformat(),
        "reviewer": manifest.reviewer,
        "artifact_count": len(manifest.artifacts),
        "command_count": len(manifest.commands_used),
        "confirm_real_host_observed": manifest.confirm_real_host_observed,
    }


def _proof_runner_next_commands(
    *,
    request: EvidenceProofRequest,
    manifest: EvidenceSessionManifest,
) -> list[str]:
    return [
        (
            f"albu-mcp evidence validate-manifest --input {request.manifest_path} "
            f"--path {request.records_path} --format json"
        ),
        (
            f"albu-mcp evidence import-manifest --input {request.manifest_path} "
            f"--path {request.records_path} --format json"
        ),
        f"albu-mcp evidence close-host --host {manifest.host} --path {request.records_path} --format json",
        (
            "albu-mcp trust gate-transition "
            f"--before-host-records {request.records_path} --before-beta-records {request.beta_records_path} "
            f"--after-host-records {request.records_path} --after-beta-records {request.beta_records_path} "
            "--format markdown"
        ),
    ]


def _proof_status_host(*, host: HostName, records_path: Path) -> dict[str, Any]:
    report = build_evidence_close_host_report(host=host, path=records_path)
    return {
        "host": report["host"],
        "closure_status": report["closure_status"],
        "missing_gates": report["missing_gates"],
        "current_host_status": report["current_host_status"],
        "next_commands": report["next_commands"],
    }
