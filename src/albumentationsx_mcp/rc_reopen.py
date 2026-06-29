"""RC reopen decision helpers that never mutate release state."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import build_beta_validation_report, validate_beta_validation_records
from albumentationsx_mcp.evidence import build_evidence_doctor_report

_PREFLIGHT_COMMANDS = [
    "uv run pytest -q",
    "uv run ruff check .",
    "uv run ruff format --check .",
    "uv run ty check",
    "uv run python scripts/check_release_readiness.py",
    "uv build",
]


def build_rc_reopen_report(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
) -> dict[str, Any]:
    """Build a go/no-go report for reopening an RC without creating tags or releases."""
    evidence = build_evidence_doctor_report(host_records_path)
    beta = build_beta_validation_report(validate_beta_validation_records(beta_records_path))
    blocked_reasons = _blocked_reasons(evidence=evidence, beta=beta)
    publish_allowed = not blocked_reasons
    return {
        "rc_decision": "ready_for_rc_reopen" if publish_allowed else "hold_rc",
        "release_tag": release_tag,
        "publish_allowed": publish_allowed,
        "blocked_reasons": blocked_reasons,
        "evidence_summary": evidence["summary"],
        "beta_summary": beta["summary"],
        "preflight_commands": _PREFLIGHT_COMMANDS,
        "publish_commands": _publish_commands(release_tag) if publish_allowed else [],
        "next_action": _next_action(publish_allowed=publish_allowed),
        "execution_policy": "Report only; this command does not create tags, releases, or uploads.",
    }


def build_rc_rehearsal_report(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
) -> dict[str, Any]:
    """Build an RC reopen rehearsal plan without mutating tags, releases, or uploads."""
    reopen = build_rc_reopen_report(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    ready = bool(reopen["publish_allowed"])
    return {
        "rehearsal_status": "ready" if ready else "hold",
        "release_tag": release_tag,
        "execution_policy": "report_only",
        "blocked_reasons": reopen["blocked_reasons"],
        "preflight_commands": reopen["preflight_commands"],
        "allowed_publish_commands": reopen["publish_commands"] if ready else [],
        "release_note_artifacts": [
            "docs/RC_RELEASE_DECISION_REPORT.md",
            "docs/GOVERNED_100_ITERATION_REPORT.md",
            "docs/POLICY_ASSISTANT_MVP_CONTRACT.md",
        ],
        "release_note_sections": [
            "Trust gate status",
            "Real-host evidence summary",
            "Beta validation summary",
            "Policy assistant changes",
            "Distribution readiness",
        ],
        "next_actions": _rehearsal_next_actions(ready=ready),
    }


def build_rc_candidate_packet(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
) -> dict[str, Any]:
    """Build an RC candidate packet without creating tags, releases, or uploads."""
    reopen = build_rc_reopen_report(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    publish_allowed = bool(reopen["publish_allowed"])
    return {
        "candidate_status": "ready_for_release_manager_review" if publish_allowed else "blocked",
        "release_tag": release_tag,
        "publish_allowed": publish_allowed,
        "blocked_reasons": reopen["blocked_reasons"],
        "evidence_summary": reopen["evidence_summary"],
        "beta_summary": reopen["beta_summary"],
        "preflight_commands": reopen["preflight_commands"],
        "publish_commands": reopen["publish_commands"] if publish_allowed else [],
        "operator_commands": _candidate_operator_commands(publish_allowed=publish_allowed),
        "release_note_artifacts": [
            "docs/RC_RELEASE_DECISION_REPORT.md",
            "docs/GOVERNED_100_ITERATION_REPORT.md",
            "docs/POLICY_ASSISTANT_MVP_CONTRACT.md",
            "docs/USAGE.md",
        ],
        "execution_policy": "Report only; this packet does not create tags, releases, or uploads.",
        "next_actions": _candidate_next_actions(publish_allowed=publish_allowed),
    }


def render_rc_candidate_packet_markdown(packet: dict[str, Any]) -> str:
    """Render an RC candidate packet as markdown."""
    blocked_reasons = "\n".join(f"- `{reason}`" for reason in packet["blocked_reasons"]) or "- none"
    preflight = "\n".join(f"- `{command}`" for command in packet["preflight_commands"])
    publish = "\n".join(f"- `{command}`" for command in packet["publish_commands"]) or "- none while blocked"
    operator_commands = "\n".join(f"- `{command}`" for command in packet["operator_commands"])
    next_actions = "\n".join(f"- {action}" for action in packet["next_actions"])
    return (
        "# RC Candidate Packet\n\n"
        f"Release tag: `{packet['release_tag']}`\n\n"
        f"Candidate status: `{packet['candidate_status']}`\n\n"
        f"Publish allowed: `{str(packet['publish_allowed']).lower()}`\n\n"
        f"Execution policy: {packet['execution_policy']}\n\n"
        "## Blocked Reasons\n\n"
        f"{blocked_reasons}\n\n"
        "## Operator Commands\n\n"
        f"{operator_commands}\n\n"
        "## Preflight Commands\n\n"
        f"{preflight}\n\n"
        "## Publish Commands\n\n"
        f"{publish}\n\n"
        "## Next Actions\n\n"
        f"{next_actions}\n"
    )


def _blocked_reasons(*, evidence: dict[str, Any], beta: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not evidence["rc_reopen_allowed"]:
        reasons.append("p0_host_evidence_missing_or_blocked")
    if not beta["product_depth_allowed"]:
        reasons.append("beta_validation_incomplete")
    return reasons


def _publish_commands(release_tag: str) -> list[str]:
    return [
        f"git tag {release_tag}",
        f"git push origin {release_tag}",
        f"gh release create {release_tag} --prerelease --generate-notes",
    ]


def _next_action(*, publish_allowed: bool) -> str:
    if publish_allowed:
        return "Review preflight output, then run publish commands manually if release ownership approves."
    return "Do not tag or publish the RC; complete blocked evidence and beta gates first."


def _rehearsal_next_actions(*, ready: bool) -> list[str]:
    if ready:
        return [
            "Review allowed_publish_commands with release ownership before running them manually.",
            "Use release_note_artifacts to draft the RC release notes.",
        ]
    return [
        "Do not tag or publish during rehearsal while gates are blocked.",
        "Run albu-mcp trust next --format json and complete the recommended gate first.",
    ]


def _candidate_operator_commands(*, publish_allowed: bool) -> list[str]:
    if publish_allowed:
        return [
            "albu-mcp rc candidate-packet --format markdown",
            "albu-mcp distribution readiness --format json",
        ]
    return [
        "albu-mcp trust dashboard --format markdown",
        "albu-mcp evidence operator-packet --host Codex --output-dir docs/operator-packets",
        "albu-mcp evidence validate-import --host Codex --status passed --date YYYY-MM-DD --evidence 'reviewer observed real host UI' --artifact docs/assets/demo/demo_report.md --confirm-real-host-observed --format json",
        "albu-mcp beta intake-wizard --workflow-id noisy_preview_tuning --format json",
    ]


def _candidate_next_actions(*, publish_allowed: bool) -> list[str]:
    if publish_allowed:
        return [
            "Review preflight output with release ownership.",
            "Run publish commands manually only after release owner approval.",
        ]
    return [
        "Keep RC blocked while real-host evidence or beta validation gates are incomplete.",
        "Use operator_commands to collect real records, then regenerate this packet.",
    ]
