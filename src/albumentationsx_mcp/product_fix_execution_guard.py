"""No-write execution guard for a selected product fix implementation plan."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.product_fix_implementation_plan import (
    ProductFixImplementationPlanRequest,
    build_product_fix_implementation_plan,
)


@dataclass(frozen=True)
class ProductFixExecutionGuardRequest:
    """Inputs for building one guarded product fix execution handoff."""

    host: HostName
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_product_fix_execution_guard(request: ProductFixExecutionGuardRequest) -> dict[str, Any]:
    """Build a no-write execution guard from the product fix TDD plan."""
    plan = build_product_fix_implementation_plan(
        ProductFixImplementationPlanRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    if not plan["implementation_allowed"]:
        return _blocked_guard_report(request=request, plan=plan)

    branch_scaffold = _build_branch_scaffold(plan)
    command_groups = _build_command_groups(plan["implementation_plan"])
    execution_checklist = _build_execution_checklist(branch_scaffold=branch_scaffold, command_groups=command_groups)
    return {
        "guard_status": "ready_for_branch_scaffold",
        "plan_status": plan["plan_status"],
        "writes_records": False,
        "execution_allowed": True,
        "blocked_reasons": [],
        "selected_fix": plan["selected_fix"],
        "branch_scaffold": branch_scaffold,
        "command_groups": command_groups,
        "execution_checklist": execution_checklist,
        "source_plan": plan,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": branch_scaffold["first_commands"],
    }


def build_product_fix_execution_guard_artifacts(
    request: ProductFixExecutionGuardRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build artifact-only handoff files for a guarded product fix execution."""
    report = build_product_fix_execution_guard(request)
    artifacts = [
        _execution_guard_index_artifact(report=report, output_format=output_format),
        _branch_scaffold_artifact(report=report, output_format=output_format),
        _execution_checklist_artifact(report=report, output_format=output_format),
    ]
    return {
        "pack_status": report["guard_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_product_fix_execution_guard_json(report: dict[str, Any]) -> str:
    """Render a product fix execution guard as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_execution_guard_markdown(report: dict[str, Any]) -> str:
    """Render a product fix execution guard as Markdown."""
    blocked_reasons = _render_list(report["blocked_reasons"], code=True)
    branch_scaffold = report["branch_scaffold"]
    branch_name = "none" if branch_scaffold is None else branch_scaffold["branch_name"]
    command_groups = report["command_groups"]
    checklist = report["execution_checklist"]
    return (
        "# Product Fix Execution Guard\n\n"
        f"Guard status: `{report['guard_status']}`\n\n"
        f"Plan status: `{report['plan_status']}`\n\n"
        f"Execution allowed: `{str(report['execution_allowed']).lower()}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Branch name: `{branch_name}`\n\n"
        "## Blocked Reasons\n\n"
        f"{blocked_reasons}\n\n"
        "## Command Groups\n\n"
        f"{_render_command_groups(command_groups)}\n\n"
        "## Execution Checklist\n\n"
        f"{_render_checklist(checklist)}\n"
    )


def _blocked_guard_report(
    *,
    request: ProductFixExecutionGuardRequest,
    plan: dict[str, Any],
) -> dict[str, Any]:
    return {
        "guard_status": "blocked_until_tdd_plan",
        "plan_status": plan["plan_status"],
        "writes_records": False,
        "execution_allowed": False,
        "blocked_reasons": plan["blocked_reasons"],
        "selected_fix": plan["selected_fix"],
        "branch_scaffold": None,
        "command_groups": {},
        "execution_checklist": [],
        "source_plan": plan,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": [
            f"albu-mcp activation product-fix-implementation-plan --host {request.host} --format json",
            *plan["next_commands"],
        ],
    }


def _build_branch_scaffold(plan: dict[str, Any]) -> dict[str, Any]:
    implementation_plan = plan["implementation_plan"]
    selected_fix = plan["selected_fix"]
    suggested_files = implementation_plan["suggested_files"]
    allowed_source_files = [path for path in suggested_files if path.startswith("src/")]
    allowed_test_files = [path for path in suggested_files if path.startswith("tests/")]
    branch_name = f"codex/product-fix-{_slug(selected_fix['product_area'])}-{_slug(selected_fix['triage_bucket'])}"
    red_command = _commands_for_phase(implementation_plan, "red_tests")[0]
    return {
        "branch_name": branch_name,
        "base_branch": "main",
        "product_area": selected_fix["product_area"],
        "triage_bucket": selected_fix["triage_bucket"],
        "allowed_source_files": allowed_source_files,
        "allowed_test_files": allowed_test_files,
        "first_commands": [
            f"git checkout -b {branch_name}",
            red_command,
        ],
        "constraints": [
            "Start from main or an up-to-date feature worktree.",
            "Write at least one RED test before implementation.",
            (
                "Keep edits inside allowed source and test files unless the RED test proves "
                "a narrower support file is needed."
            ),
            "Do not edit host or beta evidence records in the implementation branch.",
        ],
    }


def _build_command_groups(implementation_plan: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "red": _commands_for_phase(implementation_plan, "red_tests"),
        "green": _commands_for_phase(implementation_plan, "minimal_implementation"),
        "verification": _commands_for_phase(implementation_plan, "verification"),
        "merge": _commands_for_phase(implementation_plan, "merge"),
    }


def _build_execution_checklist(
    *,
    branch_scaffold: dict[str, Any],
    command_groups: dict[str, list[str]],
) -> list[dict[str, Any]]:
    branch_name = branch_scaffold["branch_name"]
    return [
        {
            "id": "create_branch",
            "status": "required_before_code",
            "objective": f"Create `{branch_name}` from an up-to-date `main` branch.",
            "commands": [branch_scaffold["first_commands"][0]],
        },
        {
            "id": "red_tests",
            "status": "required_before_code",
            "objective": "Run RED tests before implementation.",
            "commands": command_groups["red"],
        },
        {
            "id": "minimal_implementation",
            "status": "after_red",
            "objective": "Implement only the selected product behavior and rerun the focused tests.",
            "commands": command_groups["green"],
        },
        {
            "id": "verification",
            "status": "before_pr",
            "objective": "Run full local verification before opening a pull request.",
            "commands": command_groups["verification"],
        },
        {
            "id": "pull_request",
            "status": "after_local_green",
            "objective": "Open one scoped PR with the selected fix, evidence source, and verification summary.",
            "commands": ["git push -u origin <branch>", "gh pr create"],
        },
        {
            "id": "merge",
            "status": "after_ci_green",
            "objective": "Merge only after local verification and CI are both green.",
            "commands": command_groups["merge"],
        },
    ]


def _commands_for_phase(implementation_plan: dict[str, Any], phase_id: str) -> list[str]:
    for phase in implementation_plan["phases"]:
        if phase["id"] == phase_id:
            return list(phase["commands"])
    return []


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _execution_guard_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    branch_scaffold = report["branch_scaffold"]
    payload = {
        "artifact": "product_fix_execution_guard_index",
        "guard_status": report["guard_status"],
        "plan_status": report["plan_status"],
        "execution_allowed": report["execution_allowed"],
        "writes_records": False,
        "branch_name": None if branch_scaffold is None else branch_scaffold["branch_name"],
        "blocked_reasons": report["blocked_reasons"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"product-fix-execution-guard-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_index_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _branch_scaffold_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "branch_scaffold",
        "guard_status": report["guard_status"],
        "writes_records": False,
        "branch_scaffold": report["branch_scaffold"],
        "command_groups": report["command_groups"],
    }
    return {
        "filename": f"branch-scaffold.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_branch_scaffold_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _execution_checklist_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "execution_checklist",
        "guard_status": report["guard_status"],
        "writes_records": False,
        "execution_checklist": report["execution_checklist"],
    }
    return {
        "filename": f"execution-checklist.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_execution_checklist_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _render_index_artifact_markdown(payload: dict[str, Any]) -> str:
    branch_name = payload["branch_name"] or "none"
    return (
        "# Product Fix Execution Guard Index\n\n"
        f"Guard status: `{payload['guard_status']}`\n\n"
        f"Plan status: `{payload['plan_status']}`\n\n"
        f"Execution allowed: `{str(payload['execution_allowed']).lower()}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Branch name: `{branch_name}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(payload['blocked_reasons'], code=True)}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_branch_scaffold_artifact_markdown(payload: dict[str, Any]) -> str:
    branch_scaffold = payload["branch_scaffold"]
    if branch_scaffold is None:
        return (
            "# Branch Scaffold\n\n"
            f"Guard status: `{payload['guard_status']}`\n\n"
            f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
            "Branch scaffold: `none`\n"
        )
    return (
        "# Branch Scaffold\n\n"
        f"Guard status: `{payload['guard_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Branch name: `{branch_scaffold['branch_name']}`\n\n"
        f"Base branch: `{branch_scaffold['base_branch']}`\n\n"
        "## Allowed Source Files\n\n"
        f"{_render_list(branch_scaffold['allowed_source_files'], code=True)}\n\n"
        "## Allowed Test Files\n\n"
        f"{_render_list(branch_scaffold['allowed_test_files'], code=True)}\n\n"
        "## First Commands\n\n"
        f"{_render_list(branch_scaffold['first_commands'], code=True)}\n\n"
        "## Constraints\n\n"
        f"{_render_list(branch_scaffold['constraints'])}\n"
    )


def _render_execution_checklist_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Execution Checklist\n\n"
        f"Guard status: `{payload['guard_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"{_render_checklist(payload['execution_checklist'])}\n"
    )


def _render_command_groups(command_groups: dict[str, list[str]]) -> str:
    if not command_groups:
        return "- none"
    sections = []
    for group_name, commands in command_groups.items():
        sections.append(f"### {group_name}\n\n{_render_list(commands, code=True)}")
    return "\n\n".join(sections)


def _render_checklist(checklist: list[dict[str, Any]]) -> str:
    if not checklist:
        return "- none"
    return "\n\n".join(
        (
            f"### {item['id']}\n\n"
            f"Status: `{item['status']}`\n\n"
            f"Objective: {item['objective']}\n\n"
            "Commands:\n\n"
            f"{_render_list(item['commands'], code=True)}"
        )
        for item in checklist
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
    msg = f"unsupported product fix execution guard artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported product fix execution guard artifact format: {output_format}"
    raise ValueError(msg)
