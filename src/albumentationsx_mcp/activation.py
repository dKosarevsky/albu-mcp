"""Report-only activation command center for blocked release gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import WorkflowId, build_beta_intake_wizard
from albumentationsx_mcp.evidence import P0_REQUIRED_HOSTS, build_evidence_execution_packet
from albumentationsx_mcp.rc_reopen import build_rc_candidate_packet
from albumentationsx_mcp.trust import build_trust_dashboard_report

_BETA_WORKFLOW_IDS: tuple[WorkflowId, ...] = (
    "dataset_health_before_training",
    "noisy_preview_tuning",
    "robustness_distortion_variants",
)


def build_activation_command_center(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
) -> dict[str, Any]:
    """Build one report-only operator command center across the remaining release gates."""
    trust_dashboard = build_trust_dashboard_report(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    rc_candidate = build_rc_candidate_packet(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    p0_evidence_packets = [
        build_evidence_execution_packet(host=host, path=host_records_path) for host in P0_REQUIRED_HOSTS
    ]
    beta_intake_wizards = [build_beta_intake_wizard(workflow_id=workflow_id) for workflow_id in _BETA_WORKFLOW_IDS]
    blocked = trust_dashboard["dashboard_status"] != "ready" or not rc_candidate["publish_allowed"]
    return {
        "center_status": "blocked" if blocked else "ready",
        "execution_policy": "report_only",
        "release_tag": release_tag,
        "host_records_path": str(host_records_path),
        "beta_records_path": str(beta_records_path),
        "p0_hosts": list(P0_REQUIRED_HOSTS),
        "trust_dashboard": trust_dashboard,
        "rc_candidate": rc_candidate,
        "p0_evidence_packets": p0_evidence_packets,
        "beta_intake_wizards": beta_intake_wizards,
        "operator_commands": _operator_commands(),
    }


def render_activation_command_center_markdown(report: dict[str, Any]) -> str:
    """Render an activation command center report as Markdown."""
    commands = "\n".join(f"- `{command}`" for command in report["operator_commands"])
    p0_hosts = ", ".join(f"`{host}`" for host in report["p0_hosts"])
    beta_workflows = "\n".join(f"- `{wizard['workflow_id']}`" for wizard in report["beta_intake_wizards"])
    return (
        "# AlbumentationsX MCP Activation Command Center\n\n"
        f"Release tag: `{report['release_tag']}`\n\n"
        f"Center status: `{report['center_status']}`\n\n"
        f"Execution policy: `{report['execution_policy']}`\n\n"
        f"P0 hosts: {p0_hosts}\n\n"
        f"Trust score: `{report['trust_dashboard']['trust_score']}`\n\n"
        "## Beta Workflows\n\n"
        f"{beta_workflows}\n\n"
        "## Operator Commands\n\n"
        f"{commands}\n"
    )


def _operator_commands() -> list[str]:
    return [
        "albu-mcp trust dashboard --format markdown",
        "albu-mcp evidence packet-bundle --output-dir docs/operator-packets --format markdown",
        "albu-mcp evidence import-checklist --host Codex --format markdown",
        "albu-mcp evidence privacy-doctor --format json",
        "albu-mcp beta intake-wizard --workflow-id noisy_preview_tuning --format json",
        "albu-mcp beta response-validate --input beta-response.json --format json",
        "albu-mcp rc candidate-packet --format markdown",
    ]
