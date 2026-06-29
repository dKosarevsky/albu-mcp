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
    build_beta_validation_report,
    record_beta_validation,
    summarize_beta_validation_records,
    validate_beta_validation_records,
)
from albumentationsx_mcp.evidence import (
    EvidenceArtifactImport,
    FirstTenMinutesReplayEvidence,
    HostName,
    HostStatus,
    build_evidence_doctor_report,
    build_evidence_session_plan,
    import_evidence_artifacts,
    record_first_10_minutes_replay,
    record_host_manual_run,
    summarize_host_manual_runs,
    validate_host_manual_runs,
)
from albumentationsx_mcp.rc_reopen import build_rc_reopen_report
from albumentationsx_mcp.server import ServerSettings, create_mcp_server, settings_from_environment

_SUBCOMMANDS = {"beta", "evidence", "rc"}


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

    import_artifacts = subparsers.add_parser(
        "import-artifacts",
        help="Import one reviewer-observed evidence session into both required P0 gates.",
    )
    _add_host_record_arguments(import_artifacts)
    import_artifacts.add_argument("--artifact", action="append", default=[])
    import_artifacts.add_argument("--confirm-real-host-observed", action="store_true")

    doctor = subparsers.add_parser("doctor", help="Inspect P0 evidence gates and print remediation actions.")
    doctor.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    doctor.add_argument("--format", choices=["text", "json"], default="text")

    status = subparsers.add_parser("status", help="Validate host evidence records and print a compact count.")
    status.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))

    args = parser.parse_args(argv)
    try:
        if args.command == "record-host-ui":
            record_host_manual_run(
                path=args.path,
                host=args.host,
                status=args.status,
                run_date=args.date,
                evidence=args.evidence,
            )
            output = f"recorded {args.host} {args.status} on {args.date} in {args.path}\n"
        elif args.command == "record-first-10-minutes":
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
            output = f"recorded first-10-minutes {args.host} {args.status} on {args.date} in {args.path}\n"
        elif args.command == "run-session":
            plan = build_evidence_session_plan(host=args.host, path=args.path)
            if args.format == "json":
                output = json.dumps(plan, indent=2, sort_keys=True) + "\n"
            else:
                output = (
                    f"evidence session {plan['session_status']} for {args.host}; "
                    "follow operator_steps and import artifacts after reviewer observation\n"
                )
        elif args.command == "import-artifacts":
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
            output = (
                f"imported {args.host} {args.status} evidence for manual_host_ui and "
                f"first_10_minutes_replay in {args.path}\n"
            )
        elif args.command == "doctor":
            report = build_evidence_doctor_report(args.path)
            if args.format == "json":
                output = json.dumps(report, indent=2, sort_keys=True) + "\n"
            else:
                output = (
                    f"evidence doctor rc_reopen_allowed={str(report['rc_reopen_allowed']).lower()} "
                    f"(passed={report['summary']['passed_gate_count']}/"
                    f"{report['summary']['required_gate_count']})\n"
                )
        else:
            output = f"{summarize_host_manual_runs(validate_host_manual_runs(args.path))}\n"
        sys.stdout.write(output)
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


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

    args = parser.parse_args(argv)
    try:
        if args.command == "record-attempt":
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
            sys.stdout.write(f"recorded beta validation attempt {args.workflow_id} in {args.path}\n")
            return
        if args.command == "status":
            sys.stdout.write(f"{summarize_beta_validation_records(validate_beta_validation_records(args.path))}\n")
            return
        if args.command == "triage":
            triage_payload = build_beta_attempt_triage(validate_beta_validation_records(args.path))
            if args.format == "json":
                sys.stdout.write(json.dumps(triage_payload, indent=2, sort_keys=True) + "\n")
                return
            sys.stdout.write(
                f"beta triage {triage_payload['triage_status']} "
                f"(records={triage_payload['summary']['record_count']}, "
                f"product_depth_allowed={str(triage_payload['product_depth_allowed']).lower()})\n"
            )
            return
        if args.command == "report":
            report_payload = build_beta_validation_report(validate_beta_validation_records(args.path))
            if args.format == "json":
                sys.stdout.write(json.dumps(report_payload, indent=2, sort_keys=True) + "\n")
                return
            sys.stdout.write(
                f"beta report {report_payload['report_status']} "
                f"(records={report_payload['summary']['record_count']}, "
                f"candidate_backlog_items={report_payload['summary']['candidate_backlog_item_count']})\n"
            )
            return
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _run_rc_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Report RC reopen readiness without mutating release state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    reopen = subparsers.add_parser("reopen", help="Build an RC reopen go/no-go report.")
    reopen.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    reopen.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    reopen.add_argument("--release-tag", default="v1.15.0-rc.1")
    reopen.add_argument("--format", choices=["text", "json"], default="text")

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
