"""No-write closure pipeline status across snapshot, import, receipt, and outcome."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.product_fix_closure_pack import (
    ProductFixClosurePackRequest,
    build_product_fix_closure_pack,
)
from albumentationsx_mcp.product_fix_closure_receipt import (
    ProductFixClosureReceiptRequest,
    build_product_fix_closure_receipt,
)
from albumentationsx_mcp.product_fix_closure_runbook import (
    ProductFixClosureRunbookRequest,
    build_product_fix_closure_runbook,
)
from albumentationsx_mcp.product_fix_outcome import ProductFixOutcomeRequest, build_product_fix_outcome

_SNAPSHOT_FILENAME = "before-beta-validation-records.json"


@dataclass(frozen=True)
class ProductFixClosurePipelineRequest:
    """Inputs for building a no-write product fix closure pipeline status."""

    host: HostName
    input_path: Path
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    snapshot_dir: Path = Path("docs/product-fix-closure-snapshot")
    closure_output_dir: Path = Path("docs/product-fix-closure-pack")
    receipt_output_dir: Path = Path("docs/product-fix-closure-receipt")
    final_outcome_output_dir: Path = Path("docs/product-fix-outcome")
    release_tag: str = "v1.15.0-rc.1"


def build_product_fix_closure_pipeline(request: ProductFixClosurePipelineRequest) -> dict[str, Any]:
    """Build one read-only status report for the closure operator pipeline."""
    snapshot_path = request.snapshot_dir / _SNAPSHOT_FILENAME
    snapshot_file_present = snapshot_path.exists()
    runbook = build_product_fix_closure_runbook(_runbook_request(request))
    final_outcome = build_product_fix_outcome(_outcome_request(request))
    commands = _commands(request=request, snapshot_path=snapshot_path)
    receipt = None
    closure_pack = None
    if snapshot_file_present:
        receipt = build_product_fix_closure_receipt(
            ProductFixClosureReceiptRequest(
                host=request.host,
                host_records_path=request.host_records_path,
                before_beta_records_path=snapshot_path,
                beta_records_path=request.beta_records_path,
                snapshot_path=snapshot_path,
                closure_output_dir=request.closure_output_dir,
                release_tag=request.release_tag,
            )
        )
        closure_pack = build_product_fix_closure_pack(
            ProductFixClosurePackRequest(
                host=request.host,
                host_records_path=request.host_records_path,
                before_beta_records_path=snapshot_path,
                beta_records_path=request.beta_records_path,
                release_tag=request.release_tag,
            )
        )

    import_status = _import_status(
        runbook=runbook,
        receipt=receipt,
        snapshot_file_present=snapshot_file_present,
    )
    pipeline_status = _pipeline_status(
        runbook=runbook,
        receipt=receipt,
        closure_pack=closure_pack,
        snapshot_file_present=snapshot_file_present,
    )
    blocked_reasons = _blocked_reasons(
        runbook=runbook,
        receipt=receipt,
        closure_pack=closure_pack,
        snapshot_file_present=snapshot_file_present,
    )
    return {
        "pipeline_status": pipeline_status,
        "writes_records": False,
        "writes_snapshot": False,
        "snapshot_path": str(snapshot_path),
        "snapshot_file_present": snapshot_file_present,
        "runbook_status": runbook["runbook_status"],
        "import_status": import_status,
        "receipt_status": None if receipt is None else receipt["receipt_status"],
        "closure_status": None if closure_pack is None else closure_pack["closure_status"],
        "final_outcome_status": final_outcome["outcome_status"],
        "new_record_count": 0 if receipt is None else receipt["new_record_count"],
        "imported_record": None if receipt is None else receipt["imported_record"],
        "blocked_reasons": blocked_reasons,
        "selected_fix": final_outcome["selected_fix"] or runbook["selected_fix"],
        "steps": _steps(
            _PipelineStepState(
                runbook=runbook,
                import_status=import_status,
                receipt=receipt,
                closure_pack=closure_pack,
                final_outcome=final_outcome,
                snapshot_file_present=snapshot_file_present,
            )
        ),
        "commands": commands,
        "next_commands": _next_commands(
            pipeline_status=pipeline_status,
            commands=commands,
            receipt=receipt,
            closure_pack=closure_pack,
        ),
        "source_runbook": runbook,
        "source_receipt": receipt,
        "source_closure_pack": closure_pack,
        "source_final_outcome": final_outcome,
        "release_tag": request.release_tag,
        "host": request.host,
        "input_path": str(request.input_path),
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "non_fabrication_policy": _non_fabrication_policy(),
    }


def build_product_fix_closure_pipeline_artifacts(
    request: ProductFixClosurePipelineRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build artifact-only closure pipeline status files."""
    report = build_product_fix_closure_pipeline(request)
    artifacts = [
        _pipeline_index_artifact(report=report, output_format=output_format),
        _pipeline_steps_artifact(report=report, output_format=output_format),
        _pipeline_commands_artifact(report=report, output_format=output_format),
    ]
    return {
        "pack_status": report["pipeline_status"],
        "writes_records": False,
        "writes_snapshot": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_product_fix_closure_pipeline_json(report: dict[str, Any]) -> str:
    """Render a product fix closure pipeline report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_closure_pipeline_markdown(report: dict[str, Any]) -> str:
    """Render a product fix closure pipeline report as Markdown."""
    return (
        "# Product Fix Closure Pipeline\n\n"
        f"Pipeline status: `{report['pipeline_status']}`\n\n"
        f"Runbook status: `{report['runbook_status']}`\n\n"
        f"Import status: `{report['import_status']}`\n\n"
        f"Receipt status: `{report['receipt_status'] or 'none'}`\n\n"
        f"Closure status: `{report['closure_status'] or 'none'}`\n\n"
        f"Final outcome: `{report['final_outcome_status']}`\n\n"
        f"Snapshot file present: `{str(report['snapshot_file_present']).lower()}`\n\n"
        f"New records: `{report['new_record_count']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Writes snapshot: `{str(report['writes_snapshot']).lower()}`\n\n"
        "## Imported Record\n\n"
        f"{_render_imported_record(report['imported_record'])}\n\n"
        "## Steps\n\n"
        f"{_render_steps(report['steps'])}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(report['next_commands'], code=True)}\n"
    )


def _runbook_request(request: ProductFixClosurePipelineRequest) -> ProductFixClosureRunbookRequest:
    return ProductFixClosureRunbookRequest(
        host=request.host,
        input_path=request.input_path,
        host_records_path=request.host_records_path,
        beta_records_path=request.beta_records_path,
        snapshot_dir=request.snapshot_dir,
        closure_output_dir=request.closure_output_dir,
        release_tag=request.release_tag,
    )


def _outcome_request(request: ProductFixClosurePipelineRequest) -> ProductFixOutcomeRequest:
    return ProductFixOutcomeRequest(
        host=request.host,
        host_records_path=request.host_records_path,
        beta_records_path=request.beta_records_path,
        release_tag=request.release_tag,
    )


def _pipeline_status(
    *,
    runbook: dict[str, Any],
    receipt: dict[str, Any] | None,
    closure_pack: dict[str, Any] | None,
    snapshot_file_present: bool,
) -> str:
    if receipt is not None and closure_pack is not None and receipt["receipt_status"] == "ready":
        return closure_pack["closure_status"]
    if not snapshot_file_present and runbook["import_allowed"]:
        return "ready_for_snapshot"
    if snapshot_file_present and runbook["import_allowed"]:
        return "ready_for_guarded_import"
    return runbook["runbook_status"]


def _import_status(
    *,
    runbook: dict[str, Any],
    receipt: dict[str, Any] | None,
    snapshot_file_present: bool,
) -> str:
    if receipt is not None and receipt["imported_record"] is not None:
        return "imported"
    if not snapshot_file_present:
        return "blocked_until_snapshot_file"
    if runbook["import_allowed"]:
        return "ready_for_guarded_import"
    return "blocked_until_runbook_ready"


def _blocked_reasons(
    *,
    runbook: dict[str, Any],
    receipt: dict[str, Any] | None,
    closure_pack: dict[str, Any] | None,
    snapshot_file_present: bool,
) -> list[str]:
    if receipt is not None and receipt["receipt_status"] == "ready":
        return []
    reasons: list[str] = []
    if not snapshot_file_present:
        reasons.append("snapshot_file_missing")
    reasons.extend(runbook["stop_conditions"])
    if receipt is not None:
        reasons.extend(receipt["blocked_reasons"])
    if closure_pack is not None:
        reasons.extend(closure_pack["blocked_reasons"])
    return _dedupe(reasons)


@dataclass(frozen=True)
class _PipelineStepState:
    runbook: dict[str, Any]
    import_status: str
    receipt: dict[str, Any] | None
    closure_pack: dict[str, Any] | None
    final_outcome: dict[str, Any]
    snapshot_file_present: bool


def _steps(state: _PipelineStepState) -> list[dict[str, str]]:
    return [
        _step(
            step_id="snapshot_file",
            status="passed" if state.snapshot_file_present else "operator_action_required",
            summary=(
                "Pre-import beta records snapshot is present."
                if state.snapshot_file_present
                else "Write the pre-import beta records snapshot before importing post-fix evidence."
            ),
        ),
        _step(
            step_id="operator_runbook",
            status=_passed_if(
                condition=state.runbook["runbook_status"] == "ready_for_operator_import" or state.receipt is not None
            ),
            summary=state.runbook["runbook_status"],
        ),
        _step(
            step_id="guarded_import",
            status=_passed_if(condition=state.import_status == "imported"),
            summary=state.import_status,
        ),
        _step(
            step_id="closure_receipt",
            status=_passed_if(condition=state.receipt is not None and state.receipt["receipt_status"] == "ready"),
            summary="not_run" if state.receipt is None else state.receipt["receipt_status"],
        ),
        _step(
            step_id="closure_pack",
            status=_passed_if(
                condition=state.closure_pack is not None and state.closure_pack["closure_status"] in _CLOSED_STATUSES
            ),
            summary="not_run" if state.closure_pack is None else state.closure_pack["closure_status"],
        ),
        _step(
            step_id="final_outcome",
            status=_passed_if(condition=state.final_outcome["outcome_status"] in {"accepted", "rejected"}),
            summary=state.final_outcome["outcome_status"],
        ),
    ]


_CLOSED_STATUSES = {"closed_accepted", "closed_rejected"}


def _step(*, step_id: str, status: str, summary: str) -> dict[str, str]:
    return {"step_id": step_id, "status": status, "summary": summary}


def _passed_if(*, condition: bool) -> str:
    return "passed" if condition else "blocked"


def _commands(*, request: ProductFixClosurePipelineRequest, snapshot_path: Path) -> dict[str, str]:
    return {
        "snapshot": (
            f"albu-mcp activation product-fix-closure-snapshot --host {request.host} "
            f"--host-records {request.host_records_path} --beta-records {request.beta_records_path} "
            f"--input {request.input_path} --output-dir {request.snapshot_dir} --format markdown"
        ),
        "import": (
            f"albu-mcp activation product-fix-closure-import --host {request.host} "
            f"--host-records {request.host_records_path} --beta-records {request.beta_records_path} "
            f"--input {request.input_path} --snapshot-dir {request.snapshot_dir} "
            f"--closure-output-dir {request.closure_output_dir} --confirm-import-ready --format json"
        ),
        "receipt": (
            f"albu-mcp activation product-fix-closure-receipt --host {request.host} "
            f"--host-records {request.host_records_path} --before-beta-records {snapshot_path} "
            f"--beta-records {request.beta_records_path} --snapshot-path {snapshot_path} "
            f"--output-dir {request.receipt_output_dir} --format markdown"
        ),
        "closure_pack": (
            f"albu-mcp activation product-fix-closure-pack --host {request.host} "
            f"--host-records {request.host_records_path} --before-beta-records {snapshot_path} "
            f"--beta-records {request.beta_records_path} --output-dir {request.closure_output_dir} --format markdown"
        ),
        "final_outcome": (
            f"albu-mcp activation product-fix-outcome --host {request.host} "
            f"--host-records {request.host_records_path} --beta-records {request.beta_records_path} "
            f"--output-dir {request.final_outcome_output_dir} --format markdown"
        ),
    }


def _next_commands(
    *,
    pipeline_status: str,
    commands: dict[str, str],
    receipt: dict[str, Any] | None,
    closure_pack: dict[str, Any] | None,
) -> list[str]:
    if pipeline_status == "ready_for_snapshot":
        return [commands["snapshot"], commands["import"], commands["receipt"]]
    if receipt is None or receipt["receipt_status"] != "ready":
        return [commands["import"], commands["receipt"]]
    if closure_pack is not None and closure_pack["closure_status"] in _CLOSED_STATUSES:
        return [commands["receipt"], commands["closure_pack"], commands["final_outcome"]]
    return [commands["receipt"], commands["closure_pack"]]


def _pipeline_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "product_fix_closure_pipeline_index",
        "pipeline_status": report["pipeline_status"],
        "writes_records": False,
        "writes_snapshot": False,
        "snapshot_path": report["snapshot_path"],
        "snapshot_file_present": report["snapshot_file_present"],
        "runbook_status": report["runbook_status"],
        "import_status": report["import_status"],
        "receipt_status": report["receipt_status"],
        "closure_status": report["closure_status"],
        "final_outcome_status": report["final_outcome_status"],
        "new_record_count": report["new_record_count"],
        "blocked_reasons": report["blocked_reasons"],
    }
    return {
        "filename": f"product-fix-closure-pipeline-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_index_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _pipeline_steps_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "closure_pipeline_steps",
        "pipeline_status": report["pipeline_status"],
        "writes_records": False,
        "writes_snapshot": False,
        "steps": report["steps"],
    }
    return {
        "filename": f"closure-pipeline-steps.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_steps_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _pipeline_commands_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "closure_pipeline_commands",
        "pipeline_status": report["pipeline_status"],
        "writes_records": False,
        "writes_snapshot": False,
        "commands": report["commands"],
        "next_commands": report["next_commands"],
        "non_fabrication_policy": report["non_fabrication_policy"],
    }
    return {
        "filename": f"closure-pipeline-commands.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_commands_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _render_index_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Product Fix Closure Pipeline Index\n\n"
        f"Pipeline status: `{payload['pipeline_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Writes snapshot: `{str(payload['writes_snapshot']).lower()}`\n\n"
        f"Snapshot file present: `{str(payload['snapshot_file_present']).lower()}`\n\n"
        f"Runbook status: `{payload['runbook_status']}`\n\n"
        f"Receipt status: `{payload['receipt_status'] or 'none'}`\n\n"
        f"Closure status: `{payload['closure_status'] or 'none'}`\n\n"
        f"Final outcome: `{payload['final_outcome_status']}`\n\n"
        f"New records: `{payload['new_record_count']}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(payload['blocked_reasons'], code=True)}\n"
    )


def _render_steps_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Closure Pipeline Steps\n\n"
        f"Pipeline status: `{payload['pipeline_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Writes snapshot: `{str(payload['writes_snapshot']).lower()}`\n\n"
        f"{_render_steps(payload['steps'])}\n"
    )


def _render_commands_artifact_markdown(payload: dict[str, Any]) -> str:
    commands = [f"{name}: {command}" for name, command in payload["commands"].items()]
    return (
        "# Closure Pipeline Commands\n\n"
        f"Pipeline status: `{payload['pipeline_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Writes snapshot: `{str(payload['writes_snapshot']).lower()}`\n\n"
        "## Commands\n\n"
        f"{_render_list(commands, code=True)}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n\n"
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


def _render_steps(steps: list[dict[str, str]]) -> str:
    return "\n".join(f"- `{step['step_id']}`: `{step['status']}` - {step['summary']}" for step in steps)


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
    msg = f"unsupported product fix closure pipeline artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported product fix closure pipeline artifact format: {output_format}"
    raise ValueError(msg)


def _non_fabrication_policy() -> str:
    return (
        "The closure pipeline is report-only. It does not write beta records or snapshots; it only reads "
        "the current draft, snapshot file, beta records, and derived no-write closure reports."
    )
