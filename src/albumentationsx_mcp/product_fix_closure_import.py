"""Guarded writer for importing one post-fix outcome response."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import (
    import_beta_response_draft,
    load_beta_response_draft,
    validate_beta_validation_records,
    write_beta_validation_records,
)
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.product_fix_closure_runbook import (
    ProductFixClosureRunbookRequest,
    build_product_fix_closure_runbook,
)
from albumentationsx_mcp.product_fix_outcome import ProductFixOutcomeRequest, build_product_fix_outcome

_SNAPSHOT_FILENAME = "before-beta-validation-records.json"


@dataclass(frozen=True)
class ProductFixClosureImportRequest:
    """Inputs for guarded post-fix outcome import execution."""

    host: HostName
    input_path: Path
    confirm_import_ready: bool = False
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    snapshot_dir: Path = Path("docs/product-fix-closure-snapshot")
    closure_output_dir: Path = Path("docs/product-fix-closure-pack")
    release_tag: str = "v1.15.0-rc.1"


def build_product_fix_closure_import(request: ProductFixClosureImportRequest) -> dict[str, Any]:
    """Run the guarded post-fix response import only when every safety gate is open."""
    before_records = validate_beta_validation_records(request.beta_records_path)
    runbook = build_product_fix_closure_runbook(_runbook_request(request))
    snapshot_path = request.snapshot_dir / _SNAPSHOT_FILENAME
    imported_record = load_beta_response_draft(request.input_path).to_record().model_dump(mode="json")
    if runbook["runbook_status"] != "ready_for_operator_import":
        return _base_report(
            request=request,
            runbook=runbook,
            snapshot_path=snapshot_path,
            state=_ImportReportState(
                import_status="blocked_until_runbook_ready",
                writes_records=False,
                writes_snapshot=False,
                blocked_reasons=runbook["stop_conditions"] or [f"runbook_status:{runbook['runbook_status']}"],
                before_record_count=len(before_records.records),
                after_record_count=len(before_records.records),
                imported_record=imported_record,
                post_import_outcome=None,
                next_commands=runbook["next_commands"],
            ),
        )
    if not request.confirm_import_ready:
        return _base_report(
            request=request,
            runbook=runbook,
            snapshot_path=snapshot_path,
            state=_ImportReportState(
                import_status="blocked_until_confirm_import_ready",
                writes_records=False,
                writes_snapshot=False,
                blocked_reasons=["confirm_import_ready_missing"],
                before_record_count=len(before_records.records),
                after_record_count=len(before_records.records),
                imported_record=imported_record,
                post_import_outcome=None,
                next_commands=[_confirmed_import_command(request)],
            ),
        )

    write_beta_validation_records(snapshot_path, before_records)
    after_records = import_beta_response_draft(
        path=request.beta_records_path,
        draft=load_beta_response_draft(request.input_path),
    )
    post_import_outcome = build_product_fix_outcome(
        ProductFixOutcomeRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    closure_command = _closure_command(request=request, snapshot_path=snapshot_path)
    receipt_command = _receipt_command(request=request, snapshot_path=snapshot_path)
    final_outcome_command = _final_outcome_command(request)
    return _base_report(
        request=request,
        runbook=runbook,
        snapshot_path=snapshot_path,
        state=_ImportReportState(
            import_status="imported",
            writes_records=True,
            writes_snapshot=True,
            blocked_reasons=[],
            before_record_count=len(before_records.records),
            after_record_count=len(after_records.records),
            imported_record=imported_record,
            post_import_outcome=post_import_outcome,
            next_commands=[
                receipt_command,
                closure_command,
                final_outcome_command,
                f"albu-mcp activation evidence-product-loop --host {request.host} --format json",
            ],
        ),
    )


def render_product_fix_closure_import_json(report: dict[str, Any]) -> str:
    """Render a product fix closure import report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_closure_import_markdown(report: dict[str, Any]) -> str:
    """Render a product fix closure import report as Markdown."""
    return (
        "# Product Fix Closure Import\n\n"
        f"Import status: `{report['import_status']}`\n\n"
        f"Runbook status: `{report['runbook_status']}`\n\n"
        f"Confirm import ready: `{str(report['confirm_import_ready']).lower()}`\n\n"
        f"Runbook import allowed: `{str(report['runbook_import_allowed']).lower()}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Writes snapshot: `{str(report['writes_snapshot']).lower()}`\n\n"
        f"Before records: `{report['before_record_count']}`\n\n"
        f"After records: `{report['after_record_count']}`\n\n"
        f"Post-import outcome: `{report['post_import_outcome_status'] or 'none'}`\n\n"
        f"Snapshot path: `{report['snapshot_path']}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(report['blocked_reasons'], code=True)}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(report['next_commands'], code=True)}\n"
    )


