"""Command-line entry point for the AlbumentationsX MCP server and operator workflows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

from albumentationsx_mcp.beta_validation import (
    BetaValidationRecord,
    TriageBucket,
    ValidationStatus,
    WorkflowId,
    build_beta_attempt_triage,
    build_beta_campaign_plan,
    build_beta_intake_wizard,
    build_beta_trial_pack,
    build_beta_validation_report,
    record_beta_validation,
    summarize_beta_validation_records,
    validate_beta_validation_records,
)
from albumentationsx_mcp.distribution import build_distribution_readiness_report
from albumentationsx_mcp.evidence import (
    EvidenceArtifactImport,
    FirstTenMinutesReplayEvidence,
    HostName,
    HostStatus,
    build_evidence_artifact_doctor_report,
    build_evidence_doctor_report,
    build_evidence_execution_packet,
    build_evidence_operator_packet_artifact,
    build_evidence_session_plan,
    build_evidence_unblock_plan,
    import_evidence_artifacts,
    record_first_10_minutes_replay,
    record_host_manual_run,
    summarize_host_manual_runs,
    validate_evidence_artifact_import,
    validate_host_manual_runs,
)
from albumentationsx_mcp.rc_reopen import (
    build_rc_candidate_packet,
    build_rc_rehearsal_report,
    build_rc_reopen_report,
    render_rc_candidate_packet_markdown,
)
from albumentationsx_mcp.server import ServerSettings, create_mcp_server, settings_from_environment
from albumentationsx_mcp.trust import (
    build_trust_audit_report,
    build_trust_dashboard_report,
    build_trust_next_action,
    render_trust_dashboard_markdown,
)

_SUBCOMMANDS = {"beta", "distribution", "evidence", "rc", "trust"}


def main(argv: list[str] | None = None) -> None:
    """Run the requested command."""
    resolved_argv = sys.argv[1:] if argv is None else argv
    if resolved_argv and resolved_argv[0] == "evidence":
        _run_evidence_cli(resolved_argv[1:])
        return
    if resolved_argv and resolved_argv[0] == "beta":
        _run_beta_cli(resolved_argv[1:])
        return
    if resolved_argv and resolved_argv[0] == "rc":
        _run_rc_cli(resolved_argv[1:])
        return
    if resolved_argv and resolved_argv[0] == "distribution":
        _run_distribution_cli(resolved_argv[1:])
        return
    if resolved_argv and resolved_argv[0] == "trust":
        _run_trust_cli(resolved_argv[1:])
        return
    _run_server(resolved_argv)


def _run_server(argv: list[str]) -> None:
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="Run the AlbumentationsX MCP server.")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--artifact-root", type=Path, default=None)
    parser.add_argument("--allowed-root", action="append", type=Path, default=None)
    args = parser.parse_args(argv)

    settings = settings_from_environment()
    if args.artifact_root is not None or args.allowed_root is not None:
        settings = ServerSettings(
            allowed_roots=args.allowed_root or settings.allowed_roots,
            artifact_root=args.artifact_root or settings.artifact_root,
        )

    server = create_mcp_server(settings)
    server.run(transport=args.transport)


def _run_evidence_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Record and validate real MCP host evidence.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    host_ui = subparsers.add_parser("record-host-ui", help="Record one manual host UI evidence result.")
    _add_host_record_arguments(host_ui)

    replay = subparsers.add_parser(
        "record-first-10-minutes",
        help="Record one first-10-minutes host replay evidence result.",
    )
    _add_host_record_arguments(replay)
    replay.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Artifact path or URL proving the replay. Can be repeated.",
    )

    run_session = subparsers.add_parser("run-session", help="Print a guided real-host evidence session plan.")
    run_session.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    run_session.add_argument("--host", choices=get_args(HostName), required=True)
    run_session.add_argument("--format", choices=["text", "json"], default="text")

    execution_packet = subparsers.add_parser(
        "execution-packet",
        help="Print a host-specific real MCP evidence execution packet.",
    )
    execution_packet.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    execution_packet.add_argument("--host", choices=get_args(HostName), required=True)
    execution_packet.add_argument("--format", choices=["text", "json"], default="text")

    operator_packet = subparsers.add_parser(
        "operator-packet",
        help="Write a host-specific real MCP evidence operator packet artifact.",
    )
    operator_packet.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    operator_packet.add_argument("--host", choices=get_args(HostName), required=True)
    operator_packet.add_argument("--output-dir", type=Path, required=True)
    operator_packet.add_argument("--format", choices=["markdown", "json"], default="markdown")

    import_artifacts = subparsers.add_parser(
        "import-artifacts",
        help="Import one reviewer-observed evidence session into both required P0 gates.",
    )
    _add_host_record_arguments(import_artifacts)
    import_artifacts.add_argument("--artifact", action="append", default=[])
    import_artifacts.add_argument("--confirm-real-host-observed", action="store_true")

    validate_import = subparsers.add_parser(
        "validate-import",
        help="Validate a real-host evidence import without writing records.",
    )
    _add_host_record_arguments(validate_import)
    validate_import.add_argument("--artifact", action="append", default=[])
    validate_import.add_argument("--confirm-real-host-observed", action="store_true")
    validate_import.add_argument("--format", choices=["text", "json"], default="text")

    doctor = subparsers.add_parser("doctor", help="Inspect P0 evidence gates and print remediation actions.")
    doctor.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    doctor.add_argument("--format", choices=["text", "json"], default="text")

    artifact_doctor = subparsers.add_parser("artifact-doctor", help="Inspect evidence artifact completeness.")
    artifact_doctor.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    artifact_doctor.add_argument("--format", choices=["text", "json"], default="text")

    unblock_plan = subparsers.add_parser("unblock-plan", help="Build a prioritized real-host unblock plan.")
    unblock_plan.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    unblock_plan.add_argument("--format", choices=["text", "json"], default="text")

    status = subparsers.add_parser("status", help="Validate host evidence records and print a compact count.")
    status.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))

    args = parser.parse_args(argv)
    try:
        sys.stdout.write(_handle_evidence_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _handle_evidence_command(args: argparse.Namespace) -> str:
    handlers = {
        "record-host-ui": _handle_evidence_record_host_ui,
        "record-first-10-minutes": _handle_evidence_record_first_10_minutes,
        "run-session": _handle_evidence_run_session,
        "execution-packet": _handle_evidence_execution_packet,
        "operator-packet": _handle_evidence_operator_packet,
        "import-artifacts": _handle_evidence_import_artifacts,
        "validate-import": _handle_evidence_validate_import,
        "doctor": _handle_evidence_doctor,
        "artifact-doctor": _handle_evidence_artifact_doctor,
        "unblock-plan": _handle_evidence_unblock_plan,
        "status": _handle_evidence_status,
    }
    return handlers[args.command](args)


def _handle_evidence_record_host_ui(args: argparse.Namespace) -> str:
    record_host_manual_run(
        path=args.path,
        host=args.host,
        status=args.status,
        run_date=args.date,
        evidence=args.evidence,
    )
    return f"recorded {args.host} {args.status} on {args.date} in {args.path}\n"


def _handle_evidence_record_first_10_minutes(args: argparse.Namespace) -> str:
    record_first_10_minutes_replay(
        path=args.path,
        replay=FirstTenMinutesReplayEvidence(
            host=args.host,
            status=args.status,
            run_date=args.date,
            evidence=args.evidence,
            artifacts=args.artifact,
        ),
    )
    return f"recorded first-10-minutes {args.host} {args.status} on {args.date} in {args.path}\n"


def _handle_evidence_run_session(args: argparse.Namespace) -> str:
    plan = build_evidence_session_plan(host=args.host, path=args.path)
    if args.format == "json":
        return json.dumps(plan, indent=2, sort_keys=True) + "\n"
    return (
        f"evidence session {plan['session_status']} for {args.host}; "
        "follow operator_steps and import artifacts after reviewer observation\n"
    )


def _handle_evidence_execution_packet(args: argparse.Namespace) -> str:
    packet = build_evidence_execution_packet(host=args.host, path=args.path)
    if args.format == "json":
        return json.dumps(packet, indent=2, sort_keys=True) + "\n"
    return f"evidence execution-packet {packet['packet_status']} for {args.host}\n"


def _handle_evidence_operator_packet(args: argparse.Namespace) -> str:
    artifact = build_evidence_operator_packet_artifact(
        host=args.host,
        path=args.path,
        output_format=args.format,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    packet_path = args.output_dir / artifact["filename"]
    packet_path.write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence operator-packet for {args.host} to {packet_path}\n"


def _handle_evidence_import_artifacts(args: argparse.Namespace) -> str:
    import_evidence_artifacts(
        EvidenceArtifactImport(
            path=args.path,
            host=args.host,
            status=args.status,
            run_date=args.date,
            evidence=args.evidence,
            artifacts=args.artifact,
            confirm_real_host_observed=args.confirm_real_host_observed,
        )
    )
    return (
        f"imported {args.host} {args.status} evidence for manual_host_ui and first_10_minutes_replay in {args.path}\n"
    )


def _handle_evidence_validate_import(args: argparse.Namespace) -> str:
    report = validate_evidence_artifact_import(
        EvidenceArtifactImport(
            path=args.path,
            host=args.host,
            status=args.status,
            run_date=args.date,
            evidence=args.evidence,
            artifacts=args.artifact,
            confirm_real_host_observed=args.confirm_real_host_observed,
        )
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return (
        f"evidence validate-import {report['validation_status']} "
        f"(host={args.host}, artifacts={report['artifact_count']})\n"
    )


def _handle_evidence_doctor(args: argparse.Namespace) -> str:
    report = build_evidence_doctor_report(args.path)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return (
        f"evidence doctor rc_reopen_allowed={str(report['rc_reopen_allowed']).lower()} "
        f"(passed={report['summary']['passed_gate_count']}/{report['summary']['required_gate_count']})\n"
    )


def _handle_evidence_artifact_doctor(args: argparse.Namespace) -> str:
    report = build_evidence_artifact_doctor_report(args.path)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"evidence artifact-doctor {report['artifact_status']} (issues={report['issue_count']})\n"


def _handle_evidence_unblock_plan(args: argparse.Namespace) -> str:
    plan = build_evidence_unblock_plan(args.path)
    if args.format == "json":
        return json.dumps(plan, indent=2, sort_keys=True) + "\n"
    return f"evidence unblock-plan {plan['plan_status']} (blocked_hosts={plan['blocked_host_count']})\n"


def _handle_evidence_status(args: argparse.Namespace) -> str:
    return f"{summarize_host_manual_runs(validate_host_manual_runs(args.path))}\n"


def _run_beta_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Record and validate privacy-safe beta validation attempts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    attempt = subparsers.add_parser("record-attempt", help="Record one redacted beta validation attempt.")
    attempt.add_argument("--path", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    attempt.add_argument("--workflow-id", choices=get_args(WorkflowId), required=True)
    attempt.add_argument("--status", choices=get_args(ValidationStatus), required=True)
    attempt.add_argument("--attempt-date", required=True)
    attempt.add_argument("--participant-role", required=True)
    attempt.add_argument("--summary", required=True)
    attempt.add_argument("--triage-bucket", choices=get_args(TriageBucket), required=True)
    attempt.add_argument("--artifact-ref", action="append", default=[])

    status = subparsers.add_parser("status", help="Validate beta records and print a compact count.")
    status.add_argument("--path", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))

    triage = subparsers.add_parser("triage", help="Map beta attempts to backlog-oriented triage lanes.")
    triage.add_argument("--path", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    triage.add_argument("--format", choices=["text", "json"], default="text")

    report = subparsers.add_parser("report", help="Build a redacted beta decision report.")
    report.add_argument("--path", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    report.add_argument("--format", choices=["text", "json"], default="text")

    campaign_plan = subparsers.add_parser("campaign-plan", help="Build a privacy-safe beta campaign plan.")
    campaign_plan.add_argument("--path", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    campaign_plan.add_argument("--target-participants", type=int, default=3)
    campaign_plan.add_argument("--format", choices=["text", "json"], default="text")

    trial_pack = subparsers.add_parser("trial-pack", help="Build a privacy-safe beta trial handoff.")
    trial_pack.add_argument("--path", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    trial_pack.add_argument("--workflow-id", choices=get_args(WorkflowId), required=True)
    trial_pack.add_argument("--participant-role", default="ML practitioner")
    trial_pack.add_argument("--format", choices=["text", "json"], default="text")

    intake_wizard = subparsers.add_parser("intake-wizard", help="Build a privacy-safe beta intake wizard.")
    intake_wizard.add_argument("--workflow-id", choices=get_args(WorkflowId), required=True)
    intake_wizard.add_argument("--participant-role", default="ML practitioner")
    intake_wizard.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args(argv)
    try:
        sys.stdout.write(_handle_beta_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _handle_beta_command(args: argparse.Namespace) -> str:
    handlers = {
        "record-attempt": _handle_beta_record_attempt,
        "status": _handle_beta_status,
        "triage": _handle_beta_triage,
        "report": _handle_beta_report,
        "campaign-plan": _handle_beta_campaign_plan,
        "trial-pack": _handle_beta_trial_pack,
        "intake-wizard": _handle_beta_intake_wizard,
    }
    return handlers[args.command](args)


def _handle_beta_record_attempt(args: argparse.Namespace) -> str:
    record_beta_validation(
        path=args.path,
        record=BetaValidationRecord(
            workflow_id=args.workflow_id,
            status=args.status,
            attempt_date=args.attempt_date,
            participant_role=args.participant_role,
            summary=args.summary,
            triage_bucket=args.triage_bucket,
            artifact_refs=args.artifact_ref,
            private_data_included=False,
        ),
    )
    return f"recorded beta validation attempt {args.workflow_id} in {args.path}\n"


def _handle_beta_status(args: argparse.Namespace) -> str:
    return f"{summarize_beta_validation_records(validate_beta_validation_records(args.path))}\n"


def _handle_beta_triage(args: argparse.Namespace) -> str:
    triage_payload = build_beta_attempt_triage(validate_beta_validation_records(args.path))
    if args.format == "json":
        return json.dumps(triage_payload, indent=2, sort_keys=True) + "\n"
    return (
        f"beta triage {triage_payload['triage_status']} "
        f"(records={triage_payload['summary']['record_count']}, "
        f"product_depth_allowed={str(triage_payload['product_depth_allowed']).lower()})\n"
    )


def _handle_beta_report(args: argparse.Namespace) -> str:
    report_payload = build_beta_validation_report(validate_beta_validation_records(args.path))
    if args.format == "json":
        return json.dumps(report_payload, indent=2, sort_keys=True) + "\n"
    return (
        f"beta report {report_payload['report_status']} "
        f"(records={report_payload['summary']['record_count']}, "
        f"candidate_backlog_items={report_payload['summary']['candidate_backlog_item_count']})\n"
    )


def _handle_beta_campaign_plan(args: argparse.Namespace) -> str:
    campaign_payload = build_beta_campaign_plan(
        validate_beta_validation_records(args.path),
        target_participants=args.target_participants,
    )
    if args.format == "json":
        return json.dumps(campaign_payload, indent=2, sort_keys=True) + "\n"
    return (
        f"beta campaign-plan {campaign_payload['campaign_status']} "
        f"(workflows={campaign_payload['workflow_trial_count']}, "
        f"target_participants={campaign_payload['target_participant_count']})\n"
    )


def _handle_beta_trial_pack(args: argparse.Namespace) -> str:
    validate_beta_validation_records(args.path)
    trial_pack = build_beta_trial_pack(
        workflow_id=args.workflow_id,
        participant_role=args.participant_role,
    )
    if args.format == "json":
        return json.dumps(trial_pack, indent=2, sort_keys=True) + "\n"
    return f"beta trial-pack {trial_pack['pack_status']} for {args.workflow_id}\n"


def _handle_beta_intake_wizard(args: argparse.Namespace) -> str:
    wizard = build_beta_intake_wizard(
        workflow_id=args.workflow_id,
        participant_role=args.participant_role,
    )
    if args.format == "json":
        return json.dumps(wizard, indent=2, sort_keys=True) + "\n"
    return f"beta intake-wizard {wizard['wizard_status']} for {args.workflow_id}\n"


def _run_rc_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Report RC reopen readiness without mutating release state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    reopen = subparsers.add_parser("reopen", help="Build an RC reopen go/no-go report.")
    reopen.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    reopen.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    reopen.add_argument("--release-tag", default="v1.15.0-rc.1")
    reopen.add_argument("--format", choices=["text", "json"], default="text")

    rehearse = subparsers.add_parser("rehearse", help="Build an RC reopen rehearsal report.")
    rehearse.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    rehearse.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    rehearse.add_argument("--release-tag", default="v1.15.0-rc.1")
    rehearse.add_argument("--format", choices=["text", "json"], default="text")

    candidate_packet = subparsers.add_parser("candidate-packet", help="Build an RC candidate packet.")
    candidate_packet.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    candidate_packet.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    candidate_packet.add_argument("--release-tag", default="v1.15.0-rc.1")
    candidate_packet.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    args = parser.parse_args(argv)
    try:
        if args.command == "reopen":
            report = build_rc_reopen_report(
                host_records_path=args.host_records,
                beta_records_path=args.beta_records,
                release_tag=args.release_tag,
            )
            if args.format == "json":
                sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
                return
            sys.stdout.write(
                f"rc reopen {report['rc_decision']} (publish_allowed={str(report['publish_allowed']).lower()})\n"
            )
            return
        if args.command == "rehearse":
            report = build_rc_rehearsal_report(
                host_records_path=args.host_records,
                beta_records_path=args.beta_records,
                release_tag=args.release_tag,
            )
            if args.format == "json":
                sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
                return
            sys.stdout.write(f"rc rehearse {report['rehearsal_status']} for {args.release_tag}\n")
            return
        if args.command == "candidate-packet":
            packet = build_rc_candidate_packet(
                host_records_path=args.host_records,
                beta_records_path=args.beta_records,
                release_tag=args.release_tag,
            )
            if args.format == "json":
                sys.stdout.write(json.dumps(packet, indent=2, sort_keys=True) + "\n")
                return
            if args.format == "markdown":
                sys.stdout.write(render_rc_candidate_packet_markdown(packet))
                return
            sys.stdout.write(
                f"rc candidate-packet {packet['candidate_status']} "
                f"(publish_allowed={str(packet['publish_allowed']).lower()})\n"
            )
            return
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _run_distribution_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Report public distribution readiness without publishing.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    readiness = subparsers.add_parser("readiness", help="Build a public distribution readiness report.")
    readiness.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    readiness.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    readiness.add_argument("--release-tag", default="v1.15.0-rc.1")
    readiness.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args(argv)
    try:
        report = build_distribution_readiness_report(
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
            release_tag=args.release_tag,
        )
        if args.format == "json":
            sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
            return
        sys.stdout.write(
            f"distribution readiness {report['distribution_status']} "
            f"(publish_allowed={str(report['publish_allowed']).lower()})\n"
        )
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _run_trust_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Audit trust gates without mutating release state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Build a unified evidence, beta, and distribution audit.")
    audit.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    audit.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    audit.add_argument("--release-tag", default="v1.15.0-rc.1")
    audit.add_argument("--format", choices=["text", "json"], default="text")

    next_action = subparsers.add_parser("next", help="Print the next safest trust-gate action.")
    next_action.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    next_action.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    next_action.add_argument("--release-tag", default="v1.15.0-rc.1")
    next_action.add_argument("--format", choices=["text", "json"], default="text")

    dashboard = subparsers.add_parser("dashboard", help="Build a unified trust gate dashboard.")
    dashboard.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    dashboard.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    dashboard.add_argument("--release-tag", default="v1.15.0-rc.1")
    dashboard.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    args = parser.parse_args(argv)
    try:
        if args.command == "audit":
            report = build_trust_audit_report(
                host_records_path=args.host_records,
                beta_records_path=args.beta_records,
                release_tag=args.release_tag,
            )
            if args.format == "json":
                sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
                return
            sys.stdout.write(
                f"trust audit {report['audit_status']} "
                f"(trust_score={report['trust_score']}, next='{report['recommended_next_command']}')\n"
            )
            return
        if args.command == "next":
            report = build_trust_next_action(
                host_records_path=args.host_records,
                beta_records_path=args.beta_records,
                release_tag=args.release_tag,
            )
            if args.format == "json":
                sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
                return
            sys.stdout.write(f"trust next {report['next_status']} {report['recommended_command']}\n")
            return
        if args.command == "dashboard":
            report = build_trust_dashboard_report(
                host_records_path=args.host_records,
                beta_records_path=args.beta_records,
                release_tag=args.release_tag,
            )
            if args.format == "json":
                sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
                return
            if args.format == "markdown":
                sys.stdout.write(render_trust_dashboard_markdown(report))
                return
            sys.stdout.write(
                f"trust dashboard {report['dashboard_status']} "
                f"(trust_score={report['trust_score']}, next='{report['recommended_command']}')\n"
            )
            return
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _add_host_record_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    parser.add_argument("--host", choices=get_args(HostName), required=True)
    parser.add_argument("--status", choices=get_args(HostStatus), required=True)
    parser.add_argument("--date", required=True, help="ISO date, for example 2026-06-28.")
    parser.add_argument("--evidence", required=True)


if __name__ == "__main__":
    main()
