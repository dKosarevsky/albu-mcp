"""Combined proof sprint orchestration for external evidence gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from albumentationsx_mcp.activation import build_activation_command_center
from albumentationsx_mcp.beta_validation import build_beta_validation_report, validate_beta_validation_records
from albumentationsx_mcp.host_setup import build_host_setup_probe

OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL = "https://albumentations.ai/docs/integrations/mcp/"


def build_combined_proof_sprint(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
) -> dict[str, Any]:
    """Build one report-only sprint over the remaining external proof gates."""
    command_center = build_activation_command_center(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    beta_report = build_beta_validation_report(validate_beta_validation_records(beta_records_path))
    host_probe = build_host_setup_probe()
    p0_blocked = "p0_host_evidence_missing_or_blocked" in command_center["rc_candidate"]["blocked_reasons"]
    beta_blocked = not beta_report["product_depth_allowed"]
    host_depth_allowed = not p0_blocked and not beta_blocked
    points = [
        _real_host_evidence_point(blocked=p0_blocked),
        _beta_validation_point(blocked=beta_blocked, beta_report=beta_report),
        _host_onboarding_depth_point(implementation_allowed=host_depth_allowed, host_probe=host_probe),
    ]
    blocked = any(point["status"].startswith("blocked") for point in points)
    return {
        "sprint_status": "blocked" if blocked else "ready",
        "writes_records": False,
        "release_tag": release_tag,
        "host_records_path": str(host_records_path),
        "beta_records_path": str(beta_records_path),
        "point_count": len(points),
        "points": points,
        "next_action": "collect_real_host_and_beta_evidence" if blocked else "run_rc_go_check",
        "non_fabrication_policy": (
            "Generated proof sprint packets do not count as P0 host evidence or beta validation records. "
            "Only reviewer-observed real MCP host UI sessions and redacted external beta attempts may close gates."
        ),
        "source_docs": [
            "docs/GOVERNED_100_ITERATION_REPORT.md",
            "docs/HOST_ONBOARDING_DEPTH_PLAN.md",
            "docs/BETA_VALIDATION_SPRINT.md",
            "docs/P0_EVIDENCE_IMPORT_GUIDE.md",
            OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL,
        ],
    }


def build_combined_proof_sprint_artifacts(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build a no-write artifact folder for the combined proof sprint."""
    report = build_combined_proof_sprint(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    artifacts = [
        _index_artifact(report=report, output_format=output_format),
        *[_point_artifact(point=point, output_format=output_format) for point in report["points"]],
    ]
    return {
        "pack_status": report["sprint_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "next_actions": [
            "Run the real host evidence sprint with reviewer-observed MCP host UI sessions.",
            "Send beta validation templates from the official Albumentations docs link.",
            "Keep host onboarding depth implementation blocked until real P0 and beta gates open.",
        ],
    }


def render_combined_proof_sprint_markdown(report: dict[str, Any]) -> str:
    """Render the combined proof sprint index as Markdown."""
    return _render_index_markdown(report)


def build_proof_execution_workspace(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
) -> dict[str, Any]:
    """Build one no-write workspace for executing the external proof sprint."""
    proof_sprint = build_combined_proof_sprint(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    real_host_point = _point_by_id(proof_sprint, "real_host_evidence_sprint")
    beta_point = _point_by_id(proof_sprint, "beta_validation_sprint")
    steps = [
        _execution_workspace_step(),
        _execution_point_step(
            step_id="real_host_execution",
            source_point=real_host_point,
            next_commands=[
                "albu-mcp activation proof-sprint",
                "albu-mcp evidence session-folder",
                "albu-mcp evidence import-manifest",
            ],
        ),
        _execution_point_step(
            step_id="beta_execution",
            source_point=beta_point,
            next_commands=[
                "albu-mcp beta loop-pack",
                "albu-mcp beta response-import-dir",
                "albu-mcp beta report",
            ],
        ),
    ]
    blocked = any(step["status"].startswith("blocked") for step in steps)
    return {
        "workspace_status": "blocked" if blocked else "ready",
        "writes_records": False,
        "release_tag": release_tag,
        "host_records_path": str(host_records_path),
        "beta_records_path": str(beta_records_path),
        "step_count": len(steps),
        "steps": steps,
        "next_action": "run_workspace_artifacts" if blocked else "run_rc_go_check",
        "non_fabrication_policy": (
            "Generated execution workspace files do not count as evidence. Only reviewer-observed real MCP host "
            "sessions and privacy-safe external beta attempts may close the remaining gates."
        ),
        "source_docs": [
            "docs/GOVERNED_100_ITERATION_REPORT.md",
            "docs/USAGE.md",
            "docs/P0_EVIDENCE_IMPORT_GUIDE.md",
            "docs/BETA_VALIDATION_SPRINT.md",
            OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL,
        ],
    }


def build_proof_execution_workspace_artifacts(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build a no-write proof execution workspace artifact folder."""
    workspace = build_proof_execution_workspace(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    proof_sprint = build_combined_proof_sprint(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    artifacts = [
        _workspace_index_artifact(workspace=workspace, output_format=output_format),
        _workspace_step_artifact(
            filename_stem="real-host-execution-handoff",
            step=_workspace_step_by_id(workspace, "real_host_execution"),
            output_format=output_format,
        ),
        _workspace_step_artifact(
            filename_stem="beta-execution-handoff",
            step=_workspace_step_by_id(workspace, "beta_execution"),
            output_format=output_format,
        ),
        _host_onboarding_gate_artifact(
            point=_point_by_id(proof_sprint, "host_onboarding_depth"),
            output_format=output_format,
        ),
    ]
    return {
        "pack_status": workspace["workspace_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "next_actions": [
            "Run the real-host execution handoff before importing any evidence.",
            "Run the beta execution handoff with redacted external participant responses.",
            "Keep host onboarding depth blocked until external gates open.",
        ],
    }


def render_proof_execution_workspace_markdown(workspace: dict[str, Any]) -> str:
    """Render the proof execution workspace index as Markdown."""
    return _render_workspace_index_markdown(workspace)


def _real_host_evidence_point(*, blocked: bool) -> dict[str, Any]:
    return {
        "id": "real_host_evidence_sprint",
        "title": "Real host evidence sprint",
        "status": "blocked_until_real_host_evidence" if blocked else "ready",
        "implementation_allowed": False,
        "goal": "Close P0 host evidence with reviewer-observed MCP host UI sessions.",
        "success_signal": "Codex and Claude Code have passed manual_host_ui and first_10_minutes_replay records.",
        "next_commands": [
            "albu-mcp evidence session-folder",
            "albu-mcp evidence import-manifest",
            "albu-mcp evidence close-host",
        ],
        "source_links": [
            "docs/P0_EVIDENCE_IMPORT_GUIDE.md",
            "docs/HOST_EVIDENCE_CAPTURE_KIT.md",
            OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL,
        ],
    }


def _beta_validation_point(*, blocked: bool, beta_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "beta_validation_sprint",
        "title": "Beta validation sprint",
        "status": "blocked_until_beta_validation" if blocked else "ready",
        "implementation_allowed": False,
        "goal": "Collect privacy-safe external attempts from all required beta workflows.",
        "success_signal": "Every beta workflow has at least one redacted non-blocked validation record.",
        "summary": beta_report["summary"],
        "next_commands": [
            "albu-mcp beta loop-pack",
            "albu-mcp beta response-import-dir",
            "albu-mcp beta report",
        ],
        "source_links": [
            "docs/BETA_VALIDATION_SPRINT.md",
            "docs/BETA_FEEDBACK_INTAKE.md",
            OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL,
        ],
    }


def _host_onboarding_depth_point(*, implementation_allowed: bool, host_probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "host_onboarding_depth",
        "artifact_slug": "host-onboarding-depth-sprint",
        "title": "Host onboarding depth",
        "status": "ready_for_depth_plan" if implementation_allowed else "blocked_until_p0_and_beta_gates",
        "implementation_allowed": implementation_allowed,
        "goal": "Improve setup recovery only after real host and beta evidence identify repeated setup gaps.",
        "success_signal": "A beta user can recover from setup failure without maintainer intervention.",
        "probe_summary": host_probe["summary"],
        "next_commands": [
            "albu-mcp host setup-probe",
            "albu-mcp evidence collect",
            "albu-mcp activation proof-sprint",
        ],
        "source_links": [
            "docs/HOST_ONBOARDING_DEPTH_PLAN.md",
            "docs/HOST_FAILURE_COOKBOOK.md",
            "docs/P0_HOST_UNBLOCK_PACK.md",
        ],
    }


def _point_by_id(report: dict[str, Any], point_id: str) -> dict[str, Any]:
    for point in report["points"]:
        if point["id"] == point_id:
            return point
    msg = f"missing proof sprint point: {point_id}"
    raise ValueError(msg)


def _execution_workspace_step() -> dict[str, Any]:
    return {
        "id": "execution_workspace",
        "title": "Proof execution workspace",
        "status": "ready_to_write_artifacts",
        "implementation_allowed": False,
        "goal": "Write one operator folder for real host evidence, beta validation, and depth gate review.",
        "next_commands": [
            "albu-mcp activation execution-workspace --output-dir docs/proof-execution --format markdown",
        ],
    }


def _execution_point_step(
    *,
    step_id: str,
    source_point: dict[str, Any],
    next_commands: list[str],
) -> dict[str, Any]:
    return {
        "id": step_id,
        "title": source_point["title"],
        "status": source_point["status"],
        "implementation_allowed": source_point["implementation_allowed"],
        "goal": source_point["goal"],
        "success_signal": source_point["success_signal"],
        "next_commands": next_commands,
        "source_links": source_point["source_links"],
    }


def _workspace_step_by_id(workspace: dict[str, Any], step_id: str) -> dict[str, Any]:
    for step in workspace["steps"]:
        if step["id"] == step_id:
            return step
    msg = f"missing execution workspace step: {step_id}"
    raise ValueError(msg)


def _workspace_index_artifact(*, workspace: dict[str, Any], output_format: str) -> dict[str, str]:
    content = json_dumps(workspace) if output_format == "json" else _render_workspace_index_markdown(workspace)
    return {"filename": f"proof-execution-workspace-index.{_extension(output_format)}", "content": content}


def _workspace_step_artifact(
    *,
    filename_stem: str,
    step: dict[str, Any],
    output_format: str,
) -> dict[str, str]:
    content = json_dumps(step) if output_format == "json" else _render_workspace_step_markdown(step)
    return {"filename": f"{filename_stem}.{_extension(output_format)}", "content": content}


def _host_onboarding_gate_artifact(*, point: dict[str, Any], output_format: str) -> dict[str, str]:
    content = json_dumps(point) if output_format == "json" else _render_host_onboarding_gate_markdown(point)
    return {"filename": f"host-onboarding-depth-gate.{_extension(output_format)}", "content": content}


def _render_workspace_index_markdown(workspace: dict[str, Any]) -> str:
    steps = "\n".join(
        f"- `{step['id']}`: `{step['status']}`; implementation_allowed=`{str(step['implementation_allowed']).lower()}`"
        for step in workspace["steps"]
    )
    sources = "\n".join(f"- {source}" for source in workspace["source_docs"])
    return (
        "# Proof Execution Workspace\n\n"
        f"Release tag: `{workspace['release_tag']}`\n\n"
        f"Workspace status: `{workspace['workspace_status']}`\n\n"
        f"Writes records: `{str(workspace['writes_records']).lower()}`\n\n"
        f"Next action: `{workspace['next_action']}`\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{workspace['non_fabrication_policy']}\n\n"
        "## Steps\n\n"
        f"{steps}\n\n"
        "## Source Docs\n\n"
        f"{sources}\n"
    )


def _render_workspace_step_markdown(step: dict[str, Any]) -> str:
    commands = "\n".join(f"- `{command}`" for command in step["next_commands"])
    links = "\n".join(f"- {link}" for link in step.get("source_links", []))
    return (
        f"# {step['title']}\n\n"
        f"Status: `{step['status']}`\n\n"
        f"Implementation allowed: `{str(step['implementation_allowed']).lower()}`\n\n"
        f"Goal: {step['goal']}\n\n"
        f"Success signal: {step.get('success_signal', 'workspace artifacts are ready for operator execution')}\n\n"
        "## Next Commands\n\n"
        f"{commands}\n\n"
        "## Source Links\n\n"
        f"{links}\n"
    )


def _render_host_onboarding_gate_markdown(point: dict[str, Any]) -> str:
    commands = "\n".join(f"- `{command}`" for command in point["next_commands"])
    links = "\n".join(f"- {link}" for link in point["source_links"])
    return (
        "# Host onboarding depth gate\n\n"
        f"Status: `{point['status']}`\n\n"
        f"Implementation allowed: `{str(point['implementation_allowed']).lower()}`\n\n"
        "Depth work stays blocked until P0 real-host evidence and beta validation external gates are open.\n\n"
        f"Goal: {point['goal']}\n\n"
        f"Success signal: {point['success_signal']}\n\n"
        "## Next Commands\n\n"
        f"{commands}\n\n"
        "## Source Links\n\n"
        f"{links}\n"
    )


def _index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    content = json_dumps(report) if output_format == "json" else _render_index_markdown(report)
    return {"filename": f"combined-proof-sprint-index.{_extension(output_format)}", "content": content}


def _point_artifact(*, point: dict[str, Any], output_format: str) -> dict[str, str]:
    content = json_dumps(point) if output_format == "json" else _render_point_markdown(point)
    return {"filename": f"{_point_artifact_slug(point)}.{_extension(output_format)}", "content": content}


def _render_index_markdown(report: dict[str, Any]) -> str:
    points = "\n".join(
        f"- `{point['id']}`: `{point['status']}`; implementation_allowed="
        f"`{str(point['implementation_allowed']).lower()}`"
        for point in report["points"]
    )
    sources = "\n".join(f"- {source}" for source in report["source_docs"])
    return (
        "# Combined Proof Sprint\n\n"
        f"Release tag: `{report['release_tag']}`\n\n"
        f"Sprint status: `{report['sprint_status']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Next action: `{report['next_action']}`\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{report['non_fabrication_policy']}\n\n"
        "## Points\n\n"
        f"{points}\n\n"
        "## Source Docs\n\n"
        f"{sources}\n"
    )


def _render_point_markdown(point: dict[str, Any]) -> str:
    commands = "\n".join(f"- `{command}`" for command in point["next_commands"])
    links = "\n".join(f"- {link}" for link in point["source_links"])
    return (
        f"# {point['title']}\n\n"
        f"Status: `{point['status']}`\n\n"
        f"Implementation allowed: `{str(point['implementation_allowed']).lower()}`\n\n"
        f"Goal: {point['goal']}\n\n"
        f"Success signal: {point['success_signal']}\n\n"
        "## Next Commands\n\n"
        f"{commands}\n\n"
        "## Source Links\n\n"
        f"{links}\n"
    )


def _extension(output_format: str) -> str:
    return "json" if output_format == "json" else "md"


def _point_artifact_slug(point: dict[str, Any]) -> str:
    return str(point.get("artifact_slug", point["id"].replace("_", "-")))


def json_dumps(payload: dict[str, Any]) -> str:
    """Serialize proof sprint artifacts with stable formatting."""
    import json

    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