@dataclass(frozen=True)
class _ImportReportState:
    import_status: str
    writes_records: bool
    writes_snapshot: bool
    blocked_reasons: list[str]
    before_record_count: int
    after_record_count: int
    imported_record: dict[str, Any]
    post_import_outcome: dict[str, Any] | None
    next_commands: list[str]


def _base_report(
    *,
    request: ProductFixClosureImportRequest,
    runbook: dict[str, Any],
    snapshot_path: Path,
    state: _ImportReportState,
) -> dict[str, Any]:
    return {
        "import_status": state.import_status,
        "runbook_status": runbook["runbook_status"],
        "confirm_import_ready": request.confirm_import_ready,
        "runbook_import_allowed": runbook["import_allowed"],
        "writes_records": state.writes_records,
        "writes_snapshot": state.writes_snapshot,
        "blocked_reasons": state.blocked_reasons,
        "selected_fix": runbook["selected_fix"],
        "input_path": str(request.input_path),
        "snapshot_path": str(snapshot_path),
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "before_record_count": state.before_record_count,
        "after_record_count": state.after_record_count,
        "imported_record": state.imported_record,
        "post_import_outcome_status": (
            None if state.post_import_outcome is None else state.post_import_outcome["outcome_status"]
        ),
        "source_runbook": runbook,
        "release_tag": request.release_tag,
        "host": request.host,
        "next_commands": state.next_commands,
        "non_fabrication_policy": _non_fabrication_policy(),
    }


def _runbook_request(request: ProductFixClosureImportRequest) -> ProductFixClosureRunbookRequest:
    return ProductFixClosureRunbookRequest(
        host=request.host,
        input_path=request.input_path,
        host_records_path=request.host_records_path,
        beta_records_path=request.beta_records_path,
        snapshot_dir=request.snapshot_dir,
        closure_output_dir=request.closure_output_dir,
        release_tag=request.release_tag,
    )


def _confirmed_import_command(request: ProductFixClosureImportRequest) -> str:
    return (
        f"albu-mcp activation product-fix-closure-import --host {request.host} "
        f"--host-records {request.host_records_path} --beta-records {request.beta_records_path} "
        f"--input {request.input_path} --snapshot-dir {request.snapshot_dir} "
        f"--closure-output-dir {request.closure_output_dir} --confirm-import-ready --format json"
    )


def _closure_command(*, request: ProductFixClosureImportRequest, snapshot_path: Path) -> str:
    return (
        f"albu-mcp activation product-fix-closure-pack --host {request.host} "
        f"--host-records {request.host_records_path} --before-beta-records {snapshot_path} "
        f"--beta-records {request.beta_records_path} --output-dir {request.closure_output_dir} --format markdown"
    )


def _receipt_command(*, request: ProductFixClosureImportRequest, snapshot_path: Path) -> str:
    return (
        f"albu-mcp activation product-fix-closure-receipt --host {request.host} "
        f"--host-records {request.host_records_path} --before-beta-records {snapshot_path} "
        f"--beta-records {request.beta_records_path} --snapshot-path {snapshot_path} "
        "--output-dir docs/product-fix-closure-receipt --format markdown"
    )


def _final_outcome_command(request: ProductFixClosureImportRequest) -> str:
    return (
        f"albu-mcp activation product-fix-outcome --host {request.host} "
        f"--host-records {request.host_records_path} --beta-records {request.beta_records_path} "
        "--output-dir docs/product-fix-outcome --format markdown"
    )


def _render_list(items: list[str], *, code: bool = False) -> str:
    if not items:
        return "- none"
    if code:
        return "\n".join(f"- `{item}`" for item in items)
    return "\n".join(f"- {item}" for item in items)


def _non_fabrication_policy() -> str:
    return (
        "The closure import command writes records only when the current runbook is ready and "
        "--confirm-import-ready is present. Otherwise it is a no-write report."
    )
