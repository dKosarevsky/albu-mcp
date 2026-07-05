"""No-write closure pack after importing post-fix beta outcome evidence."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import BetaValidationRecord, validate_beta_validation_records
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.product_fix_outcome import ProductFixOutcomeRequest, build_product_fix_outcome

_OUTCOME_STATUSES = ("blocked", "needs_followup", "passed")


@dataclass(frozen=True)
class ProductFixClosurePackRequest:
    """Inputs for building a post-import product fix closure pack."""

    host: HostName
    before_beta_records_path: Path
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_product_fix_closure_pack(request: ProductFixClosurePackRequest) -> dict[str, Any]:
    """Build a no-write post-import closure report for one selected product fix."""
    before_outcome = build_product_fix_outcome(
        ProductFixOutcomeRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.before_beta_records_path,
            release_tag=request.release_tag,
        )
    )
    after_outcome = build_product_fix_outcome(
        ProductFixOutcomeRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    selected_fix = after_outcome["selected_fix"] or before_outcome["selected_fix"]
    triage_bucket = None if selected_fix is None else selected_fix["triage_bucket"]
    evidence_diff = _build_evidence_diff(
        triage_bucket=triage_bucket,
        before_beta_records_path=request.before_beta_records_path,
        after_beta_records_path=request.beta_records_path,
    )
    closure_status = _closure_status(after_outcome=after_outcome, evidence_diff=evidence_diff)
    blocked_reasons = _blocked_reasons(
        after_outcome=after_outcome,
        evidence_diff=evidence_diff,
        closure_status=closure_status,
    )
    closure_summary = _closure_summary(
        closure_status=closure_status,
        after_outcome=after_outcome,
        selected_fix=selected_fix,
        evidence_diff=evidence_diff,
    )
    return {
        "closure_status": closure_status,
        "writes_records": False,
        "before_outcome_status": before_outcome["outcome_status"],
        "after_outcome_status": after_outcome["outcome_status"],
        "closure_ready": closure_status in {"closed_accepted", "closed_rejected"},
        "blocked_reasons": blocked_reasons,
        "selected_fix": selected_fix,
        "evidence_diff": evidence_diff,
        "closure_summary": closure_summary,
        "source_before_outcome": before_outcome,
        "source_after_outcome": after_outcome,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "before_beta_records_path": str(request.before_beta_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": _next_commands(
            host=request.host,
            beta_records_path=request.beta_records_path,
            closure_status=closure_status,
        ),
        "non_fabrication_policy": (
            "The closure pack is report-only. It reads before/after beta records, does not import records, and "
            "summarizes only redacted post-fix beta records that are present in the after-state."
        ),
    }


def build_product_fix_closure_pack_artifacts(
    request: ProductFixClosurePackRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build artifact-only post-import closure files."""
    report = build_product_fix_closure_pack(request)
    artifacts = [
        _closure_index_artifact(report=report, output_format=output_format),
        _evidence_diff_artifact(report=report, output_format=output_format),
        _release_summary_artifact(report=report, output_format=output_format),
    ]
    return {
        "pack_status": report["closure_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_product_fix_closure_pack_json(report: dict[str, Any]) -> str:
    """Render a product fix closure pack as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_closure_pack_markdown(report: dict[str, Any]) -> str:
    """Render a product fix closure pack as Markdown."""
    return (
        "# Product Fix Closure Pack\n\n"
        f"Closure status: `{report['closure_status']}`\n\n"
        f"Before outcome: `{report['before_outcome_status']}`\n\n"
        f"After outcome: `{report['after_outcome_status']}`\n\n"
        f"New records: `{report['evidence_diff']['new_record_count']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(report['blocked_reasons'], code=True)}\n\n"
        "## Release Summary\n\n"
        f"{_render_release_summary(report['closure_summary'])}\n"
    )


def _build_evidence_diff(
    *,
    triage_bucket: str | None,
    before_beta_records_path: Path,
    after_beta_records_path: Path,
) -> dict[str, Any]:
    if triage_bucket is None:
        return _empty_evidence_diff()
    before_records = _matching_records(path=before_beta_records_path, triage_bucket=triage_bucket)
    after_records = _matching_records(path=after_beta_records_path, triage_bucket=triage_bucket)
    before_keys = {_record_key(record) for record in before_records}
    new_records = [record for record in after_records if _record_key(record) not in before_keys]
    before_counts = _status_counts(before_records)
    after_counts = _status_counts(after_records)
    return {
        "triage_bucket": triage_bucket,
        "before_record_count": len(before_records),
        "after_record_count": len(after_records),
        "new_record_count": len(new_records),
        "before_status_counts": before_counts,
        "after_status_counts": after_counts,
        "status_count_delta": {status: after_counts[status] - before_counts[status] for status in _OUTCOME_STATUSES},
        "new_records": _dump_records(new_records),
        "artifact_refs_added": _artifact_refs(new_records),
    }


def _empty_evidence_diff() -> dict[str, Any]:
    empty_counts = dict.fromkeys(_OUTCOME_STATUSES, 0)
    return {
        "triage_bucket": None,
        "before_record_count": 0,
        "after_record_count": 0,
        "new_record_count": 0,
        "before_status_counts": empty_counts,
        "after_status_counts": empty_counts,
        "status_count_delta": empty_counts,
        "new_records": [],
        "artifact_refs_added": [],
    }


def _matching_records(*, path: Path, triage_bucket: str) -> list[BetaValidationRecord]:
    records = validate_beta_validation_records(path)
    return [record for record in records.records if record.triage_bucket == triage_bucket]


def _record_key(record: BetaValidationRecord) -> tuple[str, str, str]:
    return (record.workflow_id, record.attempt_date.isoformat(), record.summary)


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


def _closure_status(*, after_outcome: dict[str, Any], evidence_diff: dict[str, Any]) -> str:
    if after_outcome["outcome_status"] == "accepted":
        return "closed_accepted"
    if after_outcome["outcome_status"] == "rejected":
        return "closed_rejected"
    if after_outcome["outcome_status"] == "blocked_until_product_fix_validation":
        return "blocked_until_product_fix_validation"
    if evidence_diff["new_record_count"] == 0:
        return "blocked_until_post_fix_outcome_import"
    return "blocked_until_conclusive_post_fix_outcome"


def _blocked_reasons(
    *,
    after_outcome: dict[str, Any],
    evidence_diff: dict[str, Any],
    closure_status: str,
) -> list[str]:
    if closure_status in {"closed_accepted", "closed_rejected"}:
        return []
    reasons = ["post_fix_outcome_not_closed", *after_outcome["blocked_reasons"]]
    if evidence_diff["new_record_count"] == 0:
        reasons.append("post_fix_import_record_missing")
    return _dedupe(reasons)


def _closure_summary(
    *,
    closure_status: str,
    after_outcome: dict[str, Any],
    selected_fix: dict[str, Any] | None,
    evidence_diff: dict[str, Any],
) -> dict[str, Any]:
    if selected_fix is None or closure_status not in {"closed_accepted", "closed_rejected"}:
        return {
            "summary_status": "blocked",
            "private_data_included": False,
            "product_area": None,
            "triage_bucket": evidence_diff["triage_bucket"],
            "outcome_status": after_outcome["outcome_status"],
            "new_record_count": evidence_diff["new_record_count"],
            "release_note": None,
            "changelog_entry": None,
            "source_record_summaries": _record_summaries(evidence_diff["new_records"]),
        }

    outcome_word = "accepted" if closure_status == "closed_accepted" else "rejected"
    product_area = selected_fix["product_area"]
    triage_bucket = selected_fix["triage_bucket"]
    source_summaries = _record_summaries(evidence_diff["new_records"])
    evidence_summary = source_summaries[0] if source_summaries else "No new redacted post-fix record summary."
    return {
        "summary_status": "ready",
        "private_data_included": False,
        "product_area": product_area,
        "triage_bucket": triage_bucket,
        "outcome_status": after_outcome["outcome_status"],
        "new_record_count": evidence_diff["new_record_count"],
        "release_note": (
            f"{product_area}: post-fix outcome {outcome_word} for {triage_bucket}. Evidence: {evidence_summary}"
        ),
        "changelog_entry": (
            f"- {product_area}: closed {triage_bucket} product fix as {outcome_word} based on "
            f"{evidence_diff['new_record_count']} redacted post-fix beta record(s)."
        ),
        "source_record_summaries": source_summaries,
    }


def _record_summaries(records: list[dict[str, Any]]) -> list[str]:
    return [record["summary"] for record in records]


def _next_commands(*, host: HostName, beta_records_path: Path, closure_status: str) -> list[str]:
    if closure_status == "closed_accepted":
        return [
            f"albu-mcp activation evidence-product-loop --host {host} --format json",
            f"albu-mcp activation product-fix-outcome --host {host} --format markdown",
        ]
    if closure_status == "closed_rejected":
        return [
            f"albu-mcp activation first-product-fix --host {host} --format json",
            f"albu-mcp activation product-fix-implementation-plan --host {host} --format json",
        ]
    return [
        f"albu-mcp activation product-fix-outcome-capture --host {host} --format json",
        (f"albu-mcp activation product-fix-outcome-import-guard --host {host} --input <post-fix-draft> --format json"),
        f"albu-mcp beta response-import --input <post-fix-draft> --path {beta_records_path}",
        f"albu-mcp activation product-fix-outcome --host {host} --format json",
    ]


def _closure_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "product_fix_closure_pack_index",
        "closure_status": report["closure_status"],
        "before_outcome_status": report["before_outcome_status"],
        "after_outcome_status": report["after_outcome_status"],
        "closure_ready": report["closure_ready"],
        "writes_records": False,
        "blocked_reasons": report["blocked_reasons"],
        "selected_fix": report["selected_fix"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"product-fix-closure-pack-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_index_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _evidence_diff_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "evidence_diff",
        "closure_status": report["closure_status"],
        "writes_records": False,
        "evidence_diff": report["evidence_diff"],
    }
    return {
        "filename": f"evidence-diff.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_evidence_diff_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _release_summary_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "release_summary",
        "closure_status": report["closure_status"],
        "writes_records": False,
        "closure_summary": report["closure_summary"],
        "non_fabrication_policy": report["non_fabrication_policy"],
    }
    return {
        "filename": f"release-summary.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_release_summary_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _render_index_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Product Fix Closure Pack Index\n\n"
        f"Closure status: `{payload['closure_status']}`\n\n"
        f"Before outcome: `{payload['before_outcome_status']}`\n\n"
        f"After outcome: `{payload['after_outcome_status']}`\n\n"
        f"Closure ready: `{str(payload['closure_ready']).lower()}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(payload['blocked_reasons'], code=True)}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_evidence_diff_artifact_markdown(payload: dict[str, Any]) -> str:
    diff = payload["evidence_diff"]
    return (
        "# Evidence Diff\n\n"
        f"Closure status: `{payload['closure_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Triage bucket: `{diff['triage_bucket'] or 'none'}`\n\n"
        f"Before records: `{diff['before_record_count']}`\n\n"
        f"After records: `{diff['after_record_count']}`\n\n"
        f"New records: `{diff['new_record_count']}`\n\n"
        "## New Record Summaries\n\n"
        f"{_render_list(_record_summaries(diff['new_records']))}\n"
    )


def _render_release_summary_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Release Summary\n\n"
        f"Closure status: `{payload['closure_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"{_render_release_summary(payload['closure_summary'])}\n\n"
        "## Policy\n\n"
        f"{payload['non_fabrication_policy']}\n"
    )


def _render_release_summary(summary: dict[str, Any]) -> str:
    return (
        f"Summary status: `{summary['summary_status']}`\n\n"
        f"Product area: `{summary['product_area'] or 'none'}`\n\n"
        f"Triage bucket: `{summary['triage_bucket'] or 'none'}`\n\n"
        f"Private data included: `{str(summary['private_data_included']).lower()}`\n\n"
        f"Release note: {summary['release_note'] or 'none'}\n\n"
        f"Changelog entry: {summary['changelog_entry'] or 'none'}"
    )


def _render_list(items: list[str], *, code: bool = False) -> str:
    if not items:
        return "- none"
    if code:
        return "\n".join(f"- `{item}`" for item in items)
    return "\n".join(f"- {item}" for item in items)


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _artifact_extension(output_format: str) -> str:
    if output_format == "markdown":
        return "md"
    if output_format == "json":
        return "json"
    msg = f"unsupported product fix closure pack artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported product fix closure pack artifact format: {output_format}"
    raise ValueError(msg)
