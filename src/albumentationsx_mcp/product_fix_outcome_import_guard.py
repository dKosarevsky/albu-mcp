"""No-write import guard for post-fix beta outcome drafts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import BetaResponseDraft, load_beta_response_draft
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.product_fix_outcome import ProductFixOutcomeRequest, build_product_fix_outcome
from albumentationsx_mcp.product_fix_outcome_capture import post_fix_workflow_for_bucket


@dataclass(frozen=True)
class ProductFixOutcomeImportGuardRequest:
    """Inputs for guarding a post-fix beta response import."""

    host: HostName
    input_path: Path
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_product_fix_outcome_import_guard(request: ProductFixOutcomeImportGuardRequest) -> dict[str, Any]:
    """Build a no-write guard report before importing one post-fix beta response draft."""
    outcome = build_product_fix_outcome(
        ProductFixOutcomeRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    if not outcome["fix_validated"]:
        return _blocked_until_validation_report(request=request, outcome=outcome)
    if outcome["outcome_status"] in {"accepted", "rejected"}:
        return _blocked_closed_outcome_report(request=request, outcome=outcome)

    draft = load_beta_response_draft(request.input_path)
    selected_fix = outcome["selected_fix"]
    expected_triage_bucket = selected_fix["triage_bucket"]
    expected_workflow_id = post_fix_workflow_for_bucket(expected_triage_bucket)
    draft_checks = _build_draft_checks(
        draft=draft,
        expected_workflow_id=expected_workflow_id,
        expected_triage_bucket=expected_triage_bucket,
    )
    blocked_reasons = [check["blocked_reason"] for check in draft_checks if check["status"] == "failed"]
    import_allowed = not blocked_reasons
    import_command = f"albu-mcp beta response-import --input {request.input_path} --path {request.beta_records_path}"
    return {
        "guard_status": "ready_to_import" if import_allowed else "blocked_until_post_fix_draft_ready",
        "outcome_status": outcome["outcome_status"],
        "writes_records": False,
        "import_allowed": import_allowed,
        "blocked_reasons": blocked_reasons,
        "selected_fix": selected_fix,
        "expected_workflow_id": expected_workflow_id,
        "expected_triage_bucket": expected_triage_bucket,
        "draft_path": str(request.input_path),
        "draft": draft.model_dump(mode="json"),
        "draft_checks": draft_checks,
        "import_command": import_command if import_allowed else None,
        "source_outcome": outcome,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": _next_commands(
            host=request.host,
            import_allowed=import_allowed,
            import_command=import_command,
        ),
    }


def build_product_fix_outcome_import_guard_artifacts(
    request: ProductFixOutcomeImportGuardRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build artifact-only import guard files for one post-fix beta response draft."""
    report = build_product_fix_outcome_import_guard(request)
    artifacts = [
        _guard_index_artifact(report=report, output_format=output_format),
        _draft_checks_artifact(report=report, output_format=output_format),
        _guarded_import_command_artifact(report=report, output_format=output_format),
    ]
    return {
        "pack_status": report["guard_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_product_fix_outcome_import_guard_json(report: dict[str, Any]) -> str:
    """Render a product fix outcome import guard report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_outcome_import_guard_markdown(report: dict[str, Any]) -> str:
    """Render a product fix outcome import guard report as Markdown."""
    return (
        "# Product Fix Outcome Import Guard\n\n"
        f"Guard status: `{report['guard_status']}`\n\n"
        f"Outcome status: `{report['outcome_status']}`\n\n"
        f"Import allowed: `{str(report['import_allowed']).lower()}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Draft path: `{report['draft_path']}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(report['blocked_reasons'], code=True)}\n\n"
        "## Draft Checks\n\n"
        f"{_render_draft_checks(report['draft_checks'])}\n"
    )


def _blocked_until_validation_report(
    *,
    request: ProductFixOutcomeImportGuardRequest,
    outcome: dict[str, Any],
) -> dict[str, Any]:
    return {
        "guard_status": "blocked_until_product_fix_validation",
        "outcome_status": outcome["outcome_status"],
        "writes_records": False,
        "import_allowed": False,
        "blocked_reasons": outcome["blocked_reasons"],
        "selected_fix": outcome["selected_fix"],
        "expected_workflow_id": None,
        "expected_triage_bucket": None,
        "draft_path": str(request.input_path),
        "draft": None,
        "draft_checks": [],
        "import_command": None,
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


def _blocked_closed_outcome_report(
    *,
    request: ProductFixOutcomeImportGuardRequest,
    outcome: dict[str, Any],
) -> dict[str, Any]:
    return {
        "guard_status": f"blocked_fix_outcome_{outcome['outcome_status']}",
        "outcome_status": outcome["outcome_status"],
        "writes_records": False,
        "import_allowed": False,
        "blocked_reasons": [f"fix_outcome_closed:{outcome['outcome_status']}"],
        "selected_fix": outcome["selected_fix"],
        "expected_workflow_id": None,
        "expected_triage_bucket": None,
        "draft_path": str(request.input_path),
        "draft": None,
        "draft_checks": [],
        "import_command": None,
        "source_outcome": outcome,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": [f"albu-mcp activation product-fix-outcome --host {request.host} --format json"],
    }


def _build_draft_checks(
    *,
    draft: BetaResponseDraft,
    expected_workflow_id: str,
    expected_triage_bucket: str,
) -> list[dict[str, Any]]:
    return [
        _draft_check(
            check_id="workflow_matches_selected_fix",
            passed=draft.workflow_id == expected_workflow_id,
            blocked_reason=f"post_fix_workflow_mismatch:{expected_workflow_id}",
            expected=expected_workflow_id,
            observed=draft.workflow_id,
        ),
        _draft_check(
            check_id="triage_bucket_matches_selected_fix",
            passed=draft.triage_bucket == expected_triage_bucket,
            blocked_reason=f"post_fix_triage_bucket_mismatch:{expected_triage_bucket}",
            expected=expected_triage_bucket,
            observed=draft.triage_bucket,
        ),
        _draft_check(
            check_id="summary_replaced",
            passed=not _looks_like_placeholder_summary(draft.summary),
            blocked_reason="post_fix_summary_placeholder",
            expected="redacted reviewer-observed post-fix outcome summary",
            observed=draft.summary,
        ),
        _draft_check(
            check_id="artifact_refs_present",
            passed=bool(draft.artifact_refs),
            blocked_reason="post_fix_artifacts_missing",
            expected="at least one redacted artifact ref",
            observed=draft.artifact_refs,
        ),
        _draft_check(
            check_id="privacy_redacted",
            passed=draft.private_data_included is False,
            blocked_reason="post_fix_private_data_included",
            expected=False,
            observed=draft.private_data_included,
        ),
    ]


def _draft_check(
    *,
    check_id: str,
    passed: bool,
    blocked_reason: str,
    expected: Any,
    observed: Any,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "passed" if passed else "failed",
        "blocked_reason": None if passed else blocked_reason,
        "expected": expected,
        "observed": observed,
    }


def _looks_like_placeholder_summary(summary: str) -> bool:
    normalized = summary.lower()
    return "replace with" in normalized or "placeholder" in normalized


def _next_commands(*, host: HostName, import_allowed: bool, import_command: str) -> list[str]:
    if import_allowed:
        return [
            import_command,
            f"albu-mcp activation product-fix-outcome --host {host} --format json",
        ]
    return [
        f"albu-mcp activation product-fix-outcome-capture --host {host} --format json",
        f"albu-mcp activation product-fix-outcome-import-guard --host {host} --input <post-fix-draft> --format json",
    ]


def _guard_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "product_fix_outcome_import_guard_index",
        "guard_status": report["guard_status"],
        "outcome_status": report["outcome_status"],
        "import_allowed": report["import_allowed"],
        "writes_records": False,
        "blocked_reasons": report["blocked_reasons"],
        "draft_path": report["draft_path"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"product-fix-outcome-import-guard-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_guard_index_markdown(payload),
            output_format=output_format,
        ),
    }


def _draft_checks_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "draft_checks",
        "guard_status": report["guard_status"],
        "writes_records": False,
        "draft_checks": report["draft_checks"],
    }
    return {
        "filename": f"draft-checks.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_draft_checks_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _guarded_import_command_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "guarded_import_command",
        "guard_status": report["guard_status"],
        "writes_records": False,
        "import_allowed": report["import_allowed"],
        "import_command": report["import_command"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"guarded-import-command.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_guarded_import_command_markdown(payload),
            output_format=output_format,
        ),
    }


def _render_guard_index_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Product Fix Outcome Import Guard Index\n\n"
        f"Guard status: `{payload['guard_status']}`\n\n"
        f"Outcome status: `{payload['outcome_status']}`\n\n"
        f"Import allowed: `{str(payload['import_allowed']).lower()}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Draft path: `{payload['draft_path']}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(payload['blocked_reasons'], code=True)}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_draft_checks_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Draft Checks\n\n"
        f"Guard status: `{payload['guard_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"{_render_draft_checks(payload['draft_checks'])}\n"
    )


def _render_guarded_import_command_markdown(payload: dict[str, Any]) -> str:
    command = payload["import_command"] or "none"
    return (
        "# Guarded Import Command\n\n"
        f"Guard status: `{payload['guard_status']}`\n\n"
        f"Import allowed: `{str(payload['import_allowed']).lower()}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        "## Command\n\n"
        f"- `{command}`\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_draft_checks(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return "- none"
    return "\n\n".join(
        (
            f"### {check['id']}\n\n"
            f"Status: `{check['status']}`\n\n"
            f"Expected: `{_stringify(check['expected'])}`\n\n"
            f"Observed: `{_stringify(check['observed'])}`"
        )
        for check in checks
    )


def _render_list(items: list[str], *, code: bool = False) -> str:
    if not items:
        return "- none"
    if code:
        return "\n".join(f"- `{item}`" for item in items)
    return "\n".join(f"- {item}" for item in items)


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True)


def _artifact_extension(output_format: str) -> str:
    if output_format == "markdown":
        return "md"
    if output_format == "json":
        return "json"
    msg = f"unsupported product fix outcome import guard artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported product fix outcome import guard artifact format: {output_format}"
    raise ValueError(msg)
