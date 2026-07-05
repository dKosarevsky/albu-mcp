"""Operator runbook for closing one validated product fix with real evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.product_fix_closure_snapshot import (
    ProductFixClosureSnapshotRequest,
    build_product_fix_closure_snapshot,
)
from albumentationsx_mcp.product_fix_outcome import ProductFixOutcomeRequest, build_product_fix_outcome
from albumentationsx_mcp.product_fix_outcome_capture import (
    ProductFixOutcomeCaptureRequest,
    build_product_fix_outcome_capture,
)
from albumentationsx_mcp.product_fix_outcome_import_guard import (
    ProductFixOutcomeImportGuardRequest,
    build_product_fix_outcome_import_guard,
)
from albumentationsx_mcp.product_fix_outcome_rehearsal import (
    ProductFixOutcomeRehearsalRequest,
    build_product_fix_outcome_rehearsal,
)


@dataclass(frozen=True)
class ProductFixClosureRunbookRequest:
    """Inputs for building a no-write operator runbook for product fix closure."""

    host: HostName
    input_path: Path
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    snapshot_dir: Path = Path("docs/product-fix-closure-snapshot")
    closure_output_dir: Path = Path("docs/product-fix-closure-pack")
    release_tag: str = "v1.15.0-rc.1"


def build_product_fix_closure_runbook(request: ProductFixClosureRunbookRequest) -> dict[str, Any]:
    """Build a no-write closure runbook from capture through final outcome confirmation."""
    capture = build_product_fix_outcome_capture(
        ProductFixOutcomeCaptureRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    import_guard = build_product_fix_outcome_import_guard(
        ProductFixOutcomeImportGuardRequest(
            host=request.host,
            input_path=request.input_path,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    rehearsal = build_product_fix_outcome_rehearsal(
        ProductFixOutcomeRehearsalRequest(
            host=request.host,
            input_path=request.input_path,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    snapshot = build_product_fix_closure_snapshot(
        ProductFixClosureSnapshotRequest(
            host=request.host,
            input_path=request.input_path,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            snapshot_dir=request.snapshot_dir,
            closure_output_dir=request.closure_output_dir,
            release_tag=request.release_tag,
        )
    )
    current_outcome = build_product_fix_outcome(
        ProductFixOutcomeRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    runbook_status = _runbook_status(capture=capture, import_guard=import_guard, snapshot=snapshot)
    stop_conditions = _stop_conditions(
        runbook_status=runbook_status,
        capture=capture,
        import_guard=import_guard,
        rehearsal=rehearsal,
        snapshot=snapshot,
    )
    operator_sequence = _operator_sequence(
        request=request,
        capture=capture,
        import_guard=import_guard,
        rehearsal=rehearsal,
        snapshot=snapshot,
    )
    return {
        "runbook_status": runbook_status,
        "writes_records": False,
        "import_allowed": snapshot["import_allowed"],
        "capture_status": capture["capture_status"],
        "guard_status": import_guard["guard_status"],
        "rehearsal_status": rehearsal["rehearsal_status"],
        "snapshot_status": snapshot["snapshot_status"],
        "current_outcome_status": current_outcome["outcome_status"],
        "selected_fix": current_outcome["selected_fix"],
        "input_path": str(request.input_path),
        "snapshot_path": snapshot["snapshot_path"],
        "stop_conditions": stop_conditions,
        "operator_sequence": operator_sequence,
        "source_capture": capture,
        "source_import_guard": import_guard,
        "source_rehearsal": rehearsal,
        "source_snapshot": snapshot,
        "source_current_outcome": current_outcome,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": _next_commands(operator_sequence),
        "non_fabrication_policy": _non_fabrication_policy(),
    }


def build_product_fix_closure_runbook_artifacts(
    request: ProductFixClosureRunbookRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build no-write product fix closure runbook artifacts."""
    report = build_product_fix_closure_runbook(request)
    artifacts = [
        _runbook_index_artifact(report=report, output_format=output_format),
        _operator_sequence_artifact(report=report, output_format=output_format),
        _stop_conditions_artifact(report=report, output_format=output_format),
    ]
    return {
        "pack_status": report["runbook_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_product_fix_closure_runbook_json(report: dict[str, Any]) -> str:
    """Render a product fix closure runbook report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_closure_runbook_markdown(report: dict[str, Any]) -> str:
    """Render a product fix closure runbook report as Markdown."""
    return (
        "# Product Fix Closure Runbook\n\n"
        f"Runbook status: `{report['runbook_status']}`\n\n"
        f"Import allowed: `{str(report['import_allowed']).lower()}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Capture status: `{report['capture_status']}`\n\n"
        f"Guard status: `{report['guard_status']}`\n\n"
        f"Rehearsal status: `{report['rehearsal_status']}`\n\n"
        f"Snapshot status: `{report['snapshot_status']}`\n\n"
        f"Current outcome: `{report['current_outcome_status']}`\n\n"
        f"Input path: `{report['input_path']}`\n\n"
        f"Snapshot path: `{report['snapshot_path']}`\n\n"
        "## Operator Sequence\n\n"
        f"{_render_operator_sequence(report['operator_sequence'])}\n\n"
        "## Stop Conditions\n\n"
        f"{_render_stop_conditions(report['stop_conditions'])}\n"
    )


def _runbook_status(
    *,
    capture: dict[str, Any],
    import_guard: dict[str, Any],
    snapshot: dict[str, Any],
) -> str:
    if snapshot["snapshot_status"] == "ready_for_import":
        return "ready_for_operator_import"
    if capture["capture_status"] != "ready_to_capture":
        return "blocked_until_capture_ready"
    if import_guard["guard_status"] != "ready_to_import":
        return "blocked_until_post_fix_import_guard"
    return snapshot["snapshot_status"]


def _stop_conditions(
    *,
    runbook_status: str,
    capture: dict[str, Any],
    import_guard: dict[str, Any],
    rehearsal: dict[str, Any],
    snapshot: dict[str, Any],
) -> list[str]:
    if runbook_status == "ready_for_operator_import":
        return []
    if runbook_status == "blocked_until_capture_ready":
        return ["capture_status_not_ready", *capture["blocked_reasons"]]
    if runbook_status == "blocked_until_post_fix_import_guard":
        return ["post_fix_import_guard_blocked", *import_guard["blocked_reasons"]]
    if rehearsal["rehearsal_status"] != "ready_for_guarded_import":
        return rehearsal["stop_conditions"]
    return snapshot["blocked_reasons"]


def _operator_sequence(
    *,
    request: ProductFixClosureRunbookRequest,
    capture: dict[str, Any],
    import_guard: dict[str, Any],
    rehearsal: dict[str, Any],
    snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    commands = _operator_commands(request=request, snapshot=snapshot)
    return [
        _sequence_step(
            step_id="capture_post_fix_response",
            status="passed" if capture["capture_status"] == "ready_to_capture" else "blocked",
            summary=capture["capture_status"],
            command=commands["capture"],
        ),
        _sequence_step(
            step_id="guard_post_fix_draft",
            status="passed" if import_guard["guard_status"] == "ready_to_import" else "blocked",
            summary=import_guard["guard_status"],
            command=commands["guard"],
        ),
        _sequence_step(
            step_id="rehearse_import_and_outcome",
            status="passed" if rehearsal["rehearsal_status"] == "ready_for_guarded_import" else "blocked",
            summary=rehearsal["rehearsal_status"],
            command=commands["rehearsal"],
        ),
        _sequence_step(
            step_id="snapshot_before_import",
            status="passed" if snapshot["snapshot_status"] == "ready_for_import" else "blocked",
            summary=snapshot["snapshot_status"],
            command=commands["snapshot"],
        ),
        _sequence_step(
            step_id="import_post_fix_response",
            status="operator_action_required" if snapshot["import_allowed"] else "not_run",
            summary="Import the guarded post-fix beta response after reviewer approval.",
            command=snapshot["import_command"],
        ),
        _sequence_step(
            step_id="build_closure_pack",
            status="operator_action_required" if snapshot["import_allowed"] else "not_run",
            summary="Build the before/after closure pack after the import command writes the record.",
            command=snapshot["closure_command"],
        ),
        _sequence_step(
            step_id="confirm_final_outcome",
            status="operator_action_required" if snapshot["import_allowed"] else "not_run",
            summary="Confirm product-fix outcome after the closure pack shows the new evidence record.",
            command=commands["final_outcome"],
        ),
    ]


def _operator_commands(
    *,
    request: ProductFixClosureRunbookRequest,
    snapshot: dict[str, Any],
) -> dict[str, str | None]:
    return {
        "capture": (
            f"albu-mcp activation product-fix-outcome-capture --host {request.host} "
            "--output-dir docs/product-fix-outcome-capture --format markdown"
        ),
        "guard": (
            f"albu-mcp activation product-fix-outcome-import-guard --host {request.host} "
            f"--input {request.input_path} --output-dir docs/product-fix-outcome-import-guard --format markdown"
        ),
        "rehearsal": (
            f"albu-mcp activation product-fix-outcome-rehearsal --host {request.host} "
            f"--input {request.input_path} --output-dir docs/product-fix-outcome-rehearsal --format markdown"
        ),
        "snapshot": (
            f"albu-mcp activation product-fix-closure-snapshot --host {request.host} "
            f"--input {request.input_path} --output-dir {request.snapshot_dir} --format markdown"
        ),
        "import": snapshot["import_command"],
        "closure": snapshot["closure_command"],
        "final_outcome": (
            f"albu-mcp activation product-fix-outcome --host {request.host} "
            "--output-dir docs/product-fix-outcome --format markdown"
        ),
    }


def _sequence_step(*, step_id: str, status: str, summary: str, command: str | None) -> dict[str, Any]:
    return {
        "id": step_id,
        "status": status,
        "summary": summary,
        "command": command,
    }


def _next_commands(operator_sequence: list[dict[str, Any]]) -> list[str]:
    commands: list[str] = []
    for step in operator_sequence:
        command = step["command"]
        if command is not None and step["status"] != "not_run":
            commands.append(command)
    return commands


def _runbook_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "product_fix_closure_runbook_index",
        "runbook_status": report["runbook_status"],
        "import_allowed": report["import_allowed"],
        "writes_records": False,
        "capture_status": report["capture_status"],
        "guard_status": report["guard_status"],
        "rehearsal_status": report["rehearsal_status"],
        "snapshot_status": report["snapshot_status"],
        "current_outcome_status": report["current_outcome_status"],
        "selected_fix": report["selected_fix"],
        "input_path": report["input_path"],
        "snapshot_path": report["snapshot_path"],
        "stop_conditions": report["stop_conditions"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"product-fix-closure-runbook-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_index_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _operator_sequence_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "operator_sequence",
        "runbook_status": report["runbook_status"],
        "writes_records": False,
        "operator_sequence": report["operator_sequence"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"operator-sequence.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_sequence_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _stop_conditions_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "stop_conditions",
        "runbook_status": report["runbook_status"],
        "writes_records": False,
        "stop_conditions": report["stop_conditions"],
    }
    return {
        "filename": f"stop-conditions.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_stop_conditions_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _render_index_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Product Fix Closure Runbook Index\n\n"
        f"Runbook status: `{payload['runbook_status']}`\n\n"
        f"Import allowed: `{str(payload['import_allowed']).lower()}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Capture status: `{payload['capture_status']}`\n\n"
        f"Guard status: `{payload['guard_status']}`\n\n"
        f"Rehearsal status: `{payload['rehearsal_status']}`\n\n"
        f"Snapshot status: `{payload['snapshot_status']}`\n\n"
        f"Current outcome: `{payload['current_outcome_status']}`\n\n"
        f"Input path: `{payload['input_path']}`\n\n"
        f"Snapshot path: `{payload['snapshot_path']}`\n\n"
        "## Stop Conditions\n\n"
        f"{_render_stop_conditions(payload['stop_conditions'])}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_sequence_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Operator Sequence\n\n"
        f"Runbook status: `{payload['runbook_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"{_render_operator_sequence(payload['operator_sequence'])}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_stop_conditions_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Stop Conditions\n\n"
        f"Runbook status: `{payload['runbook_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"{_render_stop_conditions(payload['stop_conditions'])}\n"
    )


def _render_operator_sequence(sequence: list[dict[str, Any]]) -> str:
    if not sequence:
        return "- none"
    return "\n\n".join(
        (
            f"### {step['id']}\n\n"
            f"Status: `{step['status']}`\n\n"
            f"Summary: {step['summary']}\n\n"
            f"Command: `{step['command'] or 'none'}`"
        )
        for step in sequence
    )


def _render_stop_conditions(stop_conditions: list[str]) -> str:
    if not stop_conditions:
        return "No active stop conditions."
    return _render_list(stop_conditions, code=True)


def _render_list(items: list[str], *, code: bool = False) -> str:
    if not items:
        return "- none"
    if code:
        return "\n".join(f"- `{item}`" for item in items)
    return "\n".join(f"- {item}" for item in items)


def _artifact_extension(output_format: str) -> str:
    if output_format == "markdown":
        return "md"
    if output_format == "json":
        return "json"
    msg = f"unsupported product fix closure runbook artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported product fix closure runbook artifact format: {output_format}"
    raise ValueError(msg)


def _non_fabrication_policy() -> str:
    return (
        "The closure runbook is report-only. It composes existing no-write checks and prints the explicit "
        "operator import command, but never imports post-fix evidence by itself."
    )
