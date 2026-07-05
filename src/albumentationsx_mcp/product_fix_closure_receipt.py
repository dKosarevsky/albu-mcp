"""No-write receipt after guarded post-fix outcome import."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import validate_beta_validation_records
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.product_fix_closure_pack import (
    ProductFixClosurePackRequest,
    build_product_fix_closure_pack,
)


@dataclass(frozen=True)
class ProductFixClosureReceiptRequest:
    """Inputs for building a post-import product fix closure receipt."""

    host: HostName
    before_beta_records_path: Path
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    snapshot_path: Path | None = None
    closure_output_dir: Path = Path("docs/product-fix-closure-pack")
    release_tag: str = "v1.15.0-rc.1"


def build_product_fix_closure_receipt(request: ProductFixClosureReceiptRequest) -> dict[str, Any]:
    """Build a no-write audit receipt for the guarded import-to-closure handoff."""
    before_records = validate_beta_validation_records(request.before_beta_records_path)
    after_records = validate_beta_validation_records(request.beta_records_path)
    closure_pack = build_product_fix_closure_pack(
        ProductFixClosurePackRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            before_beta_records_path=request.before_beta_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    imported_record = _imported_record(closure_pack)
    receipt_status = _receipt_status(closure_pack=closure_pack, imported_record=imported_record)
    blocked_reasons = _blocked_reasons(
        closure_pack=closure_pack,
        imported_record=imported_record,
        receipt_status=receipt_status,
    )
    snapshot_path = request.snapshot_path or request.before_beta_records_path
    closure_command = _closure_command(request=request)
    final_outcome_command = _final_outcome_command(request)
    return {
        "receipt_status": receipt_status,
        "writes_records": False,
        "writes_snapshot": False,
        "snapshot_path": str(snapshot_path),
        "before_record_count": len(before_records.records),
        "after_record_count": len(after_records.records),
        "new_record_count": closure_pack["evidence_diff"]["new_record_count"],
        "imported_record": imported_record,
        "closure_status": closure_pack["closure_status"],
        "before_outcome_status": closure_pack["before_outcome_status"],
        "after_outcome_status": closure_pack["after_outcome_status"],
        "selected_fix": closure_pack["selected_fix"],
        "blocked_reasons": blocked_reasons,
        "source_closure_pack": closure_pack,
        "closure_command": closure_command,
        "final_outcome_command": final_outcome_command,
        "next_commands": [closure_command, final_outcome_command],
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "before_beta_records_path": str(request.before_beta_records_path),
        "beta_records_path": str(request.beta_records_path),
        "closure_output_dir": str(request.closure_output_dir),
        "non_fabrication_policy": _non_fabrication_policy(),
    }


def build_product_fix_closure_receipt_artifacts(
    request: ProductFixClosureReceiptRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build no-write product fix closure receipt artifacts."""
    report = build_product_fix_closure_receipt(request)
    artifacts = [
        _receipt_index_artifact(report=report, output_format=output_format),
        _imported_record_artifact(report=report, output_format=output_format),
        _follow_up_commands_artifact(report=report, output_format=output_format),
    ]
    return {
        "pack_status": report["receipt_status"],
        "writes_records": False,
        "writes_snapshot": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_product_fix_closure_receipt_json(report: dict[str, Any]) -> str:
    """Render a product fix closure receipt as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_closure_receipt_markdown(report: dict[str, Any]) -> str:
    """Render a product fix closure receipt as Markdown."""
    return (
        "# Product Fix Closure Receipt\n\n"
        f"Receipt status: `{report['receipt_status']}`\n\n"
        f"Closure status: `{report['closure_status']}`\n\n"
        f"Before outcome: `{report['before_outcome_status']}`\n\n"
        f"After outcome: `{report['after_outcome_status']}`\n\n"
        f"Imported record: `{_record_presence(report['imported_record'])}`\n\n"
        f"New records: `{report['new_record_count']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Writes snapshot: `{str(report['writes_snapshot']).lower()}`\n\n"
        f"Snapshot path: `{report['snapshot_path']}`\n\n"
        "## Imported Record\n\n"
        f"{_render_imported_record(report['imported_record'])}\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(report['blocked_reasons'], code=True)}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(report['next_commands'], code=True)}\n"
    )


def _receipt_status(*, closure_pack: dict[str, Any], imported_record: dict[str, Any] | None) -> str:
    closure_status = closure_pack["closure_status"]
    if closure_status in {"closed_accepted", "closed_rejected"} and imported_record is not None:
        return "ready"
    if imported_record is None:
        return "blocked_until_post_fix_outcome_import"
    if closure_status == "blocked_until_conclusive_post_fix_outcome":
        return "blocked_until_conclusive_post_fix_outcome"
    return closure_status


def _blocked_reasons(
    *,
    closure_pack: dict[str, Any],
    imported_record: dict[str, Any] | None,
    receipt_status: str,
) -> list[str]:
    if receipt_status == "ready":
        return []
    reasons = list(closure_pack["blocked_reasons"])
    if imported_record is None:
        reasons.append("post_fix_import_record_missing")
    return _dedupe(reasons)


def _imported_record(closure_pack: dict[str, Any]) -> dict[str, Any] | None:
    new_records = closure_pack["evidence_diff"]["new_records"]
    if not new_records:
        return None
    return new_records[0]


def _closure_command(*, request: ProductFixClosureReceiptRequest) -> str:
    return (
        f"albu-mcp activation product-fix-closure-pack --host {request.host} "
        f"--host-records {request.host_records_path} --before-beta-records {request.before_beta_records_path} "
        f"--beta-records {request.beta_records_path} --output-dir {request.closure_output_dir} --format markdown"
    )


def _final_outcome_command(request: ProductFixClosureReceiptRequest) -> str:
    return (
        f"albu-mcp activation product-fix-outcome --host {request.host} "
        f"--host-records {request.host_records_path} --beta-records {request.beta_records_path} "
        "--output-dir docs/product-fix-outcome --format markdown"
    )


def _receipt_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "product_fix_closure_receipt_index",
        "receipt_status": report["receipt_status"],
        "closure_status": report["closure_status"],
        "writes_records": False,
        "writes_snapshot": False,
        "snapshot_path": report["snapshot_path"],
        "before_record_count": report["before_record_count"],
        "after_record_count": report["after_record_count"],
        "new_record_count": report["new_record_count"],
        "blocked_reasons": report["blocked_reasons"],
        "selected_fix": report["selected_fix"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"product-fix-closure-receipt-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_index_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _imported_record_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "imported_record",
        "receipt_status": report["receipt_status"],
        "writes_records": False,
        "writes_snapshot": False,
        "imported_record": report["imported_record"],
    }
    return {
        "filename": f"imported-record.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_imported_record_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _follow_up_commands_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "follow_up_commands",
        "receipt_status": report["receipt_status"],
        "writes_records": False,
        "writes_snapshot": False,
        "closure_command": report["closure_command"],
        "final_outcome_command": report["final_outcome_command"],
        "next_commands": report["next_commands"],
        "non_fabrication_policy": report["non_fabrication_policy"],
    }
    return {
        "filename": f"follow-up-commands.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_follow_up_commands_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _render_index_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Product Fix Closure Receipt Index\n\n"
        f"Receipt status: `{payload['receipt_status']}`\n\n"
        f"Closure status: `{payload['closure_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Writes snapshot: `{str(payload['writes_snapshot']).lower()}`\n\n"
        f"Snapshot path: `{payload['snapshot_path']}`\n\n"
        f"Before records: `{payload['before_record_count']}`\n\n"
        f"After records: `{payload['after_record_count']}`\n\n"
        f"New records: `{payload['new_record_count']}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(payload['blocked_reasons'], code=True)}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_imported_record_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Imported Record\n\n"
        f"Receipt status: `{payload['receipt_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Writes snapshot: `{str(payload['writes_snapshot']).lower()}`\n\n"
        f"Imported record: `{_record_presence(payload['imported_record'])}`\n\n"
        f"{_render_imported_record(payload['imported_record'])}\n"
    )


def _render_follow_up_commands_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Follow-Up Commands\n\n"
        f"Receipt status: `{payload['receipt_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Writes snapshot: `{str(payload['writes_snapshot']).lower()}`\n\n"
        "## Closure Pack\n\n"
        f"- `{payload['closure_command']}`\n\n"
        "## Final Outcome\n\n"
        f"- `{payload['final_outcome_command']}`\n\n"
        "## Policy\n\n"
        f"{payload['non_fabrication_policy']}\n"
    )


def _render_imported_record(record: dict[str, Any] | None) -> str:
    if record is None:
        return "- none"
    return (
        f"- Workflow: `{record['workflow_id']}`\n"
        f"- Status: `{record['status']}`\n"
        f"- Triage bucket: `{record['triage_bucket']}`\n"
        f"- Summary: {record['summary']}"
    )


def _record_presence(record: dict[str, Any] | None) -> str:
    return "none" if record is None else "present"


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
    msg = f"unsupported product fix closure receipt artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported product fix closure receipt artifact format: {output_format}"
    raise ValueError(msg)


def _non_fabrication_policy() -> str:
    return (
        "The closure receipt is report-only. It reads the pre-import snapshot and current beta records, "
        "does not import records, does not write snapshots, and only reports post-fix records already "
        "present in the after-state."
    )
