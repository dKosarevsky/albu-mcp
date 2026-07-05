"""No-write capture pack for post-fix beta outcome evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import BetaResponseDraft, TriageBucket, WorkflowId
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.product_fix_outcome import ProductFixOutcomeRequest, build_product_fix_outcome

_ALLOWED_STATUSES = ["passed", "blocked", "needs_followup"]
_POST_FIX_WORKFLOW_BY_BUCKET: dict[TriageBucket, WorkflowId] = {
    "dataset_quality_gap": "dataset_health_before_training",
    "docs_gap": "robustness_distortion_variants",
    "host_setup_gap": "noisy_preview_tuning",
    "review_agent_v3_gap": "noisy_preview_tuning",
    "workflow_fit_gap": "robustness_distortion_variants",
}


@dataclass(frozen=True)
class ProductFixOutcomeCaptureRequest:
    """Inputs for building a post-fix beta evidence capture pack."""

    host: HostName
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"
    participant_role: str = "ML practitioner"
    attempt_date: str | None = None


def build_product_fix_outcome_capture(request: ProductFixOutcomeCaptureRequest) -> dict[str, Any]:
    """Build a no-write pack for recording real post-fix beta outcome evidence."""
    outcome = build_product_fix_outcome(
        ProductFixOutcomeRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    if not outcome["fix_validated"]:
        return _blocked_capture_report(request=request, outcome=outcome)
    if outcome["outcome_status"] in {"accepted", "rejected"}:
        return _closed_capture_report(request=request, outcome=outcome)

    selected_fix = outcome["selected_fix"]
    triage_bucket = selected_fix["triage_bucket"]
    workflow_id = post_fix_workflow_for_bucket(triage_bucket)
    response_filename = f"post-fix-{workflow_id.replace('_', '-')}-beta-response.json"
    response = _post_fix_beta_response(
        workflow_id=workflow_id,
        triage_bucket=triage_bucket,
        participant_role=request.participant_role,
        attempt_date=_resolve_attempt_date(request.attempt_date),
    )
    validation_commands = [
        f"albu-mcp beta response-validate --input docs/product-fix-outcome-capture/{response_filename} --format json",
        (
            "albu-mcp activation product-fix-outcome-import-guard "
            f"--host {request.host} --input docs/product-fix-outcome-capture/{response_filename} --format json"
        ),
    ]
    import_commands = [
        (
            "albu-mcp beta response-import "
            f"--input docs/product-fix-outcome-capture/{response_filename} "
            f"--path {request.beta_records_path}"
        )
    ]
    return {
        "capture_status": "ready_to_capture",
        "outcome_status": outcome["outcome_status"],
        "writes_records": False,
        "privacy_policy": "redacted_only",
        "allowed_statuses": _ALLOWED_STATUSES,
        "blocked_reasons": [],
        "selected_fix": selected_fix,
        "post_fix_beta_response_filename": response_filename,
        "post_fix_beta_response": response,
        "reviewer_checklist": _reviewer_checklist(triage_bucket=triage_bucket),
        "validation_commands": validation_commands,
        "import_commands": import_commands,
        "source_outcome": outcome,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": [
            *validation_commands,
            *import_commands,
            f"albu-mcp activation product-fix-outcome --host {request.host} --format json",
        ],
    }


def build_product_fix_outcome_capture_artifacts(
    request: ProductFixOutcomeCaptureRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build artifact-only post-fix outcome capture files."""
    report = build_product_fix_outcome_capture(request)
    artifacts = [
        _capture_index_artifact(report=report, output_format=output_format),
        _post_fix_response_artifact(report=report),
        _capture_checklist_artifact(report=report, output_format=output_format),
        _capture_commands_artifact(report=report, output_format=output_format),
    ]
    return {
        "pack_status": report["capture_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_product_fix_outcome_capture_json(report: dict[str, Any]) -> str:
    """Render a product fix outcome capture report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_outcome_capture_markdown(report: dict[str, Any]) -> str:
    """Render a product fix outcome capture report as Markdown."""
    response_filename = report["post_fix_beta_response_filename"] or "none"
    return (
        "# Product Fix Outcome Capture\n\n"
        f"Capture status: `{report['capture_status']}`\n\n"
        f"Outcome status: `{report['outcome_status']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Privacy policy: `{report['privacy_policy']}`\n\n"
        f"Post-fix beta response: `{response_filename}`\n\n"
        "## Reviewer Checklist\n\n"
        f"{_render_list(report['reviewer_checklist'])}\n\n"
        "## Commands\n\n"
        f"{_render_list([*report['validation_commands'], *report['import_commands']], code=True)}\n"
    )


def post_fix_workflow_for_bucket(triage_bucket: TriageBucket) -> WorkflowId:
    """Return the canonical post-fix beta workflow for a product fix triage bucket."""
    return _POST_FIX_WORKFLOW_BY_BUCKET[triage_bucket]


def _blocked_capture_report(
    *,
    request: ProductFixOutcomeCaptureRequest,
    outcome: dict[str, Any],
) -> dict[str, Any]:
    return {
        "capture_status": "blocked_until_product_fix_validation",
        "outcome_status": outcome["outcome_status"],
        "writes_records": False,
        "privacy_policy": "redacted_only",
        "allowed_statuses": _ALLOWED_STATUSES,
        "blocked_reasons": outcome["blocked_reasons"],
        "selected_fix": outcome["selected_fix"],
        "post_fix_beta_response_filename": None,
        "post_fix_beta_response": None,
        "reviewer_checklist": [],
        "validation_commands": [],
        "import_commands": [],
        "source_outcome": outcome,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": [
            f"albu-mcp activation product-fix-validation --host {request.host} --format json",
            *outcome["next_commands"],
        ],
    }


def _closed_capture_report(
    *,
    request: ProductFixOutcomeCaptureRequest,
    outcome: dict[str, Any],
) -> dict[str, Any]:
    return {
        "capture_status": f"closed_fix_{outcome['outcome_status']}",
        "outcome_status": outcome["outcome_status"],
        "writes_records": False,
        "privacy_policy": "redacted_only",
        "allowed_statuses": _ALLOWED_STATUSES,
        "blocked_reasons": [],
        "selected_fix": outcome["selected_fix"],
        "post_fix_beta_response_filename": None,
        "post_fix_beta_response": None,
        "reviewer_checklist": [],
        "validation_commands": [],
        "import_commands": [],
        "source_outcome": outcome,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": [f"albu-mcp activation product-fix-outcome --host {request.host} --format markdown"],
    }


def _post_fix_beta_response(
    *,
    workflow_id: WorkflowId,
    triage_bucket: TriageBucket,
    participant_role: str,
    attempt_date: str,
) -> dict[str, Any]:
    draft = BetaResponseDraft(
        workflow_id=workflow_id,
        status="needs_followup",
        attempt_date=date.fromisoformat(attempt_date),
        participant_role=participant_role,
        summary=(
            f"Post-fix {triage_bucket} outcome; replace with a redacted reviewer-observed summary "
            "of whether the fix resolved the workflow."
        ),
        triage_bucket=triage_bucket,
        artifact_refs=["docs/assets/demo/demo_report.md"],
        private_data_included=False,
    )
    return draft.model_dump(mode="json")


def _reviewer_checklist(*, triage_bucket: str) -> list[str]:
    return [
        "Run the post-fix workflow with a real MCP host and a reviewer-observed beta participant or operator.",
        "Set status to passed only after the post-fix retry is reviewer-observed.",
        "Set status to blocked if the same product gap remains after the fix.",
        "Keep status as needs_followup when the run is useful but not enough to accept or reject the fix.",
        f"Keep triage_bucket as {triage_bucket} unless the observed issue clearly moved elsewhere.",
        "Keep private_data_included=false and use only redacted artifact refs.",
    ]


def _resolve_attempt_date(attempt_date: str | None) -> str:
    if attempt_date is not None:
        return attempt_date
    return datetime.now(timezone.utc).date().isoformat()


def _capture_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "product_fix_outcome_capture_index",
        "capture_status": report["capture_status"],
        "outcome_status": report["outcome_status"],
        "writes_records": False,
        "privacy_policy": report["privacy_policy"],
        "selected_fix": report["selected_fix"],
        "post_fix_beta_response_filename": report["post_fix_beta_response_filename"],
        "blocked_reasons": report["blocked_reasons"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"product-fix-outcome-capture-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_capture_index_markdown(payload),
            output_format=output_format,
        ),
    }


def _post_fix_response_artifact(*, report: dict[str, Any]) -> dict[str, str]:
    response = report["post_fix_beta_response"]
    response_filename = report["post_fix_beta_response_filename"] or "post-fix-beta-response.json"
    payload = {} if response is None else response
    return {
        "filename": response_filename,
        "content": json.dumps(payload, indent=2, sort_keys=True) + "\n",
    }


def _capture_checklist_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "capture_checklist",
        "capture_status": report["capture_status"],
        "writes_records": False,
        "reviewer_checklist": report["reviewer_checklist"],
    }
    return {
        "filename": f"capture-checklist.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_capture_checklist_markdown(payload),
            output_format=output_format,
        ),
    }


def _capture_commands_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "capture_commands",
        "capture_status": report["capture_status"],
        "writes_records": False,
        "validation_commands": report["validation_commands"],
        "import_commands": report["import_commands"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"capture-commands.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_capture_commands_markdown(payload),
            output_format=output_format,
        ),
    }


def _render_capture_index_markdown(payload: dict[str, Any]) -> str:
    response_filename = payload["post_fix_beta_response_filename"] or "none"
    return (
        "# Product Fix Outcome Capture Index\n\n"
        f"Capture status: `{payload['capture_status']}`\n\n"
        f"Outcome status: `{payload['outcome_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Privacy policy: `{payload['privacy_policy']}`\n\n"
        f"Post-fix beta response: `{response_filename}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(payload['blocked_reasons'], code=True)}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_capture_checklist_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Capture Checklist\n\n"
        f"Capture status: `{payload['capture_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"{_render_list(payload['reviewer_checklist'])}\n"
    )


def _render_capture_commands_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Capture Commands\n\n"
        f"Capture status: `{payload['capture_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        "## Validate\n\n"
        f"{_render_list(payload['validation_commands'], code=True)}\n\n"
        "## Import\n\n"
        f"{_render_list(payload['import_commands'], code=True)}\n\n"
        "## Next\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


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
    msg = f"unsupported product fix outcome capture artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported product fix outcome capture artifact format: {output_format}"
    raise ValueError(msg)
