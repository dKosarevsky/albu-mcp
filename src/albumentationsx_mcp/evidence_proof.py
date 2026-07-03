"""No-write evidence proof-loop orchestration helpers."""

from __future__ import annotations

import json
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
from albumentationsx_mcp.rc_reopen import (
    build_rc_go_check_report,
    build_rc_reopen_report,
    render_rc_go_check_markdown,
)
from albumentationsx_mcp.trust import build_trust_gate_transition_report, render_trust_gate_transition_markdown


@dataclass(frozen=True)
class EvidenceProofRequest:
    """Inputs for one no-write evidence proof runner."""

    manifest_path: Path
    records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")


@dataclass(frozen=True)
class EvidenceTransitionPackRequest:
    """Inputs for a no-write trust transition and RC preview artifact pack."""

    before_host_records_path: Path
    after_host_records_path: Path
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"
    output_format: str = "markdown"


@dataclass(frozen=True)
class RcUnblockPreviewRequest:
    """Inputs for a no-write RC unblock preview."""

    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


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


def build_evidence_transition_pack_artifacts(request: EvidenceTransitionPackRequest) -> dict[str, Any]:
    """Build no-write trust transition and RC go-check preview artifacts."""
    transition = build_trust_gate_transition_report(
        before_host_records_path=request.before_host_records_path,
        before_beta_records_path=request.beta_records_path,
        after_host_records_path=request.after_host_records_path,
        after_beta_records_path=request.beta_records_path,
        release_tag=request.release_tag,
    )
    rc_go_check = build_rc_go_check_report(
        host_records_path=request.after_host_records_path,
        beta_records_path=request.beta_records_path,
        release_tag=request.release_tag,
    )
    artifacts = [
        {
            "filename": f"trust-transition-pack-index.{_artifact_extension(request.output_format)}",
            "content": _format_transition_pack_index(
                transition=transition,
                rc_go_check=rc_go_check,
                request=request,
            ),
        },
        {
            "filename": f"trust-gate-transition.{_artifact_extension(request.output_format)}",
            "content": _format_payload(
                payload=transition,
                markdown=render_trust_gate_transition_markdown(transition),
                output_format=request.output_format,
            ),
        },
        {
            "filename": f"rc-go-check-preview.{_artifact_extension(request.output_format)}",
            "content": _format_payload(
                payload=rc_go_check,
                markdown=render_rc_go_check_markdown(rc_go_check),
                output_format=request.output_format,
            ),
        },
    ]
    return {
        "pack_status": "ready",
        "writes_records": False,
        "release_tag": request.release_tag,
        "before_host_records_path": str(request.before_host_records_path),
        "after_host_records_path": str(request.after_host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "transition_status": transition["transition_status"],
        "rc_go_decision": rc_go_check["go_decision"],
        "publish_allowed": rc_go_check["publish_allowed"],
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "next_actions": _transition_pack_next_actions(request),
        "non_fabrication_policy": (
            "The transition pack is report-only. It does not import host evidence, write beta records, tag releases, "
            "publish packages, or treat generated artifacts as P0 evidence."
        ),
    }


def build_rc_unblock_preview(request: RcUnblockPreviewRequest) -> dict[str, Any]:
    """Build a no-write preview of remaining RC blockers and unlock commands."""
    proof_status = build_evidence_proof_status(records_path=request.host_records_path)
    rc_reopen = build_rc_reopen_report(
        host_records_path=request.host_records_path,
        beta_records_path=request.beta_records_path,
        release_tag=request.release_tag,
    )
    rc_go_check = build_rc_go_check_report(
        host_records_path=request.host_records_path,
        beta_records_path=request.beta_records_path,
        release_tag=request.release_tag,
    )
    publish_allowed = bool(rc_reopen["publish_allowed"])
    return {
        "preview_status": "ready_for_release_owner_review" if publish_allowed else "blocked",
        "writes_records": False,
        "release_tag": request.release_tag,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "publish_allowed": publish_allowed,
        "blocked_reasons": rc_reopen["blocked_reasons"],
        "proof_status": proof_status,
        "rc_reopen_decision": rc_reopen["rc_decision"],
        "rc_go_decision": rc_go_check["go_decision"],
        "release_owner_packet_status": rc_go_check["release_owner_packet_status"],
        "next_unlock_commands": _rc_unblock_next_unlock_commands(publish_allowed=publish_allowed),
        "release_readiness_command": "albu-mcp distribution readiness --format json",
        "execution_policy": (
            "Report only; this preview does not write evidence records, create tags, publish releases, or upload "
            "packages."
        ),
    }


def build_operator_transcript_template_artifact(
    *,
    host: HostName,
    output_format: str = "markdown",
) -> dict[str, str]:
    """Build a privacy-safe operator transcript template artifact."""
    payload = {
        "template_status": "ready",
        "writes_records": False,
        "host": host,
        "required_fields": [
            "Reviewer",
            "Session date",
            "Commands used",
            "Observed host behavior",
            "Artifacts attached",
            "Private data check",
        ],
        "privacy_note": (
            "Do not include private source images, private dataset paths, credentials, API keys, or unredacted "
            "participant logs."
        ),
        "evidence_policy": (
            "Generated transcript templates are not P0 evidence. Import only reviewer-observed real host evidence "
            "with confirm_real_host_observed=true."
        ),
    }
    slug = _host_slug(host)
    return {
        "filename": f"{slug}-operator-transcript-template.{_artifact_extension(output_format)}",
        "content": _format_payload(
            payload=payload,
            markdown=_render_operator_transcript_template_markdown(payload),
            output_format=output_format,
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


def _artifact_extension(output_format: str) -> str:
    if output_format == "markdown":
        return "md"
    if output_format == "json":
        return "json"
    msg = f"unsupported transition pack format: {output_format}"
    raise ValueError(msg)


def _format_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported transition pack format: {output_format}"
    raise ValueError(msg)


def _format_transition_pack_index(
    *,
    transition: dict[str, Any],
    rc_go_check: dict[str, Any],
    request: EvidenceTransitionPackRequest,
) -> str:
    payload = {
        "pack_status": "ready",
        "writes_records": False,
        "release_tag": request.release_tag,
        "transition_status": transition["transition_status"],
        "rc_go_decision": rc_go_check["go_decision"],
        "publish_allowed": rc_go_check["publish_allowed"],
        "before_host_records_path": str(request.before_host_records_path),
        "after_host_records_path": str(request.after_host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_actions": _transition_pack_next_actions(request),
        "artifacts": [
            "trust-gate-transition",
            "rc-go-check-preview",
        ],
    }
    if request.output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if request.output_format != "markdown":
        msg = f"unsupported transition pack format: {request.output_format}"
        raise ValueError(msg)

    next_actions = "\n".join(f"- `{command}`" for command in payload["next_actions"])
    return (
        "# Trust Transition Pack\n\n"
        f"Release tag: `{request.release_tag}`\n\n"
        "Writes records: `false`\n\n"
        f"Transition status: `{transition['transition_status']}`\n\n"
        f"RC go decision: `{rc_go_check['go_decision']}`\n\n"
        f"Before trust score: `{transition['before_trust_score']}`\n\n"
        f"After trust score: `{transition['after_trust_score']}`\n\n"
        "## Inputs\n\n"
        f"- Before host records: `{request.before_host_records_path}`\n"
        f"- After host records: `{request.after_host_records_path}`\n"
        f"- Beta records: `{request.beta_records_path}`\n\n"
        "## Artifacts\n\n"
        "- `trust-gate-transition`\n"
        "- `rc-go-check-preview`\n\n"
        "## Next Commands\n\n"
        f"{next_actions}\n\n"
        "## Non-Fabrication Policy\n\n"
        "Generated transition artifacts are reports only. They do not replace reviewer-observed real host evidence.\n"
    )


def _render_operator_transcript_template_markdown(payload: dict[str, Any]) -> str:
    return (
        f"# {payload['host']} Operator Transcript Template\n\n"
        f"Host: `{payload['host']}`\n\n"
        "Reviewer:\n\n"
        "Session date:\n\n"
        "## Commands used\n\n"
        "```bash\n"
        "# Paste only non-secret commands that were run in the real MCP host session.\n"
        "```\n\n"
        "## Observed host behavior\n\n"
        "- Real host UI/session observed:\n"
        "- Preview or workflow result reviewed:\n"
        "- Human-readable outcome:\n\n"
        "## Artifacts attached\n\n"
        "- Redacted screenshot/report/log path or URL:\n"
        "- Artifact privacy check completed:\n\n"
        "## Privacy note\n\n"
        f"{payload['privacy_note']}\n\n"
        "## Evidence policy\n\n"
        f"{payload['evidence_policy']}\n"
    )


def _host_slug(host: HostName) -> str:
    return host.lower().replace(" ", "-")


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


def _transition_pack_next_actions(request: EvidenceTransitionPackRequest) -> list[str]:
    return [
        (
            "albu-mcp trust gate-transition "
            f"--before-host-records {request.before_host_records_path} "
            f"--before-beta-records {request.beta_records_path} "
            f"--after-host-records {request.after_host_records_path} "
            f"--after-beta-records {request.beta_records_path} "
            f"--release-tag {request.release_tag} --format markdown"
        ),
        (
            "albu-mcp rc go-check "
            f"--host-records {request.after_host_records_path} --beta-records {request.beta_records_path} "
            f"--release-tag {request.release_tag} --format markdown"
        ),
    ]


def _rc_unblock_next_unlock_commands(*, publish_allowed: bool) -> list[str]:
    if publish_allowed:
        return [
            "albu-mcp rc go-check --format markdown",
            "albu-mcp distribution readiness --format json",
        ]
    return [
        "albu-mcp evidence proof-status --format json",
        "albu-mcp beta loop-pack --output-dir docs/beta-loop --format markdown",
        "albu-mcp rc go-check --format markdown",
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
