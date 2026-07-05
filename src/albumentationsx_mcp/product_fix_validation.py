"""No-write product fix validation against implemented behavior contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.policy_assistant import plan_augmentation_policy_candidates, plan_policy_iteration
from albumentationsx_mcp.product_fix_execution_guard import (
    ProductFixExecutionGuardRequest,
    build_product_fix_execution_guard,
)
from albumentationsx_mcp.review_agent import interpret_preview_feedback

_REVIEW_AGENT_FEEDBACK_NOTE = "Example 8 is maybe too noisy; I can't even recognize the objects."
_REVIEW_AGENT_EXPECTED_CANDIDATE_ORDER = [
    "minimal_change",
    "conservative",
    "review_safe",
    "balanced",
]
_REVIEW_AGENT_EXPECTED_ITERATION_ACTION = "Restore object readability before exploring more augmentation variety."


@dataclass(frozen=True)
class ProductFixValidationRequest:
    """Inputs for validating one selected product fix behavior contract."""

    host: HostName
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_product_fix_validation(request: ProductFixValidationRequest) -> dict[str, Any]:
    """Build a no-write validation report for the selected product fix."""
    guard = build_product_fix_execution_guard(
        ProductFixExecutionGuardRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    if not guard["execution_allowed"]:
        return _blocked_validation_report(request=request, guard=guard)

    selected_fix = guard["selected_fix"]
    if selected_fix["triage_bucket"] != "review_agent_v3_gap":
        return _unsupported_validation_report(request=request, guard=guard)

    contract, validation_results = _validate_review_agent_contract()
    fix_validated = all(result["status"] == "passed" for result in validation_results)
    failed_checks = [result["id"] for result in validation_results if result["status"] != "passed"]
    return {
        "validation_status": "validated" if fix_validated else "failed_behavior_contract",
        "guard_status": guard["guard_status"],
        "writes_records": False,
        "execution_allowed": True,
        "fix_validated": fix_validated,
        "blocked_reasons": failed_checks,
        "selected_fix": selected_fix,
        "behavior_contract": contract,
        "validation_results": validation_results,
        "source_guard": guard,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": _next_commands(host=request.host, fix_validated=fix_validated),
    }


def build_product_fix_validation_artifacts(
    request: ProductFixValidationRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build artifact-only validation files for a selected product fix."""
    report = build_product_fix_validation(request)
    artifacts = [
        _validation_index_artifact(report=report, output_format=output_format),
        _behavior_contract_artifact(report=report, output_format=output_format),
        _validation_results_artifact(report=report, output_format=output_format),
    ]
    return {
        "pack_status": report["validation_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_product_fix_validation_json(report: dict[str, Any]) -> str:
    """Render a product fix validation report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_validation_markdown(report: dict[str, Any]) -> str:
    """Render a product fix validation report as Markdown."""
    contract = report["behavior_contract"]
    contract_id = "none" if contract is None else contract["contract_id"]
    return (
        "# Product Fix Validation\n\n"
        f"Validation status: `{report['validation_status']}`\n\n"
        f"Guard status: `{report['guard_status']}`\n\n"
        f"Execution allowed: `{str(report['execution_allowed']).lower()}`\n\n"
        f"Fix validated: `{str(report['fix_validated']).lower()}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Behavior contract: `{contract_id}`\n\n"
        "## Validation Results\n\n"
        f"{_render_validation_results(report['validation_results'])}\n"
    )


def _blocked_validation_report(
    *,
    request: ProductFixValidationRequest,
    guard: dict[str, Any],
) -> dict[str, Any]:
    return {
        "validation_status": "blocked_until_execution_guard",
        "guard_status": guard["guard_status"],
        "writes_records": False,
        "execution_allowed": False,
        "fix_validated": False,
        "blocked_reasons": guard["blocked_reasons"],
        "selected_fix": guard["selected_fix"],
        "behavior_contract": None,
        "validation_results": [],
        "source_guard": guard,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": [
            f"albu-mcp activation product-fix-execution-guard --host {request.host} --format json",
            *guard["next_commands"],
        ],
    }


def _unsupported_validation_report(
    *,
    request: ProductFixValidationRequest,
    guard: dict[str, Any],
) -> dict[str, Any]:
    selected_fix = guard["selected_fix"]
    blocked_reason = f"validation_contract_missing:{selected_fix['triage_bucket']}"
    return {
        "validation_status": "unsupported_validation_contract",
        "guard_status": guard["guard_status"],
        "writes_records": False,
        "execution_allowed": True,
        "fix_validated": False,
        "blocked_reasons": [blocked_reason],
        "selected_fix": selected_fix,
        "behavior_contract": None,
        "validation_results": [],
        "source_guard": guard,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": [f"Add a product-fix validation contract for {selected_fix['triage_bucket']}."],
    }


def _validate_review_agent_contract() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    interpretation = interpret_preview_feedback(_REVIEW_AGENT_FEEDBACK_NOTE)
    candidate_set = plan_augmentation_policy_candidates(
        task="classification",
        objective="robustness",
        targets=["image"],
        feedback_tags=interpretation.feedback_tags,
        candidate_count=4,
    )
    iteration = plan_policy_iteration(
        task="classification",
        objective="robustness",
        targets=["image"],
        feedback_tags=interpretation.feedback_tags,
        rejected_candidate_ids=["aggressive"],
        accepted_candidate_id=None,
        iteration=2,
    )
    observed_candidate_order = [candidate.candidate_id for candidate in candidate_set.candidates]
    observed_intensities = [candidate.plan.intensity for candidate in candidate_set.candidates]
    observed_iteration_action = iteration.next_actions[0] if iteration.next_actions else ""
    contract = {
        "contract_id": "review_agent_v3_gap_readability_recovery",
        "feedback_note": _REVIEW_AGENT_FEEDBACK_NOTE,
        "expected_feedback_tags": ["too_noisy:high", "object_unrecognizable:high"],
        "observed_feedback_tags": interpretation.feedback_tags,
        "expected_candidate_order": _REVIEW_AGENT_EXPECTED_CANDIDATE_ORDER,
        "observed_candidate_order": observed_candidate_order,
        "observed_candidate_intensities": observed_intensities,
        "expected_iteration_next_action": _REVIEW_AGENT_EXPECTED_ITERATION_ACTION,
        "observed_iteration_next_action": observed_iteration_action,
    }
    results = [
        _validation_result(
            check_id="feedback_interpretation",
            passed=interpretation.feedback_tags == contract["expected_feedback_tags"],
            expected=contract["expected_feedback_tags"],
            observed=interpretation.feedback_tags,
        ),
        _validation_result(
            check_id="candidate_recovery_order",
            passed=observed_candidate_order == _REVIEW_AGENT_EXPECTED_CANDIDATE_ORDER,
            expected=_REVIEW_AGENT_EXPECTED_CANDIDATE_ORDER,
            observed=observed_candidate_order,
        ),
        _validation_result(
            check_id="aggressive_candidate_removed",
            passed="aggressive" not in observed_candidate_order and "high" not in observed_intensities,
            expected="no aggressive candidate and no high-intensity recovery candidate",
            observed={
                "candidate_order": observed_candidate_order,
                "candidate_intensities": observed_intensities,
            },
        ),
        _validation_result(
            check_id="iteration_recovery_action",
            passed=observed_iteration_action == _REVIEW_AGENT_EXPECTED_ITERATION_ACTION,
            expected=_REVIEW_AGENT_EXPECTED_ITERATION_ACTION,
            observed=observed_iteration_action,
        ),
    ]
    return contract, results


def _validation_result(*, check_id: str, passed: bool, expected: Any, observed: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "passed" if passed else "failed",
        "expected": expected,
        "observed": observed,
    }


def _next_commands(*, host: HostName, fix_validated: bool) -> list[str]:
    focused_tests = "uv run pytest tests/test_policy_assistant_candidates.py -q"
    if fix_validated:
        return [
            focused_tests,
            f"albu-mcp activation product-fix-validation --host {host} --format markdown",
        ]
    return [
        focused_tests,
        f"albu-mcp activation product-fix-execution-guard --host {host} --format json",
    ]


def _validation_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "product_fix_validation_index",
        "validation_status": report["validation_status"],
        "guard_status": report["guard_status"],
        "execution_allowed": report["execution_allowed"],
        "fix_validated": report["fix_validated"],
        "writes_records": False,
        "blocked_reasons": report["blocked_reasons"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"product-fix-validation-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_index_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _behavior_contract_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "behavior_contract",
        "validation_status": report["validation_status"],
        "writes_records": False,
        "behavior_contract": report["behavior_contract"],
    }
    return {
        "filename": f"behavior-contract.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_behavior_contract_markdown(payload),
            output_format=output_format,
        ),
    }


def _validation_results_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "validation_results",
        "validation_status": report["validation_status"],
        "writes_records": False,
        "validation_results": report["validation_results"],
    }
    return {
        "filename": f"validation-results.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_validation_results_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _render_index_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Product Fix Validation Index\n\n"
        f"Validation status: `{payload['validation_status']}`\n\n"
        f"Guard status: `{payload['guard_status']}`\n\n"
        f"Execution allowed: `{str(payload['execution_allowed']).lower()}`\n\n"
        f"Fix validated: `{str(payload['fix_validated']).lower()}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(payload['blocked_reasons'], code=True)}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_behavior_contract_markdown(payload: dict[str, Any]) -> str:
    contract = payload["behavior_contract"]
    if contract is None:
        return (
            "# Behavior Contract\n\n"
            f"Validation status: `{payload['validation_status']}`\n\n"
            f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
            "Behavior contract: `none`\n"
        )
    return (
        "# Behavior Contract\n\n"
        f"Validation status: `{payload['validation_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Contract id: `{contract['contract_id']}`\n\n"
        f"Feedback note: {contract['feedback_note']}\n\n"
        "## Expected candidate order\n\n"
        f"{_render_list(contract['expected_candidate_order'], code=True)}\n\n"
        "## Observed candidate order\n\n"
        f"{_render_list(contract['observed_candidate_order'], code=True)}\n\n"
        "## Iteration next action\n\n"
        f"- Expected: {contract['expected_iteration_next_action']}\n"
        f"- Observed: {contract['observed_iteration_next_action']}\n"
    )


def _render_validation_results_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Validation Results\n\n"
        f"Validation status: `{payload['validation_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"{_render_validation_results(payload['validation_results'])}\n"
    )


def _render_validation_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return "- none"
    return "\n\n".join(
        (
            f"### {result['id']}\n\n"
            f"Status: `{result['status']}`\n\n"
            f"Expected: `{_stringify(result['expected'])}`\n\n"
            f"Observed: `{_stringify(result['observed'])}`"
        )
        for result in results
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
    msg = f"unsupported product fix validation artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported product fix validation artifact format: {output_format}"
    raise ValueError(msg)
