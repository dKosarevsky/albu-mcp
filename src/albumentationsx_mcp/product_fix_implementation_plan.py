"""No-write TDD implementation plan for the selected product fix."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.first_product_fix_selector import (
    FirstProductFixSelectorRequest,
    build_first_product_fix_selector,
)


@dataclass(frozen=True)
class ProductFixImplementationPlanRequest:
    """Inputs for building one product fix implementation plan."""

    host: HostName
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_product_fix_implementation_plan(request: ProductFixImplementationPlanRequest) -> dict[str, Any]:
    """Build a no-write implementation plan from the first product fix selector."""
    selector = build_first_product_fix_selector(
        FirstProductFixSelectorRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    implementation_allowed = selector["implementation_allowed"]
    implementation_plan = _build_implementation_plan(selector) if implementation_allowed else None
    return {
        "plan_status": "ready_for_tdd" if implementation_allowed else "blocked_until_first_product_fix",
        "selector_status": selector["selector_status"],
        "writes_records": False,
        "implementation_allowed": implementation_allowed,
        "blocked_reasons": selector["blocked_reasons"],
        "selected_fix": selector["selected_fix"],
        "implementation_plan": implementation_plan,
        "source_selector": selector,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": _next_commands(
            host=request.host,
            implementation_allowed=implementation_allowed,
            implementation_plan=implementation_plan,
        ),
    }


def build_product_fix_implementation_plan_artifacts(
    request: ProductFixImplementationPlanRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build artifact-only handoff files for a product fix implementation plan."""
    report = build_product_fix_implementation_plan(request)
    artifacts = [
        _implementation_plan_index_artifact(report=report, output_format=output_format),
        _tdd_plan_artifact(report=report, output_format=output_format),
        _verification_plan_artifact(report=report, output_format=output_format),
    ]
    return {
        "pack_status": report["plan_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_product_fix_implementation_plan_json(report: dict[str, Any]) -> str:
    """Render a product fix implementation plan as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_implementation_plan_markdown(report: dict[str, Any]) -> str:
    """Render a product fix implementation plan as Markdown."""
    blocked_reasons = "\n".join(f"- `{reason}`" for reason in report["blocked_reasons"]) or "- none"
    selected_fix = report["selected_fix"]
    implementation_plan = report["implementation_plan"]
    selected_summary = (
        "- none"
        if selected_fix is None
        else (
            f"- Product area: `{selected_fix['product_area']}`\n"
            f"- Triage bucket: `{selected_fix['triage_bucket']}`\n"
            f"- Success signal: {selected_fix['success_signal']}"
        )
    )
    phase_summary = "- none"
    if implementation_plan is not None:
        phase_summary = "\n".join(f"- `{phase['id']}`: {phase['objective']}" for phase in implementation_plan["phases"])
    return (
        "# Product Fix Implementation Plan\n\n"
        f"Plan status: `{report['plan_status']}`\n\n"
        f"Selector status: `{report['selector_status']}`\n\n"
        f"Implementation allowed: `{str(report['implementation_allowed']).lower()}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        "## Selected Fix\n\n"
        f"{selected_summary}\n\n"
        "## Blocked Reasons\n\n"
        f"{blocked_reasons}\n\n"
        "## Phases\n\n"
        f"{phase_summary}\n"
    )


def _implementation_plan_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "product_fix_implementation_plan_index",
        "plan_status": report["plan_status"],
        "selector_status": report["selector_status"],
        "implementation_allowed": report["implementation_allowed"],
        "writes_records": False,
        "selected_fix": report["selected_fix"],
        "blocked_reasons": report["blocked_reasons"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"product-fix-implementation-plan-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_index_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _tdd_plan_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    implementation_plan = report["implementation_plan"] or {}
    phases = [
        phase
        for phase in implementation_plan.get("phases", [])
        if phase["id"] in {"red_tests", "minimal_implementation"}
    ]
    payload = {
        "artifact": "tdd_plan",
        "plan_status": report["plan_status"],
        "writes_records": False,
        "selected_fix": report["selected_fix"],
        "phases": phases,
    }
    return {
        "filename": f"tdd-plan.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_phase_artifact_markdown(title="TDD Plan", payload=payload),
            output_format=output_format,
        ),
    }


def _verification_plan_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    implementation_plan = report["implementation_plan"] or {}
    phases = [phase for phase in implementation_plan.get("phases", []) if phase["id"] in {"verification", "merge"}]
    payload = {
        "artifact": "verification_plan",
        "plan_status": report["plan_status"],
        "writes_records": False,
        "selected_fix": report["selected_fix"],
        "phases": phases,
    }
    return {
        "filename": f"verification-plan.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_phase_artifact_markdown(title="Verification Plan", payload=payload),
            output_format=output_format,
        ),
    }


def _render_index_artifact_markdown(payload: dict[str, Any]) -> str:
    selected_fix = payload["selected_fix"]
    selected_summary = (
        "- none"
        if selected_fix is None
        else (
            f"- Product area: `{selected_fix['product_area']}`\n"
            f"- Triage bucket: `{selected_fix['triage_bucket']}`\n"
            f"- Success signal: {selected_fix['success_signal']}"
        )
    )
    blocked_reasons = "\n".join(f"- `{reason}`" for reason in payload["blocked_reasons"]) or "- none"
    next_commands = "\n".join(f"- `{command}`" for command in payload["next_commands"]) or "- none"
    return (
        "# Product Fix Implementation Plan Index\n\n"
        f"Plan status: `{payload['plan_status']}`\n\n"
        f"Selector status: `{payload['selector_status']}`\n\n"
        f"Implementation allowed: `{str(payload['implementation_allowed']).lower()}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        "## Selected Fix\n\n"
        f"{selected_summary}\n\n"
        "## Blocked Reasons\n\n"
        f"{blocked_reasons}\n\n"
        "## Next Commands\n\n"
        f"{next_commands}\n"
    )


def _render_phase_artifact_markdown(*, title: str, payload: dict[str, Any]) -> str:
    phase_items = "\n\n".join(_render_phase_markdown(phase) for phase in payload["phases"]) or "- none"
    return (
        f"# {title}\n\n"
        f"Plan status: `{payload['plan_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        "## Phases\n\n"
        f"{phase_items}\n"
    )


def _render_phase_markdown(phase: dict[str, Any]) -> str:
    commands = "\n".join(f"- `{command}`" for command in phase["commands"]) or "- none"
    success_criteria = "\n".join(f"- {criterion}" for criterion in phase["success_criteria"]) or "- none"
    return (
        f"### {phase['title']}\n\n"
        f"Status: `{phase['status']}`\n\n"
        f"Objective: {phase['objective']}\n\n"
        "Commands:\n\n"
        f"{commands}\n\n"
        "Success criteria:\n\n"
        f"{success_criteria}"
    )


def _artifact_extension(output_format: str) -> str:
    if output_format == "markdown":
        return "md"
    if output_format == "json":
        return "json"
    msg = f"unsupported product fix implementation plan artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported product fix implementation plan artifact format: {output_format}"
    raise ValueError(msg)


def _build_implementation_plan(selector: dict[str, Any]) -> dict[str, Any]:
    selected_fix = selector["selected_fix"]
    packet = selector["implementation_packet"]
    suggested_tests = [path for path in packet["suggested_files"] if path.startswith("tests/")]
    focused_test_command = f"uv run pytest {' '.join(suggested_tests)} -q"
    phases = [
        {
            "id": "red_tests",
            "title": "RED tests",
            "status": "write_first",
            "objective": packet["test_strategy"][0],
            "commands": [focused_test_command],
            "success_criteria": [
                "At least one new test fails for the selected product behavior before implementation.",
                "The failure is caused by missing behavior, not a fixture or import error.",
            ],
        },
        {
            "id": "minimal_implementation",
            "title": "Minimal implementation",
            "status": "after_red",
            "objective": f"Implement only the selected {selected_fix['product_area']} behavior.",
            "commands": [focused_test_command],
            "success_criteria": [
                "The RED tests pass without broad refactors.",
                "Host and beta evidence records remain unchanged.",
            ],
        },
        {
            "id": "verification",
            "title": "Verification",
            "status": "before_commit",
            "objective": "Run focused quality gates and the full project test suite.",
            "commands": [
                "uv run ruff check .",
                "uv run ruff format --check .",
                "uv run ty check",
                "uv run python scripts/check_release_readiness.py",
                "uv run pytest -q",
            ],
            "success_criteria": [
                "All checks pass locally.",
                "Release readiness remains green.",
            ],
        },
        {
            "id": "merge",
            "title": "PR and merge",
            "status": "after_verification",
            "objective": "Push one scoped branch, wait for CI, merge, and rerun focused post-merge checks.",
            "commands": [
                "git diff --check",
                "git push -u origin <branch>",
                "gh pr create",
                "gh pr checks <number> --watch",
            ],
            "success_criteria": [
                "CI passes on every configured Python version.",
                "Main fast-forwards cleanly after merge.",
            ],
        },
    ]
    return {
        "plan_id": f"{selected_fix['product_area']}_first_product_fix_tdd",
        "product_area": selected_fix["product_area"],
        "triage_bucket": selected_fix["triage_bucket"],
        "scope": packet["scope"],
        "success_signal": packet["success_signal"],
        "suggested_files": packet["suggested_files"],
        "phase_count": len(phases),
        "phases": phases,
    }


def _next_commands(
    *,
    host: HostName,
    implementation_allowed: bool,
    implementation_plan: dict[str, Any] | None,
) -> list[str]:
    if implementation_allowed:
        if implementation_plan is None:
            return ["Rerun product-fix-implementation-plan after selector output is ready."]
        red_phase = implementation_plan["phases"][0]
        return [
            red_phase["objective"],
            red_phase["commands"][0],
        ]
    return [
        f"albu-mcp activation first-product-fix --host {host} --format json",
        "albu-mcp evidence import-wizard --beta-dir docs/beta-response-templates --format json",
    ]
