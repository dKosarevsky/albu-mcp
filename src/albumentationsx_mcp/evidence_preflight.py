"""One-shot no-write evidence preflight dashboard."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.evidence_import_wizard import EvidenceImportWizardRequest, build_evidence_import_wizard
from albumentationsx_mcp.evidence_proof import (
    RcUnblockPreviewRequest,
    build_evidence_proof_status,
    build_rc_unblock_preview,
)
from albumentationsx_mcp.evidence_template_guard import (
    EvidenceTemplateGuardRequest,
    build_evidence_template_guard,
)

DEFAULT_TEMPLATE_HOST_MANIFEST_PATHS = (
    Path("docs/operator-packets/codex-evidence-session-manifest.json"),
    Path("docs/operator-packets/claude-code-evidence-session-manifest.json"),
)
DEFAULT_TEMPLATE_BETA_DIR = Path("docs/beta-response-templates")


@dataclass(frozen=True)
class EvidencePreflightRequest:
    """Inputs for a no-write operator evidence preflight."""

    host_manifest_paths: tuple[Path, ...] = DEFAULT_TEMPLATE_HOST_MANIFEST_PATHS
    beta_dir_path: Path = DEFAULT_TEMPLATE_BETA_DIR
    template_host_manifest_paths: tuple[Path, ...] = DEFAULT_TEMPLATE_HOST_MANIFEST_PATHS
    template_beta_dir_path: Path = DEFAULT_TEMPLATE_BETA_DIR
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    host: HostName = "Codex"
    release_tag: str = "v1.15.0-rc.1"


def build_evidence_preflight(request: EvidencePreflightRequest) -> dict[str, Any]:
    """Build one no-write report across template, import, and release-evidence gates."""
    template_guard = build_evidence_template_guard(
        EvidenceTemplateGuardRequest(
            host_manifest_paths=request.template_host_manifest_paths,
            beta_dir_path=request.template_beta_dir_path,
            host_records_path=request.host_records_path,
        )
    )
    import_wizard = build_evidence_import_wizard(
        EvidenceImportWizardRequest(
            host_manifest_paths=request.host_manifest_paths,
            beta_dir_path=request.beta_dir_path,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            host=request.host,
            release_tag=request.release_tag,
            import_ready=False,
        )
    )
    proof_status = build_evidence_proof_status(records_path=request.host_records_path)
    rc_preview = build_rc_unblock_preview(
        RcUnblockPreviewRequest(
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    blocking_reasons = _blocking_reasons(template_guard=template_guard, import_wizard=import_wizard)
    evidence_blockers = _evidence_blockers(proof_status=proof_status, rc_preview=rc_preview)
    return {
        "preflight_status": _preflight_status(blocking_reasons=blocking_reasons, rc_preview=rc_preview),
        "writes_records": False,
        "release_tag": request.release_tag,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "template_guard_status": template_guard["guard_status"],
        "import_wizard_status": import_wizard["wizard_status"],
        "proof_status": proof_status["status"],
        "rc_preview_status": rc_preview["preview_status"],
        "publish_allowed": rc_preview["publish_allowed"],
        "blocking_reasons": blocking_reasons,
        "evidence_blockers": evidence_blockers,
        "next_commands": _next_commands(
            request=request,
            blocking_reasons=blocking_reasons,
            template_guard=template_guard,
            import_wizard=import_wizard,
            rc_preview=rc_preview,
        ),
        "template_guard": template_guard,
        "import_wizard": import_wizard,
        "proof": proof_status,
        "rc_unblock": rc_preview,
        "non_fabrication_policy": (
            "Evidence preflight is report-only. It reads template, import, and release blocker state without "
            "writing records, inferring outcomes, creating tags, or treating generated templates as evidence."
        ),
    }


def render_evidence_preflight_json(report: dict[str, Any]) -> str:
    """Render an evidence preflight report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_evidence_preflight_markdown(report: dict[str, Any]) -> str:
    """Render an evidence preflight report as Markdown."""
    blocking_reasons = "\n".join(f"- `{reason}`" for reason in report["blocking_reasons"]) or "- none"
    evidence_blockers = "\n".join(f"- `{reason}`" for reason in report["evidence_blockers"]) or "- none"
    next_commands = "\n".join(f"- `{command}`" for command in report["next_commands"]) or "- none"
    return (
        "# Evidence Preflight\n\n"
        f"Preflight status: `{report['preflight_status']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Template guard: `{report['template_guard_status']}`\n\n"
        f"Import wizard: `{report['import_wizard_status']}`\n\n"
        f"Proof status: `{report['proof_status']}`\n\n"
        f"RC preview: `{report['rc_preview_status']}`\n\n"
        "## Blocking Reasons\n\n"
        f"{blocking_reasons}\n\n"
        "## Evidence Blockers\n\n"
        f"{evidence_blockers}\n\n"
        "## Next Commands\n\n"
        f"{next_commands}\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{report['non_fabrication_policy']}\n"
    )


