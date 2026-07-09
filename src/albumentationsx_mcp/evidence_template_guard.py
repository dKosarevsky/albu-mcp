"""Guard committed evidence templates from becoming importable evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import load_beta_response_draft, validate_beta_response_draft
from albumentationsx_mcp.evidence import (
    load_evidence_session_manifest,
    validate_evidence_session_manifest,
)


@dataclass(frozen=True)
class EvidenceTemplateGuardRequest:
    """Template paths that should remain blocked until real evidence is captured."""

    host_manifest_paths: tuple[Path, ...]
    beta_dir_path: Path
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")


def build_evidence_template_guard(request: EvidenceTemplateGuardRequest) -> dict[str, Any]:
    """Inspect generated evidence templates without writing records."""
    host_manifests = [_host_manifest_guard(path=path, request=request) for path in request.host_manifest_paths]
    beta_drafts = _beta_draft_guards(request.beta_dir_path)
    violations = [
        item["path"] for item in (*host_manifests, *beta_drafts) if item["guard_status"] != "blocked_as_template"
    ]
    return {
        "guard_status": "failed" if violations else "passed",
        "writes_records": False,
        "host_records_path": str(request.host_records_path),
        "beta_dir_path": str(request.beta_dir_path),
        "host_manifest_count": len(host_manifests),
        "beta_draft_count": len(beta_drafts),
        "host_manifests": host_manifests,
        "beta_drafts": beta_drafts,
        "guarded_paths": [item["path"] for item in (*host_manifests, *beta_drafts)],
        "violation_count": len(violations),
        "violations": violations,
        "non_fabrication_policy": (
            "Generated evidence templates are safe only while their validators keep them blocked. "
            "A template path that becomes ready_to_import must be moved out of the template area or imported "
            "through an explicit reviewed evidence workflow."
        ),
    }


def render_evidence_template_guard_json(report: dict[str, Any]) -> str:
    """Render a template guard report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_evidence_template_guard_markdown(report: dict[str, Any]) -> str:
    """Render a template guard report as Markdown."""
    host_items = "\n".join(_render_item_markdown(item) for item in report["host_manifests"]) or "- none"
    beta_items = "\n".join(_render_item_markdown(item) for item in report["beta_drafts"]) or "- none"
    violations = "\n".join(f"- `{path}`" for path in report["violations"]) or "- none"
    return (
        "# Evidence Template Guard\n\n"
        f"Guard status: `{report['guard_status']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        "## Host Manifests\n\n"
        f"{host_items}\n\n"
        "## Beta Drafts\n\n"
        f"{beta_items}\n\n"
        "## Violations\n\n"
        f"{violations}\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{report['non_fabrication_policy']}\n"
    )


def strict_template_guard_error(report: dict[str, Any]) -> ValueError:
    """Build the strict-mode CLI error for a failed template guard report."""
    count = report["violation_count"]
    reasons = {
        item.get("violation_reason")
        for item in (*report["host_manifests"], *report["beta_drafts"])
        if item["guard_status"] != "blocked_as_template"
    }
    if reasons and all(str(reason).endswith("_importable") for reason in reasons):
        suffix = "path" if count == 1 else "paths"
        return ValueError(f"evidence template-guard failed: {count} importable template {suffix}")
    suffix = "violation" if count == 1 else "violations"
    return ValueError(f"evidence template-guard failed: {count} template guard {suffix}")


def _host_manifest_guard(*, path: Path, request: EvidenceTemplateGuardRequest) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "guard_status": "missing",
            "violation_reason": "host_manifest_missing",
        }
    try:
        manifest = load_evidence_session_manifest(path)
        validation = validate_evidence_session_manifest(manifest=manifest, records_path=request.host_records_path)
    except ValueError as exc:
        return {
            "path": str(path),
            "guard_status": "invalid",
            "violation_reason": "host_manifest_invalid",
            "error": str(exc),
        }
    guard_status = _guard_status_for_validation(
        validation_status=validation["validation_status"],
        expected_template_status="template_requires_real_evidence",
    )
    item = {
        "path": str(path),
        "guard_status": guard_status,
        "validation_status": validation["validation_status"],
        "manifest_status": validation["manifest_status"],
        "host": validation["host"],
    }
    if guard_status != "blocked_as_template":
        item["violation_reason"] = "host_manifest_importable"
        item["import_command"] = f"albu-mcp evidence import-manifest --input {path} --path {request.host_records_path}"
    return item


def _beta_draft_guards(beta_dir_path: Path) -> list[dict[str, Any]]:
    if not beta_dir_path.exists():
        return [
            {
                "path": str(beta_dir_path),
                "guard_status": "missing",
                "violation_reason": "beta_dir_missing",
            }
        ]
    draft_paths = sorted(beta_dir_path.glob("*-beta-response.json"))
    if not draft_paths:
        return [
            {
                "path": str(beta_dir_path),
                "guard_status": "missing",
                "violation_reason": "beta_drafts_missing",
            }
        ]
    return [_beta_draft_guard(path) for path in draft_paths]


def _beta_draft_guard(path: Path) -> dict[str, Any]:
    try:
        report = validate_beta_response_draft(load_beta_response_draft(path))
    except ValueError as exc:
        return {
            "path": str(path),
            "guard_status": "invalid",
            "violation_reason": "beta_draft_invalid",
            "error": str(exc),
        }
    record = report["record"]
    guard_status = _guard_status_for_validation(
        validation_status=report["validation_status"],
        expected_template_status="template_requires_participant_evidence",
    )
    item = {
        "path": str(path),
        "guard_status": guard_status,
        "validation_status": report["validation_status"],
        "workflow_id": record["workflow_id"],
    }
    if guard_status != "blocked_as_template":
        item["violation_reason"] = "beta_draft_importable"
        item["import_command"] = f"albu-mcp beta response-import --input {path}"
    return item


def _guard_status_for_validation(*, validation_status: str, expected_template_status: str) -> str:
    if validation_status == expected_template_status:
        return "blocked_as_template"
    if validation_status == "ready_to_import":
        return "unsafe_ready_to_import"
    return "unexpected_validation_status"


def _render_item_markdown(item: dict[str, Any]) -> str:
    details = [f"`{item['path']}`: `{item['guard_status']}`"]
    if "validation_status" in item:
        details.append(f"validation=`{item['validation_status']}`")
    if "violation_reason" in item:
        details.append(f"reason=`{item['violation_reason']}`")
    return "- " + "; ".join(details)
