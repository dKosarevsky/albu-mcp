"""No-write rehearsal for guarded post-fix outcome evidence imports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.product_fix_outcome_capture import (
    ProductFixOutcomeCaptureRequest,
    build_product_fix_outcome_capture,
)
from albumentationsx_mcp.product_fix_outcome_import_guard import (
    ProductFixOutcomeImportGuardRequest,
    build_product_fix_outcome_import_guard,
)

_PROJECTED_OUTCOME_BY_DRAFT_STATUS = {
    "passed": "accepted",
    "blocked": "rejected",
    "needs_followup": "needs_more_evidence",
}


@dataclass(frozen=True)
class ProductFixOutcomeRehearsalRequest:
    """Inputs for rehearsing a post-fix outcome capture and guarded import."""

    host: HostName
    input_path: Path
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_product_fix_outcome_rehearsal(request: ProductFixOutcomeRehearsalRequest) -> dict[str, Any]:
    """Build a no-write rehearsal report for one post-fix outcome draft."""
    capture = build_product_fix_outcome_capture(
        ProductFixOutcomeCaptureRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    if capture["capture_status"] != "ready_to_capture":
        return _blocked_until_capture_ready_report(request=request, capture=capture)

    import_guard = build_product_fix_outcome_import_guard(
        ProductFixOutcomeImportGuardRequest(
            host=request.host,
            input_path=request.input_path,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    if import_guard["guard_status"] != "ready_to_import":
        return _blocked_until_import_guard_report(request=request, capture=capture, import_guard=import_guard)

    projected_outcome = _project_outcome_status(import_guard)
    return _ready_for_guarded_import_report(
        request=request,
        capture=capture,
        import_guard=import_guard,
        projected_outcome=projected_outcome,
    )


def build_product_fix_outcome_rehearsal_artifacts(
    request: ProductFixOutcomeRehearsalRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build artifact-only rehearsal files without importing records."""
    report = build_product_fix_outcome_rehearsal(request)
    artifacts = [
        _rehearsal_index_artifact(report=report, output_format=output_format),
        _rehearsal_steps_artifact(report=report, output_format=output_format),
        _stop_conditions_artifact(report=report, output_format=output_format),
    ]
    return {
        "pack_status": report["rehearsal_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_product_fix_outcome_rehearsal_json(report: dict[str, Any]) -> str:
    """Render a product fix outcome rehearsal report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_outcome_rehearsal_markdown(report: dict[str, Any]) -> str:
    """Render a product fix outcome rehearsal report as Markdown."""
    return (
        "# Product Fix Outcome Rehearsal\n\n"
        f"Rehearsal status: `{report['rehearsal_status']}`\n\n"
        f"Capture status: `{report['capture_status']}`\n\n"
        f"Import guard status: `{report['import_guard_status'] or 'none'}`\n\n"
        f"Projected outcome: `{report['projected_outcome_status'] or 'none'}`\n\n"
        f"Import allowed: `{str(report['import_allowed']).lower()}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Input path: `{report['input_path']}`\n\n"
        "## Stop Conditions\n\n"
        f"{_render_stop_conditions(report['stop_conditions'])}\n\n"
        "## Rehearsal Steps\n\n"
        f"{_render_steps(report['rehearsal_steps'])}\n"
    )


def _blocked_until_capture_ready_report(
    *,
    request: ProductFixOutcomeRehearsalRequest,
    capture: dict[str, Any],
) -> dict[str, Any]:
    stop_conditions = ["capture_status_not_ready", *capture["blocked_reasons"]]
    return _base_report(
        request=request,
        state=_RehearsalReportState(
            rehearsal_status="blocked_until_capture_ready",
            capture=capture,
            import_guard=None,
            projected_outcome=None,
            stop_conditions=stop_conditions,
            rehearsal_steps=[
                _step("capture_ready", "blocked", capture["capture_status"]),
                _step("draft_import_guard", "not_run", "Capture must be ready before validating a post-fix draft."),
            ],
            next_commands=capture["next_commands"],
        ),
    )


def _blocked_until_import_guard_report(
    *,
    request: ProductFixOutcomeRehearsalRequest,
    capture: dict[str, Any],
    import_guard: dict[str, Any],
) -> dict[str, Any]:
    stop_conditions = ["post_fix_import_guard_blocked", *import_guard["blocked_reasons"]]
    return _base_report(
        request=request,
        state=_RehearsalReportState(
            rehearsal_status="blocked_until_post_fix_import_guard",
            capture=capture,
            import_guard=import_guard,
            projected_outcome=None,
            stop_conditions=stop_conditions,
            rehearsal_steps=[
                _step("capture_ready", "passed", capture["capture_status"]),
                _step("draft_import_guard", "blocked", import_guard["guard_status"]),
                _step("projected_outcome", "not_run", "Draft cannot project an outcome until import guard passes."),
            ],
            next_commands=import_guard["next_commands"],
        ),
    )


def _ready_for_guarded_import_report(
    *,
    request: ProductFixOutcomeRehearsalRequest,
    capture: dict[str, Any],
    import_guard: dict[str, Any],
    projected_outcome: str,
) -> dict[str, Any]:
    return _base_report(
        request=request,
        state=_RehearsalReportState(
            rehearsal_status="ready_for_guarded_import",
            capture=capture,
            import_guard=import_guard,
            projected_outcome=projected_outcome,
            stop_conditions=[],
            rehearsal_steps=[
                _step("capture_ready", "passed", capture["capture_status"]),
                _step("draft_import_guard", "passed", import_guard["guard_status"]),
                _step("projected_outcome", "passed", projected_outcome),
                _step(
                    "guarded_import", "operator_action_required", "Run the import command only after reviewer approval."
                ),
            ],
            next_commands=import_guard["next_commands"],
        ),
    )


@dataclass(frozen=True)
class _RehearsalReportState:
    rehearsal_status: str
    capture: dict[str, Any]
    import_guard: dict[str, Any] | None
    projected_outcome: str | None
    stop_conditions: list[str]
    rehearsal_steps: list[dict[str, str]]
    next_commands: list[str]


def _base_report(
    *,
    request: ProductFixOutcomeRehearsalRequest,
    state: _RehearsalReportState,
) -> dict[str, Any]:
    import_guard = state.import_guard
    return {
        "rehearsal_status": state.rehearsal_status,
        "capture_status": state.capture["capture_status"],
        "import_guard_status": None if import_guard is None else import_guard["guard_status"],
        "projected_outcome_status": state.projected_outcome,
        "writes_records": False,
        "import_allowed": False if import_guard is None else import_guard["import_allowed"],
        "selected_fix": state.capture["selected_fix"],
        "input_path": str(request.input_path),
        "stop_conditions": state.stop_conditions,
        "rehearsal_steps": state.rehearsal_steps,
        "source_capture": state.capture,
        "source_import_guard": import_guard,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": state.next_commands,
    }


def _project_outcome_status(import_guard: dict[str, Any]) -> str:
    draft_status = import_guard["draft"]["status"]
    return _PROJECTED_OUTCOME_BY_DRAFT_STATUS[draft_status]


def _step(step_id: str, status: str, summary: str) -> dict[str, str]:
    return {
        "id": step_id,
        "status": status,
        "summary": summary,
    }


def _rehearsal_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "product_fix_outcome_rehearsal_index",
        "rehearsal_status": report["rehearsal_status"],
        "capture_status": report["capture_status"],
        "import_guard_status": report["import_guard_status"],
        "projected_outcome_status": report["projected_outcome_status"],
        "import_allowed": report["import_allowed"],
        "writes_records": False,
        "input_path": report["input_path"],
        "selected_fix": report["selected_fix"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"product-fix-outcome-rehearsal-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_index_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _rehearsal_steps_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "rehearsal_steps",
        "rehearsal_status": report["rehearsal_status"],
        "writes_records": False,
        "rehearsal_steps": report["rehearsal_steps"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"rehearsal-steps.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_steps_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _stop_conditions_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "stop_conditions",
        "rehearsal_status": report["rehearsal_status"],
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
        "# Product Fix Outcome Rehearsal Index\n\n"
        f"Rehearsal status: `{payload['rehearsal_status']}`\n\n"
        f"Capture status: `{payload['capture_status']}`\n\n"
        f"Import guard status: `{payload['import_guard_status'] or 'none'}`\n\n"
        f"Projected outcome: `{payload['projected_outcome_status'] or 'none'}`\n\n"
        f"Import allowed: `{str(payload['import_allowed']).lower()}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Input path: `{payload['input_path']}`\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_steps_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Rehearsal Steps\n\n"
        f"Rehearsal status: `{payload['rehearsal_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"{_render_steps(payload['rehearsal_steps'])}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_stop_conditions_artifact_markdown(payload: dict[str, Any]) -> str:
    if not payload["stop_conditions"]:
        rendered_conditions = "No active stop conditions."
    else:
        rendered_conditions = _render_list(payload["stop_conditions"], code=True)
    return (
        "# Stop Conditions\n\n"
        f"Rehearsal status: `{payload['rehearsal_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"{rendered_conditions}\n"
    )


def _render_steps(steps: list[dict[str, str]]) -> str:
    if not steps:
        return "- none"
    return "\n\n".join(
        (f"### {step['id']}\n\nStatus: `{step['status']}`\n\nSummary: {step['summary']}") for step in steps
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
    msg = f"unsupported product fix outcome rehearsal artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported product fix outcome rehearsal artifact format: {output_format}"
    raise ValueError(msg)
