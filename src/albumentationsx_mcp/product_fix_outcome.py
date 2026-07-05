"""No-write product fix outcome decision over validated behavior and real beta evidence."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import BetaValidationRecord, validate_beta_validation_records
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.product_fix_validation import ProductFixValidationRequest, build_product_fix_validation

_OUTCOME_STATUSES = ("blocked", "needs_followup", "passed")


@dataclass(frozen=True)
class ProductFixOutcomeRequest:
    """Inputs for deciding whether a validated product fix has real outcome evidence."""

    host: HostName
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_product_fix_outcome(request: ProductFixOutcomeRequest) -> dict[str, Any]:
    """Build a no-write acceptance/rejection report for one validated product fix."""
    validation = build_product_fix_validation(
        ProductFixValidationRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    if not validation["fix_validated"]:
        return _blocked_outcome_report(request=request, validation=validation)

    selected_fix = validation["selected_fix"]
    outcome_evidence = _build_outcome_evidence(
        triage_bucket=selected_fix["triage_bucket"],
        beta_records_path=request.beta_records_path,
    )
    outcome_status, blocked_reasons = _decide_outcome(outcome_evidence)
    fix_accepted = outcome_status == "accepted"
    fix_rejected = outcome_status == "rejected"
    return {
        "outcome_status": outcome_status,
        "validation_status": validation["validation_status"],
        "writes_records": False,
        "fix_validated": True,
        "evidence_sufficient": fix_accepted or fix_rejected,
        "fix_accepted": fix_accepted,
        "fix_rejected": fix_rejected,
        "blocked_reasons": blocked_reasons,
        "selected_fix": selected_fix,
        "outcome_evidence": outcome_evidence,
        "source_validation": validation,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": _next_commands(
            host=request.host,
            outcome_status=outcome_status,
            triage_bucket=selected_fix["triage_bucket"],
        ),
    }


def build_product_fix_outcome_artifacts(
    request: ProductFixOutcomeRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build artifact-only outcome files for a validated product fix."""
    report = build_product_fix_outcome(request)
    artifacts = [
        _outcome_index_artifact(report=report, output_format=output_format),
        _outcome_evidence_artifact(report=report, output_format=output_format),
        _outcome_decision_artifact(report=report, output_format=output_format),
    ]
    return {
        "pack_status": report["outcome_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_product_fix_outcome_json(report: dict[str, Any]) -> str:
    """Render a product fix outcome report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_outcome_markdown(report: dict[str, Any]) -> str:
    """Render a product fix outcome report as Markdown."""
    selected_fix = report["selected_fix"] or {}
    triage_bucket = selected_fix.get("triage_bucket", "none")
    return (
        "# Product Fix Outcome\n\n"
        f"Outcome status: `{report['outcome_status']}`\n\n"
        f"Validation status: `{report['validation_status']}`\n\n"
        f"Fix validated: `{str(report['fix_validated']).lower()}`\n\n"
        f"Evidence sufficient: `{str(report['evidence_sufficient']).lower()}`\n\n"
        f"Fix accepted: `{str(report['fix_accepted']).lower()}`\n\n"
        f"Fix rejected: `{str(report['fix_rejected']).lower()}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Triage bucket: `{triage_bucket}`\n\n"
        "## Outcome Evidence\n\n"
        f"{_render_outcome_evidence(report['outcome_evidence'])}\n"
    )


def _blocked_outcome_report(
    *,
    request: ProductFixOutcomeRequest,
    validation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "outcome_status": "blocked_until_product_fix_validation",
        "validation_status": validation["validation_status"],
        "writes_records": False,
        "fix_validated": False,
        "evidence_sufficient": False,
        "fix_accepted": False,
        "fix_rejected": False,
        "blocked_reasons": validation["blocked_reasons"],
        "selected_fix": validation["selected_fix"],
        "outcome_evidence": None,
        "source_validation": validation,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": [
            f"albu-mcp activation product-fix-validation --host {request.host} --format json",
            *validation["next_commands"],
        ],
    }


def _build_outcome_evidence(*, triage_bucket: str, beta_records_path: Path) -> dict[str, Any]:
    beta_records = validate_beta_validation_records(beta_records_path)
    matching_records = [record for record in beta_records.records if record.triage_bucket == triage_bucket]
    accepted_records = [record for record in matching_records if record.status == "passed"]
    rejected_records = [record for record in matching_records if record.status == "blocked"]
    open_records = [record for record in matching_records if record.status == "needs_followup"]
    return {
        "triage_bucket": triage_bucket,
        "record_count": len(matching_records),
        "status_counts": _status_counts(matching_records),
        "accepted_records": _dump_records(accepted_records),
        "rejected_records": _dump_records(rejected_records),
        "open_records": _dump_records(open_records),
        "artifact_refs": _artifact_refs(matching_records),
    }


def _decide_outcome(outcome_evidence: dict[str, Any]) -> tuple[str, list[str]]:
    triage_bucket = outcome_evidence["triage_bucket"]
    status_counts = outcome_evidence["status_counts"]
    if status_counts["blocked"] > 0:
        return "rejected", [f"post_fix_beta_blocked:{triage_bucket}"]
    if status_counts["passed"] > 0:
        return "accepted", []
    return "needs_more_evidence", [f"post_fix_acceptance_signal_missing:{triage_bucket}"]


def _status_counts(records: Iterable[BetaValidationRecord]) -> dict[str, int]:
    counts = dict.fromkeys(_OUTCOME_STATUSES, 0)
    for record in records:
        counts[record.status] += 1
    return counts


def _dump_records(records: list[BetaValidationRecord]) -> list[dict[str, Any]]:
    return [record.model_dump(mode="json") for record in records]


def _artifact_refs(records: list[BetaValidationRecord]) -> list[str]:
    refs = {artifact_ref for record in records for artifact_ref in record.artifact_refs}
    return sorted(refs)


def _next_commands(*, host: HostName, outcome_status: str, triage_bucket: str) -> list[str]:
    if outcome_status == "accepted":
        return [
            f"albu-mcp activation product-fix-outcome --host {host} --format markdown",
            f"albu-mcp activation evidence-product-loop --host {host} --format json",
        ]
    if outcome_status == "rejected":
        return [
            f"albu-mcp activation first-product-fix --host {host} --format json",
            f"albu-mcp activation product-fix-implementation-plan --host {host} --format json",
        ]
    return [
        f"Record a redacted post-fix beta attempt for {triage_bucket}.",
        "albu-mcp beta response-template --output-dir docs/beta-responses",
    ]


def _outcome_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "product_fix_outcome_index",
        "outcome_status": report["outcome_status"],
        "validation_status": report["validation_status"],
        "fix_validated": report["fix_validated"],
        "evidence_sufficient": report["evidence_sufficient"],
        "fix_accepted": report["fix_accepted"],
        "fix_rejected": report["fix_rejected"],
        "writes_records": False,
        "blocked_reasons": report["blocked_reasons"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"product-fix-outcome-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_index_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _outcome_evidence_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "outcome_evidence",
        "outcome_status": report["outcome_status"],
        "writes_records": False,
        "outcome_evidence": report["outcome_evidence"],
    }
    return {
        "filename": f"outcome-evidence.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_outcome_evidence_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _outcome_decision_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "outcome_decision",
        "outcome_status": report["outcome_status"],
        "writes_records": False,
        "fix_accepted": report["fix_accepted"],
        "fix_rejected": report["fix_rejected"],
        "evidence_sufficient": report["evidence_sufficient"],
        "blocked_reasons": report["blocked_reasons"],
        "selected_fix": report["selected_fix"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"outcome-decision.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_outcome_decision_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _render_index_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Product Fix Outcome Index\n\n"
        f"Outcome status: `{payload['outcome_status']}`\n\n"
        f"Validation status: `{payload['validation_status']}`\n\n"
        f"Fix validated: `{str(payload['fix_validated']).lower()}`\n\n"
        f"Evidence sufficient: `{str(payload['evidence_sufficient']).lower()}`\n\n"
        f"Fix accepted: `{str(payload['fix_accepted']).lower()}`\n\n"
        f"Fix rejected: `{str(payload['fix_rejected']).lower()}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(payload['blocked_reasons'], code=True)}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_outcome_evidence_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Outcome Evidence\n\n"
        f"Outcome status: `{payload['outcome_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"{_render_outcome_evidence(payload['outcome_evidence'])}\n"
    )


def _render_outcome_decision_artifact_markdown(payload: dict[str, Any]) -> str:
    selected_fix = payload["selected_fix"] or {}
    triage_bucket = selected_fix.get("triage_bucket", "none")
    return (
        "# Outcome Decision\n\n"
        f"Outcome status: `{payload['outcome_status']}`\n\n"
        f"Evidence sufficient: `{str(payload['evidence_sufficient']).lower()}`\n\n"
        f"Fix accepted: `{str(payload['fix_accepted']).lower()}`\n\n"
        f"Fix rejected: `{str(payload['fix_rejected']).lower()}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Triage bucket: `{triage_bucket}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(payload['blocked_reasons'], code=True)}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_outcome_evidence(outcome_evidence: dict[str, Any] | None) -> str:
    if outcome_evidence is None:
        return "- none"
    return (
        f"- Triage bucket: `{outcome_evidence['triage_bucket']}`\n"
        f"- Record count: `{outcome_evidence['record_count']}`\n"
        f"- Status counts: `{json.dumps(outcome_evidence['status_counts'], sort_keys=True)}`\n"
        f"- Artifact refs: {_inline_list(outcome_evidence['artifact_refs'])}\n\n"
        "### Accepted Records\n\n"
        f"{_render_records(outcome_evidence['accepted_records'])}\n\n"
        "### Rejected Records\n\n"
        f"{_render_records(outcome_evidence['rejected_records'])}\n\n"
        "### Open Records\n\n"
        f"{_render_records(outcome_evidence['open_records'])}"
    )


def _render_records(records: list[dict[str, Any]]) -> str:
    if not records:
        return "- none"
    return "\n".join(
        f"- `{record['status']}` `{record['attempt_date']}` `{record['workflow_id']}`: {record['summary']}"
        for record in records
    )


def _render_list(items: list[str], *, code: bool = False) -> str:
    if not items:
        return "- none"
    if code:
        return "\n".join(f"- `{item}`" for item in items)
    return "\n".join(f"- {item}" for item in items)


def _inline_list(items: list[str]) -> str:
    if not items:
        return "`none`"
    return ", ".join(f"`{item}`" for item in items)


def _artifact_extension(output_format: str) -> str:
    if output_format == "markdown":
        return "md"
    if output_format == "json":
        return "json"
    msg = f"unsupported product fix outcome artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported product fix outcome artifact format: {output_format}"
    raise ValueError(msg)
