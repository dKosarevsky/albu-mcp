"""No-write real evidence execution cockpit helpers."""

from __future__ import annotations

import json
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


def build_evidence_cockpit_artifacts(
    request: EvidenceCockpitRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build no-write cockpit artifacts for one real evidence run."""
    report = build_evidence_cockpit(request)
    artifacts = [
        _cockpit_index_artifact(report=report, output_format=output_format),
        *[_cockpit_phase_artifact(phase=phase, output_format=output_format) for phase in report["phases"]],
    ]
    return {
        "pack_status": report["cockpit_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_evidence_cockpit_markdown(report: dict[str, Any]) -> str:
    """Render the cockpit index as Markdown."""
    return _render_cockpit_index_markdown(report)


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
        "goal": ("Prepare privacy-safe reviewer notes and a manifest template for Reviewer-observed real MCP host UI."),
        "next_commands": [
            "albu-mcp evidence transcript-template",
            f"albu-mcp evidence session-manifest --host {request.host} --date YYYY-MM-DD --reviewer 'Release operator'",
            f"albu-mcp evidence session-folder --host {request.host} --date YYYY-MM-DD --reviewer 'Release operator'",
        ],
    }


def _cockpit_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    return {
        "filename": f"evidence-cockpit-index.{_extension(output_format)}",
        "content": _json_dumps(report) if output_format == "json" else _render_cockpit_index_markdown(report),
    }


def _cockpit_phase_artifact(*, phase: dict[str, Any], output_format: str) -> dict[str, str]:
    return {
        "filename": f"{phase['id'].replace('_', '-')}.{_extension(output_format)}",
        "content": _json_dumps(phase) if output_format == "json" else _render_phase_markdown(phase),
    }


def _render_cockpit_index_markdown(report: dict[str, Any]) -> str:
    phases = "\n".join(
        f"- `{phase['id']}`: `{phase['status']}`; writes_records=`{str(phase['writes_records']).lower()}`"
        for phase in report["phases"]
    )
    return (
        "# Real Evidence Execution Cockpit\n\n"
        f"Release tag: `{report['release_tag']}`\n\n"
        f"Host: `{report['host']}`\n\n"
        f"Cockpit status: `{report['cockpit_status']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Next action: `{report['next_action']}`\n\n"
        "## Phases\n\n"
        f"{phases}\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{report['non_fabrication_policy']}\n"
    )


def _render_phase_markdown(phase: dict[str, Any]) -> str:
    commands = "\n".join(f"- `{command}`" for command in phase.get("next_commands", [])) or "- none"
    return (
        f"# {phase['title']}\n\n"
        f"Phase id: `{phase['id']}`\n\n"
        f"Status: `{phase['status']}`\n\n"
        f"Writes records: `{str(phase['writes_records']).lower()}`\n\n"
        "## Goal\n\n"
        f"{phase['goal']}\n\n"
        "## Next Commands\n\n"
        f"{commands}\n"
    )


def _extension(output_format: str) -> str:
    if output_format == "markdown":
        return "md"
    if output_format == "json":
        return "json"
    msg = f"unsupported evidence cockpit format: {output_format}"
    raise ValueError(msg)


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


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