def _blocking_reasons(*, template_guard: dict[str, Any], import_wizard: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if template_guard["guard_status"] != "passed":
        for item in (*template_guard["host_manifests"], *template_guard["beta_drafts"]):
            if item["guard_status"] != "blocked_as_template":
                _append_once(reasons, f"template_guard:{item.get('violation_reason', item['guard_status'])}")
    if import_wizard["wizard_status"] == "blocked":
        for reason in import_wizard["blocked_reasons"]:
            _append_once(reasons, f"import_wizard:{reason}")
    return reasons


def _evidence_blockers(*, proof_status: dict[str, Any], rc_preview: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for host in proof_status["hosts"]:
        if host["closure_status"] != "closed":
            for gate in host["missing_gates"]:
                _append_once(blockers, f"proof_status:{host['host']}:{gate}")
    for reason in rc_preview["blocked_reasons"]:
        _append_once(blockers, f"rc_unblock:{reason}")
    return blockers


def _preflight_status(*, blocking_reasons: list[str], rc_preview: dict[str, Any]) -> str:
    if blocking_reasons:
        return "blocked"
    if rc_preview["publish_allowed"]:
        return "ready_for_release_owner_review"
    return "ready_to_import"


def _next_commands(
    *,
    request: EvidencePreflightRequest,
    blocking_reasons: list[str],
    template_guard: dict[str, Any],
    import_wizard: dict[str, Any],
    rc_preview: dict[str, Any],
) -> list[str]:
    commands: list[str] = []
    if any(reason.startswith("template_guard:") for reason in blocking_reasons):
        commands.append("Keep committed template paths blocked or move filled evidence into a session folder.")
        commands.extend(_template_guard_commands(template_guard))
    if any(reason.startswith("import_wizard:") for reason in blocking_reasons):
        commands.extend(import_wizard["next_commands"])
    if not blocking_reasons:
        commands.append(_import_ready_command(request))
        commands.append("albu-mcp evidence rc-unblock-preview --format json")
    if rc_preview["next_unlock_commands"] and blocking_reasons:
        commands.extend(rc_preview["next_unlock_commands"])
    return _dedupe(commands)


def _template_guard_commands(template_guard: dict[str, Any]) -> list[str]:
    return [
        item["import_command"]
        for item in (*template_guard["host_manifests"], *template_guard["beta_drafts"])
        if item["guard_status"] != "blocked_as_template" and "import_command" in item
    ]


def _import_ready_command(request: EvidencePreflightRequest) -> str:
    parts = ["albu-mcp", "evidence", "import-wizard"]
    for path in request.host_manifest_paths:
        parts.extend(["--host-manifest", str(path)])
    parts.extend(
        [
            "--beta-dir",
            str(request.beta_dir_path),
            "--host-records",
            str(request.host_records_path),
            "--beta-records",
            str(request.beta_records_path),
            "--host",
            request.host,
            "--release-tag",
            request.release_tag,
            "--import-ready",
            "--format",
            "json",
        ]
    )
    return " ".join(shlex.quote(part) for part in parts)


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _dedupe(items: list[str]) -> list[str]:
    deduped: list[str] = []
    for item in items:
        _append_once(deduped, item)
    return deduped
