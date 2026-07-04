"""No-write evidence-to-product loop helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import build_beta_validation_report, validate_beta_validation_records
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.evidence_proof import build_evidence_proof_status


@dataclass(frozen=True)
class EvidenceProductLoopRequest:
    """Inputs for one no-write evidence-to-product loop."""

    host: HostName
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_evidence_product_loop(request: EvidenceProductLoopRequest) -> dict[str, Any]:
    """Build one no-write product loop from real-host and beta evidence gates."""
    proof_status = build_evidence_proof_status(records_path=request.host_records_path)
    beta_report = build_beta_validation_report(validate_beta_validation_records(request.beta_records_path))
    blocked_reasons = _product_blocked_reasons(proof_status=proof_status, beta_report=beta_report)
    sections = [
        _real_host_evidence_section(request=request, proof_status=proof_status),
        _beta_validation_section(beta_report=beta_report),
        _product_backlog_section(blocked_reasons=blocked_reasons, beta_report=beta_report),
    ]
    return {
        "loop_status": "blocked" if blocked_reasons else "ready_for_product_backlog",
        "writes_records": False,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "section_count": len(sections),
        "sections": sections,
        "next_action": "collect_real_host_and_beta_evidence" if blocked_reasons else "select_product_depth_item",
        "non_fabrication_policy": (
            "No generated packet, fixture, smoke output, transcript template, or report-only artifact is counted as "
            "real host evidence or external beta validation."
        ),
    }


def build_evidence_product_loop_artifacts(
    request: EvidenceProductLoopRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build no-write evidence-to-product artifacts for operators."""
    report = build_evidence_product_loop(request)
    artifacts = [
        _loop_index_artifact(report=report, output_format=output_format),
        *[_loop_section_artifact(section=section, output_format=output_format) for section in report["sections"]],
    ]
    return {
        "pack_status": report["loop_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_evidence_product_loop_markdown(report: dict[str, Any]) -> str:
    """Render the evidence-to-product loop as Markdown."""
    sections = "\n".join(
        f"- `{section['id']}`: `{section['status']}`; writes_records=`{str(section['writes_records']).lower()}`"
        for section in report["sections"]
    )
    return (
        "# Evidence-to-Product Loop\n\n"
        f"Release tag: `{report['release_tag']}`\n\n"
        f"Host: `{report['host']}`\n\n"
        f"Loop status: `{report['loop_status']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Next action: `{report['next_action']}`\n\n"
        "## Sections\n\n"
        f"{sections}\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{report['non_fabrication_policy']}\n"
    )


def _loop_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    return {
        "filename": f"evidence-product-loop-index.{_extension(output_format)}",
        "content": _json_dumps(report) if output_format == "json" else render_evidence_product_loop_markdown(report),
    }


def _loop_section_artifact(*, section: dict[str, Any], output_format: str) -> dict[str, str]:
    return {
        "filename": f"{section['id'].replace('_', '-')}.{_extension(output_format)}",
        "content": _json_dumps(section) if output_format == "json" else _render_section_markdown(section),
    }


def _render_section_markdown(section: dict[str, Any]) -> str:
    commands = "\n".join(f"- `{command}`" for command in section.get("next_commands", [])) or "- none"
    summary = "\n".join(f"- `{key}`: `{value}`" for key, value in section.get("summary", {}).items()) or "- none"
    blocked_reasons = "\n".join(f"- `{reason}`" for reason in section.get("blocked_reasons", [])) or "- none"
    return (
        f"# {section['title']}\n\n"
        f"Section id: `{section['id']}`\n\n"
        f"Status: `{section['status']}`\n\n"
        f"Writes records: `{str(section['writes_records']).lower()}`\n\n"
        "## Summary\n\n"
        f"{summary}\n\n"
        "## Blocked Reasons\n\n"
        f"{blocked_reasons}\n\n"
        "## Next Commands\n\n"
        f"{commands}\n"
    )


def _extension(output_format: str) -> str:
    if output_format == "markdown":
        return "md"
    if output_format == "json":
        return "json"
    msg = f"unsupported evidence product loop format: {output_format}"
    raise ValueError(msg)


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _real_host_evidence_section(
    *,
    request: EvidenceProductLoopRequest,
    proof_status: dict[str, Any],
) -> dict[str, Any]:
    blocked = proof_status["status"] != "ready_for_rc_reopen"
    return {
        "id": "real_host_evidence",
        "title": "Real host evidence",
        "status": "blocked_until_real_host_evidence" if blocked else "ready",
        "writes_records": False,
        "proof_status": proof_status["status"],
        "blocked_host_count": proof_status["blocked_host_count"],
        "blocked_reasons": ["p0_host_evidence_missing_or_blocked"] if blocked else [],
        "next_commands": [
            f"albu-mcp activation evidence-cockpit --host {request.host} --format json",
            "albu-mcp evidence proof-status --format json",
            "albu-mcp evidence import-manifest",
        ],
    }


def _beta_validation_section(*, beta_report: dict[str, Any]) -> dict[str, Any]:
    blocked_reason = _beta_blocked_reason(beta_report)
    return {
        "id": "beta_validation",
        "title": "Beta validation",
        "status": "blocked_until_beta_validation" if blocked_reason else "ready",
        "writes_records": False,
        "privacy_status": beta_report["privacy_status"],
        "summary": beta_report["summary"],
        "blocked_reasons": [blocked_reason] if blocked_reason else [],
        "next_commands": [
            "albu-mcp beta loop-pack --output-dir docs/beta-loop --format markdown",
            "albu-mcp beta response-import-dir --input-dir docs/beta-loop --format json",
            "albu-mcp beta report --format json",
        ],
    }


def _product_backlog_section(*, blocked_reasons: list[str], beta_report: dict[str, Any]) -> dict[str, Any]:
    implementation_allowed = not blocked_reasons
    return {
        "id": "product_backlog",
        "title": "Product backlog",
        "status": "ready_for_product_backlog" if implementation_allowed else "blocked_until_external_evidence",
        "writes_records": False,
        "implementation_allowed": implementation_allowed,
        "blocked_reasons": blocked_reasons,
        "candidate_backlog_item_count": beta_report["summary"]["candidate_backlog_item_count"],
        "decisions": beta_report["decisions"],
        "next_commands": [
            "albu-mcp activation evidence-product-loop --host Codex --format json",
            "albu-mcp beta triage --format json",
            "albu-mcp trust dashboard --format markdown",
        ],
    }


def _product_blocked_reasons(*, proof_status: dict[str, Any], beta_report: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if proof_status["status"] != "ready_for_rc_reopen":
        reasons.append("p0_host_evidence_missing_or_blocked")
    beta_reason = _beta_blocked_reason(beta_report)
    if beta_reason is not None:
        reasons.append(beta_reason)
    return reasons


def _beta_blocked_reason(beta_report: dict[str, Any]) -> str | None:
    if beta_report["product_depth_allowed"]:
        return None
    if beta_report["summary"]["record_count"] == 0:
        return "beta_validation_records_missing"
    return "beta_validation_incomplete"
