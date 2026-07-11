"""No-write status orchestration for one evidence execution pack."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.evidence_execution_pack import (
    EvidenceExecutionPackProgressRequest,
    build_evidence_execution_pack_progress,
)
from albumentationsx_mcp.evidence_import_wizard import EvidenceImportWizardRequest, build_evidence_import_wizard


@dataclass(frozen=True)
class EvidenceExecutionPackStatusRequest:
    """Inputs for one no-write execution-pack status report."""

    input_dir: Path
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")


def build_evidence_execution_pack_status(request: EvidenceExecutionPackStatusRequest) -> dict[str, Any]:
    """Summarize pack structure, fill progress, and no-write import readiness."""
    progress = build_evidence_execution_pack_progress(
        EvidenceExecutionPackProgressRequest(
            input_dir=request.input_dir,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
        )
    )
    audit = progress["audit"]
    import_wizard = _build_import_wizard(request=request, audit=audit)
    status, next_action = _status_and_next_action(audit=audit, progress=progress, import_wizard=import_wizard)
    return {
        "status": status,
        "writes_records": False,
        "input_dir": str(request.input_dir),
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "audit_status": audit["audit_status"],
        "progress_status": progress["progress_status"],
        "import_wizard_status": "not_run" if import_wizard is None else import_wizard["wizard_status"],
        "required_item_count": progress["required_item_count"],
        "completed_item_count": progress["completed_item_count"],
        "pending_host_count": len(progress["host_updates"]),
        "pending_beta_count": len(progress["beta_updates"]),
        "import_ready_command_available": bool(
            progress["progress_status"] == "ready_for_import_review"
            and import_wizard is not None
            and import_wizard["wizard_status"] == "ready_to_import"
        ),
        "blocking_reasons": _status_blocking_reasons(
            audit=audit,
            progress=progress,
            import_wizard=import_wizard,
        ),
        "next_action": next_action,
        "next_commands": _status_next_commands(
            request=request,
            status=status,
            audit=audit,
            progress=progress,
            import_wizard=import_wizard,
        ),
        "audit": audit,
        "progress": progress,
        "import_wizard": import_wizard,
        "non_fabrication_policy": (
            "Execution pack status is report-only. It does not write records, approve imports, infer outcomes, or "
            "treat generated templates as real host or beta evidence."
        ),
    }


def render_evidence_execution_pack_status_json(report: dict[str, Any]) -> str:
    """Render an execution-pack status report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_evidence_execution_pack_status_markdown(report: dict[str, Any]) -> str:
    """Render an execution-pack status report as Markdown."""
    blockers = "\n".join(f"- `{reason}`" for reason in report["blocking_reasons"]) or "- none"
    commands = "\n".join(f"- `{command}`" for command in report["next_commands"]) or "- none"
    return (
        "# Evidence Execution Pack Status\n\n"
        f"Status: `{report['status']}`  \n"
        f"Writes records: `{str(report['writes_records']).lower()}`  \n"
        f"Audit: `{report['audit_status']}`  \n"
        f"Progress: `{report['progress_status']}`  \n"
        f"Import wizard: `{report['import_wizard_status']}`  \n"
        f"Completed: `{report['completed_item_count']}/{report['required_item_count']}`  \n"
        f"Pending hosts: `{report['pending_host_count']}`  \n"
        f"Pending beta responses: `{report['pending_beta_count']}`  \n"
        "Import-ready command available: "
        f"`{str(report['import_ready_command_available']).lower()}`  \n"
        f"Next action: `{report['next_action']}`\n\n"
        "## Blocking Reasons\n\n"
        f"{blockers}\n\n"
        "## Next Commands\n\n"
        f"{commands}\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{report['non_fabrication_policy']}\n"
    )


def _build_import_wizard(
    *,
    request: EvidenceExecutionPackStatusRequest,
    audit: dict[str, Any],
) -> dict[str, Any] | None:
    if audit["audit_status"] == "blocked":
        return None
    return build_evidence_import_wizard(
        EvidenceImportWizardRequest(
            host_manifest_paths=tuple(Path(item["path"]) for item in audit["host_manifests"]),
            beta_dir_path=request.input_dir / "beta-responses",
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            import_ready=False,
        )
    )


def _status_and_next_action(
    *,
    audit: dict[str, Any],
    progress: dict[str, Any],
    import_wizard: dict[str, Any] | None,
) -> tuple[str, str]:
    if audit["audit_status"] == "blocked":
        return "blocked", "repair_execution_pack"
    if progress["progress_status"] != "ready_for_import_review":
        return "needs_real_session_input", "fill_real_session_evidence"
    if import_wizard is None or import_wizard["wizard_status"] != "ready_to_import":
        return "blocked", "resolve_import_wizard_blockers"
    return "ready_for_import_review", "review_and_run_import"


def _status_blocking_reasons(
    *,
    audit: dict[str, Any],
    progress: dict[str, Any],
    import_wizard: dict[str, Any] | None,
) -> list[str]:
    if audit["audit_status"] == "blocked":
        return list(audit["blocking_reasons"])
    if progress["progress_status"] != "ready_for_import_review" or import_wizard is None:
        return []
    return [f"import_wizard:{reason}" for reason in import_wizard["blocked_reasons"]]


def _status_next_commands(
    *,
    request: EvidenceExecutionPackStatusRequest,
    status: str,
    audit: dict[str, Any],
    progress: dict[str, Any],
    import_wizard: dict[str, Any] | None,
) -> list[str]:
    if status == "needs_real_session_input":
        rerun_status = (
            "albu-mcp evidence execution-pack-status "
            f"--input-dir {shlex.quote(str(request.input_dir))} --format markdown"
        )
        return _first_unique([*progress["next_commands"][:2], rerun_status])
    if status == "ready_for_import_review":
        import_commands = [command for command in audit["next_commands"] if "--import-ready" in command]
        wizard_commands = [] if import_wizard is None else import_wizard["next_commands"]
        return _first_unique([*import_commands, *wizard_commands])
    if audit["audit_status"] == "blocked":
        return _first_unique(audit["next_commands"])
    wizard_commands = [] if import_wizard is None else import_wizard["next_commands"]
    safe_audit_commands = [command for command in audit["next_commands"] if "--import-ready" not in command]
    return _first_unique([*wizard_commands, *safe_audit_commands])


def _first_unique(items: list[str], *, limit: int = 3) -> list[str]:
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
        if len(result) == limit:
            break
    return result
