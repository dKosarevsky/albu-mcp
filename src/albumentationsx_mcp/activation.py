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


def build_manual_evidence_runbook(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
) -> dict[str, Any]:
    """Build a report-only runbook for collecting real evidence and beta responses."""
    command_center = build_activation_command_center(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    return {
        "runbook_status": command_center["center_status"],
        "release_tag": release_tag,
        "host_records_path": str(host_records_path),
        "beta_records_path": str(beta_records_path),
        "writes_records": False,
        "execution_policy": "report_only",
        "non_fabrication_policy": (
            "Record passed only after a reviewer observes the real MCP host UI flow; demo fixture output is not "
            "P0 evidence and generated smoke output alone is not accepted."
        ),
        "operator_scenario": _manual_evidence_operator_scenario(),
        "expected_outputs": _manual_evidence_expected_outputs(),
        "command_center_summary": {
            "center_status": command_center["center_status"],
            "trust_score": command_center["trust_dashboard"]["trust_score"],
            "publish_allowed": command_center["rc_candidate"]["publish_allowed"],
            "blocked_reasons": command_center["rc_candidate"]["blocked_reasons"],
        },
        "next_actions": [
            "Run the scenario commands in order on a real MCP host.",
            "Import passed records only after reviewer-observed host UI evidence exists.",
            "Regenerate trust dashboard and RC candidate packet after imports.",
        ],
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


def render_manual_evidence_runbook_markdown(report: dict[str, Any]) -> str:
    """Render the manual evidence runbook as Markdown."""
    scenario = "\n\n".join(
        (
            f"### {index}. {step['name']}\n\n"
            f"Expected output: {step['expected_output']}\n\n"
            "```bash\n"
            f"{step['command']}\n"
            "```"
        )
        for index, step in enumerate(report["operator_scenario"], start=1)
    )
    expected_outputs = "\n".join(
        (
            f"- `{item['command_family']}`: blocked=`{item['status_when_blocked']}`, "
            f"ready=`{item['status_when_ready']}`"
        )
        for item in report["expected_outputs"]
    )
    next_actions = "\n".join(f"- {action}" for action in report["next_actions"])
    return (
        "# Manual Real Evidence Runbook\n\n"
        f"Release tag: `{report['release_tag']}`\n\n"
        f"Runbook status: `{report['runbook_status']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{report['non_fabrication_policy']}\n\n"
        "## Operator Scenario\n\n"
        f"{scenario}\n\n"
        "## Expected Outputs\n\n"
        f"{expected_outputs}\n\n"
        "## Next Actions\n\n"
        f"{next_actions}\n"
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


def _manual_evidence_operator_scenario() -> list[dict[str, str]]:
    return [
        {
            "name": "Inspect current release gates",
            "command": "albu-mcp activation command-center --format markdown",
            "expected_output": "Activation command center with blocked or ready gate summary.",
        },
        {
            "name": "Write P0 host operator packets",
            "command": "albu-mcp evidence packet-bundle --output-dir docs/operator-packets --format markdown",
            "expected_output": "Packet bundle index plus one packet for Codex and Claude Code.",
        },
        {
            "name": "Prepare Codex import fields",
            "command": "albu-mcp evidence import-checklist --host Codex --format markdown",
            "expected_output": "No-write checklist with validate and import commands.",
        },
        {
            "name": "Prepare Claude Code import fields",
            "command": "albu-mcp evidence import-checklist --host 'Claude Code' --format markdown",
            "expected_output": "No-write checklist with validate and import commands.",
        },
        {
            "name": "Validate one reviewer-observed import",
            "command": (
                "albu-mcp evidence validate-import --host Codex --status passed --date YYYY-MM-DD "
                "--evidence 'reviewer observed real host UI' --artifact docs/assets/demo/demo_report.md "
                "--confirm-real-host-observed --format json"
            ),
            "expected_output": "ready_to_import with writes_records=false.",
        },
        {
            "name": "Import the reviewed evidence",
            "command": (
                "albu-mcp evidence import-artifacts --host Codex --status passed --date YYYY-MM-DD "
                "--evidence 'reviewer observed real host UI' --artifact docs/assets/demo/demo_report.md "
                "--confirm-real-host-observed"
            ),
            "expected_output": "Writes both manual_host_ui and first_10_minutes_replay for the selected host.",
        },
        {
            "name": "Check privacy and artifact quality",
            "command": "albu-mcp evidence privacy-doctor --format json",
            "expected_output": "ready only when required P0 hosts have redacted artifact refs.",
        },
        {
            "name": "Validate beta response drafts",
            "command": "albu-mcp beta response-validate --input beta-response.json --format json",
            "expected_output": "ready_to_import with private_data_included=false.",
        },
        {
            "name": "Review trust gates",
            "command": "albu-mcp trust dashboard --format markdown",
            "expected_output": "Trust score and next safest command.",
        },
        {
            "name": "Prepare RC owner review",
            "command": "albu-mcp rc candidate-packet --format markdown",
            "expected_output": "Publish commands stay empty while gates are blocked.",
        },
    ]


def _manual_evidence_expected_outputs() -> list[dict[str, str]]:
    return [
        {
            "command_family": "activation command-center",
            "status_when_blocked": "blocked",
            "status_when_ready": "ready",
        },
        {
            "command_family": "evidence validate-import",
            "status_when_blocked": "validation_error",
            "status_when_ready": "ready_to_import",
        },
        {
            "command_family": "trust dashboard",
            "status_when_blocked": "action_required",
            "status_when_ready": "ready",
        },
        {
            "command_family": "rc candidate-packet",
            "status_when_blocked": "blocked",
            "status_when_ready": "ready_for_release_manager_review",
        },
    ]
