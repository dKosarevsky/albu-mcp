"""Evidence import wizard orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import (
    import_beta_response_draft_dir,
    load_beta_response_draft,
    validate_beta_response_draft,
)
from albumentationsx_mcp.evidence import (
    HostName,
    import_evidence_session_manifest,
    load_evidence_session_manifest,
    validate_evidence_session_manifest,
)
from albumentationsx_mcp.real_adoption_cycle import RealAdoptionCycleRequest, build_real_adoption_cycle


@dataclass(frozen=True)
class EvidenceImportWizardRequest:
    """Inputs for one evidence import wizard run."""

    host_manifest_paths: tuple[Path, ...]
    beta_dir_path: Path
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    host: HostName = "Codex"
    release_tag: str = "v1.15.0-rc.1"
    import_ready: bool = False


def build_evidence_import_wizard(request: EvidenceImportWizardRequest) -> dict[str, Any]:
    """Validate host and beta inputs before optionally importing records."""
    host_manifests = [_host_manifest_status(path=path, request=request) for path in request.host_manifest_paths]
    beta_drafts = _beta_draft_statuses(request.beta_dir_path)
    blocked_reasons = _blocked_reasons(host_manifests=host_manifests, beta_drafts=beta_drafts, request=request)
    if request.import_ready and blocked_reasons:
        msg = f"evidence import-wizard cannot import blocked inputs: {', '.join(blocked_reasons)}"
        raise ValueError(msg)
    if request.import_ready:
        _import_ready_records(request=request, host_manifests=host_manifests)
    cycle = build_real_adoption_cycle(
        RealAdoptionCycleRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    return {
        "wizard_status": _wizard_status(import_ready=request.import_ready, blocked_reasons=blocked_reasons),
        "writes_records": bool(request.import_ready and not blocked_reasons),
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "host_manifest_count": len(host_manifests),
        "beta_draft_count": len(beta_drafts),
        "host_manifests": host_manifests,
        "beta_drafts": beta_drafts,
        "blocked_reasons": blocked_reasons,
        "next_commands": _next_commands(blocked_reasons=blocked_reasons, request=request),
        "post_import_cycle_status": cycle["cycle_status"],
        "non_fabrication_policy": (
            "The wizard validates and imports reviewer-observed host manifests and privacy-safe beta drafts only. "
            "It does not create real evidence or infer participant outcomes."
        ),
    }


def render_evidence_import_wizard_markdown(report: dict[str, Any]) -> str:
    """Render an evidence import wizard report as Markdown."""
    host_items = "\n".join(
        f"- `{item['path']}`: `{item['status']}`"
        + (f"; validation=`{item['validation_status']}`" if "validation_status" in item else "")
        + (f"; manifest=`{item['manifest_status']}`" if "manifest_status" in item else "")
        + (f"; reason=`{item['blocked_reason']}`" if "blocked_reason" in item else "")
        for item in report["host_manifests"]
    )
    beta_items = "\n".join(
        f"- `{item['path']}`: `{item['status']}`"
        + (f"; reason=`{item['blocked_reason']}`" if "blocked_reason" in item else "")
        for item in report["beta_drafts"]
    )
    blockers = "\n".join(f"- `{reason}`" for reason in report["blocked_reasons"]) or "- none"
    commands = "\n".join(f"- `{command}`" for command in report["next_commands"]) or "- none"
    return (
        "# Evidence Import Wizard\n\n"
        f"Wizard status: `{report['wizard_status']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Post-import cycle status: `{report['post_import_cycle_status']}`\n\n"
        "## Host Manifests\n\n"
        f"{host_items or '- none'}\n\n"
        "## Beta Drafts\n\n"
        f"{beta_items or '- none'}\n\n"
        "## Blocked Reasons\n\n"
        f"{blockers}\n\n"
        "## Next Commands\n\n"
        f"{commands}\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{report['non_fabrication_policy']}\n"
    )


def render_evidence_import_wizard_json(report: dict[str, Any]) -> str:
    """Render an evidence import wizard report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def _host_manifest_status(*, path: Path, request: EvidenceImportWizardRequest) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "status": "blocked",
            "blocked_reason": "host_manifest_missing",
        }
    try:
        manifest = load_evidence_session_manifest(path)
        validation = validate_evidence_session_manifest(manifest=manifest, records_path=request.host_records_path)
    except ValueError as exc:
        return {
            "path": str(path),
            "status": "blocked",
            "blocked_reason": "host_manifest_invalid",
            "error": str(exc),
        }
    return {
        "path": str(path),
        "status": "ready_to_import" if validation["validation_status"] == "ready_to_import" else "blocked",
        "host": validation["host"],
        "validation_status": validation["validation_status"],
        "manifest_status": validation["manifest_status"],
        "artifact_count": validation["artifact_count"],
    }


def _beta_draft_statuses(beta_dir_path: Path) -> list[dict[str, Any]]:
    if not beta_dir_path.exists():
        return []
    draft_paths = sorted(beta_dir_path.glob("*-beta-response.json"))
    return [_beta_draft_status(path) for path in draft_paths]


def _beta_draft_status(path: Path) -> dict[str, Any]:
    try:
        report = validate_beta_response_draft(load_beta_response_draft(path))
    except ValueError as exc:
        return {
            "path": str(path),
            "status": "blocked",
            "blocked_reason": "beta_draft_invalid",
            "error": str(exc),
        }
    record = report["record"]
    return {
        "path": str(path),
        "status": "ready_to_import",
        "workflow_id": record["workflow_id"],
        "validation_status": report["validation_status"],
        "triage_bucket": record["triage_bucket"],
    }


def _blocked_reasons(
    *,
    host_manifests: list[dict[str, Any]],
    beta_drafts: list[dict[str, Any]],
    request: EvidenceImportWizardRequest,
) -> list[str]:
    reasons: list[str] = []
    for item in host_manifests:
        if item["status"] != "ready_to_import":
            _append_once(reasons, item.get("blocked_reason", "host_manifest_not_ready"))
    if not request.beta_dir_path.exists():
        reasons.append("beta_dir_missing")
    elif not beta_drafts:
        reasons.append("beta_drafts_missing")
    for item in beta_drafts:
        if item["status"] != "ready_to_import":
            _append_once(reasons, item.get("blocked_reason", "beta_draft_not_ready"))
    return reasons


def _import_ready_records(
    *,
    request: EvidenceImportWizardRequest,
    host_manifests: list[dict[str, Any]],
) -> None:
    for item in host_manifests:
        manifest = load_evidence_session_manifest(Path(item["path"]))
        import_evidence_session_manifest(manifest=manifest, records_path=request.host_records_path)
    import_beta_response_draft_dir(input_dir=request.beta_dir_path, path=request.beta_records_path)


def _wizard_status(*, import_ready: bool, blocked_reasons: list[str]) -> str:
    if blocked_reasons:
        return "blocked"
    if import_ready:
        return "imported"
    return "ready_to_import"


def _next_commands(*, blocked_reasons: list[str], request: EvidenceImportWizardRequest) -> list[str]:
    commands: list[str] = []
    if any(reason.startswith("host_manifest") for reason in blocked_reasons):
        commands.append("Fill reviewer-observed host manifests before import.")
    if any(reason.startswith("beta_") for reason in blocked_reasons):
        commands.append("Fill privacy-safe beta response drafts before import.")
    if not blocked_reasons:
        commands.append("Rerun evidence import-wizard with --import-ready after reviewer approval.")
    commands.append(f"albu-mcp activation real-adoption-cycle --host {request.host} --format json")
    return commands[:-1] if blocked_reasons else commands


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)
