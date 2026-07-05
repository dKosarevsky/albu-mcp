"""No-write first product fix selector over real adoption evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import build_beta_validation_report, validate_beta_validation_records
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.real_adoption_cycle import RealAdoptionCycleRequest, build_real_adoption_cycle

_DECISION_PRIORITY = {
    "ready_for_depth_plan": 0,
    "candidate_backlog_item": 1,
}
_PRODUCT_FIX_PACKETS: dict[str, dict[str, Any]] = {
    "host_setup_gap": {
        "product_area": "host_onboarding",
        "priority": "p1_after_p0",
        "candidate": "Host-specific setup probes and clearer blocked evidence capture.",
        "success_signal": "A beta user can recover from setup failure without maintainer intervention.",
        "suggested_files": [
            "src/albumentationsx_mcp/host_setup.py",
            "src/albumentationsx_mcp/evidence.py",
            "tests/test_host_setup_probe.py",
        ],
    },
    "review_agent_v3_gap": {
        "product_area": "preview_review_agent",
        "priority": "p1_after_p0",
        "candidate": "Feedback-to-adjustment planning that better handles noisy or unreadable previews.",
        "success_signal": "Repeated noisy-preview feedback maps to safer candidate adjustments.",
        "suggested_files": [
            "src/albumentationsx_mcp/policy_assistant.py",
            "src/albumentationsx_mcp/review_agent.py",
            "src/albumentationsx_mcp/first_preview.py",
            "tests/test_policy_assistant_runtime.py",
            "tests/test_review_agent.py",
        ],
    },
    "dataset_quality_gap": {
        "product_area": "dataset_quality",
        "priority": "p1_after_p0",
        "candidate": "Deeper dataset health findings for annotations, class balance, and duplicate handling.",
        "success_signal": "Dataset issues are caught before preview rendering in beta workflows.",
        "suggested_files": [
            "src/albumentationsx_mcp/dataset.py",
            "src/albumentationsx_mcp/first_preview.py",
            "tests/test_dataset_quality.py",
        ],
    },
    "docs_gap": {
        "product_area": "host_docs",
        "priority": "p2_after_beta",
        "candidate": "Short host-specific cards for Codex, Claude Code, Cursor, and Claude Desktop.",
        "success_signal": "Users can start the first preview without reading long-form docs.",
        "suggested_files": [
            "README.md",
            "docs/USAGE.md",
            "docs/INSTALL.md",
        ],
    },
    "workflow_fit_gap": {
        "product_area": "cv_workflow_templates",
        "priority": "p2_after_beta",
        "candidate": "More task-specific workflow templates for robustness, OCR, detection, and segmentation.",
        "success_signal": "Beta users select a workflow template without custom prompting.",
        "suggested_files": [
            "src/albumentationsx_mcp/workflows.py",
            "src/albumentationsx_mcp/server.py",
            "tests/test_workflows.py",
        ],
    },
}


@dataclass(frozen=True)
class FirstProductFixSelectorRequest:
    """Inputs for selecting the first product fix after external gates pass."""

    host: HostName
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_first_product_fix_selector(request: FirstProductFixSelectorRequest) -> dict[str, Any]:
    """Build a no-write selector report for the first product fix."""
    adoption_cycle = build_real_adoption_cycle(
        RealAdoptionCycleRequest(
            host=request.host,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    beta_report = build_beta_validation_report(validate_beta_validation_records(request.beta_records_path))
    gate = _first_product_fix_gate(adoption_cycle)
    blocked_reasons = gate["blocked_reasons"]
    implementation_allowed = gate["implementation_allowed"]
    selected_fix = _select_fix(beta_report["decisions"]) if implementation_allowed else None

    selector_status = "ready_for_implementation" if implementation_allowed else "blocked_until_external_evidence"
    if implementation_allowed and selected_fix is None:
        selector_status = "blocked_no_candidate"
        implementation_allowed = False
        blocked_reasons = ["beta_validation_candidates_missing"]
    implementation_packet = _implementation_packet(selected_fix) if selected_fix is not None else None

    return {
        "selector_status": selector_status,
        "writes_records": False,
        "implementation_allowed": implementation_allowed,
        "blocked_reasons": blocked_reasons,
        "selected_fix": selected_fix,
        "implementation_packet": implementation_packet,
        "source_decisions": beta_report["decisions"],
        "adoption_cycle_status": adoption_cycle["cycle_status"],
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": _next_commands(
            host=request.host,
            implementation_allowed=implementation_allowed,
            selected_fix=selected_fix,
        ),
    }


def build_first_product_fix_selector_artifacts(
    request: FirstProductFixSelectorRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build artifact-only handoff files for the first product fix selector."""
    report = build_first_product_fix_selector(request)
    artifacts = [
        _selector_index_artifact(report=report, output_format=output_format),
        _selected_fix_artifact(report=report, output_format=output_format),
        _implementation_checklist_artifact(report=report, output_format=output_format),
    ]
    return {
        "pack_status": report["selector_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_first_product_fix_selector_json(report: dict[str, Any]) -> str:
    """Render a first product fix selector report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_first_product_fix_selector_markdown(report: dict[str, Any]) -> str:
    """Render a first product fix selector report as Markdown."""
    blocked_reasons = "\n".join(f"- `{reason}`" for reason in report["blocked_reasons"]) or "- none"
    decisions = "\n".join(
        f"- `{decision['triage_bucket']}`: `{decision['decision']}` ({decision['signal_count']} signals)"
        for decision in report["source_decisions"]
    )
    selected_fix = report["selected_fix"] or {}
    selected_summary = (
        "- none"
        if not selected_fix
        else (
            f"- Product area: `{selected_fix['product_area']}`\n"
            f"- Candidate: {selected_fix['candidate']}\n"
            f"- Success signal: {selected_fix['success_signal']}"
        )
    )
    return (
        "# First Product Fix Selector\n\n"
        f"Selector status: `{report['selector_status']}`\n\n"
        f"Implementation allowed: `{str(report['implementation_allowed']).lower()}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        "## Selected Fix\n\n"
        f"{selected_summary}\n\n"
        "## Blocked Reasons\n\n"
        f"{blocked_reasons}\n\n"
        "## Source Decisions\n\n"
        f"{decisions or '- none'}\n"
    )


def _selector_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "first_product_fix_index",
        "selector_status": report["selector_status"],
        "implementation_allowed": report["implementation_allowed"],
        "writes_records": False,
        "host": report["host"],
        "release_tag": report["release_tag"],
        "host_records_path": report["host_records_path"],
        "beta_records_path": report["beta_records_path"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"first-product-fix-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_selector_index_markdown(payload),
            output_format=output_format,
        ),
    }


def _selected_fix_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "selected_fix",
        "selector_status": report["selector_status"],
        "implementation_allowed": report["implementation_allowed"],
        "writes_records": False,
        "blocked_reasons": report["blocked_reasons"],
        "selected_fix": report["selected_fix"],
    }
    return {
        "filename": f"selected-fix.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_selected_fix_markdown(payload),
            output_format=output_format,
        ),
    }


def _implementation_checklist_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "implementation_checklist",
        "checklist_status": "ready" if report["implementation_allowed"] else "blocked",
        "writes_records": False,
        "implementation_packet": report["implementation_packet"],
        "items": _implementation_checklist_items(report),
    }
    return {
        "filename": f"implementation-checklist.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_implementation_checklist_markdown(payload),
            output_format=output_format,
        ),
    }


def _render_selector_index_markdown(payload: dict[str, Any]) -> str:
    commands = "\n".join(f"- `{command}`" for command in payload["next_commands"]) or "- none"
    return (
        "# First Product Fix Index\n\n"
        f"Selector status: `{payload['selector_status']}`\n\n"
        f"Implementation allowed: `{str(payload['implementation_allowed']).lower()}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Host: `{payload['host']}`\n\n"
        f"Release tag: `{payload['release_tag']}`\n\n"
        "## Next Commands\n\n"
        f"{commands}\n"
    )


def _render_selected_fix_markdown(payload: dict[str, Any]) -> str:
    selected_fix = payload["selected_fix"]
    if selected_fix is None:
        blocked = "\n".join(f"- `{reason}`" for reason in payload["blocked_reasons"]) or "- none"
        return (
            "# Selected Fix\n\n"
            f"Selector status: `{payload['selector_status']}`\n\n"
            "Selected fix: `none`\n\n"
            "## Blocked Reasons\n\n"
            f"{blocked}\n"
        )
    return (
        "# Selected Fix\n\n"
        f"Selector status: `{payload['selector_status']}`\n\n"
        f"Product area: `{selected_fix['product_area']}`\n\n"
        f"Triage bucket: `{selected_fix['triage_bucket']}`\n\n"
        f"Priority: `{selected_fix['priority']}`\n\n"
        f"Candidate: {selected_fix['candidate']}\n\n"
        f"Success signal: {selected_fix['success_signal']}\n"
    )


def _render_implementation_checklist_markdown(payload: dict[str, Any]) -> str:
    items = "\n".join(f"- {item}" for item in payload["items"])
    packet = payload["implementation_packet"]
    packet_summary = (
        "- none"
        if packet is None
        else (
            f"- Product area: `{packet['product_area']}`\n"
            f"- Scope: {packet['scope']}\n"
            f"- Success signal: {packet['success_signal']}"
        )
    )
    return (
        "# Implementation Checklist\n\n"
        f"Checklist status: `{payload['checklist_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        "## Checklist\n\n"
        f"{items}\n\n"
        "## Implementation Packet\n\n"
        f"{packet_summary}\n"
    )


def _implementation_checklist_items(report: dict[str, Any]) -> list[str]:
    if not report["implementation_allowed"]:
        return [
            "Do not implement runtime product changes while selector status is blocked.",
            "Collect reviewer-observed host evidence and privacy-safe beta validation records first.",
            "Rerun albu-mcp activation first-product-fix --host Codex --format json after imports.",
        ]
    packet = report["implementation_packet"]
    return [
        *packet["test_strategy"],
        "Keep the first product fix scoped to the selected product area.",
        "Do not edit host or beta evidence records while implementing product behavior.",
    ]


def _artifact_extension(output_format: str) -> str:
    if output_format == "markdown":
        return "md"
    if output_format == "json":
        return "json"
    msg = f"unsupported first product fix artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported first product fix artifact format: {output_format}"
    raise ValueError(msg)


def _first_product_fix_gate(adoption_cycle: dict[str, Any]) -> dict[str, Any]:
    return next(lane for lane in adoption_cycle["lanes"] if lane["id"] == "first_product_fix_gate")


def _select_fix(decisions: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not decisions:
        return None
    ordered = sorted(
        enumerate(decisions),
        key=lambda indexed: (_DECISION_PRIORITY.get(indexed[1]["decision"], 99), indexed[0]),
    )
    decision = ordered[0][1]
    packet = _PRODUCT_FIX_PACKETS[decision["triage_bucket"]]
    return {
        "triage_bucket": decision["triage_bucket"],
        "decision": decision["decision"],
        "signal_count": decision["signal_count"],
        "product_area": packet["product_area"],
        "priority": packet["priority"],
        "candidate": packet["candidate"],
        "success_signal": packet["success_signal"],
    }


def _implementation_packet(selected_fix: dict[str, Any]) -> dict[str, Any]:
    packet = _PRODUCT_FIX_PACKETS[selected_fix["triage_bucket"]]
    return {
        "packet_status": "ready",
        "product_area": selected_fix["product_area"],
        "triage_bucket": selected_fix["triage_bucket"],
        "priority": selected_fix["priority"],
        "scope": selected_fix["candidate"],
        "success_signal": selected_fix["success_signal"],
        "suggested_files": packet["suggested_files"],
        "test_strategy": [
            f"Write failing tests for {selected_fix['product_area']} before implementation.",
            "Keep evidence and beta records unchanged unless importing real external data.",
            "Run focused CLI and release readiness checks before merge.",
        ],
    }


def _next_commands(
    *,
    host: HostName,
    implementation_allowed: bool,
    selected_fix: dict[str, Any] | None,
) -> list[str]:
    if implementation_allowed:
        product_area = selected_fix["product_area"] if selected_fix is not None else "selected product area"
        return [
            f"Write failing tests for {product_area} before implementation.",
            "Keep evidence and beta records unchanged unless importing real external data.",
        ]
    return [
        f"albu-mcp activation real-adoption-cycle --host {host} --format json",
        "albu-mcp evidence import-wizard --beta-dir docs/beta-response-templates --format json",
    ]
