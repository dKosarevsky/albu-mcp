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
    record_beta_validation,
    summarize_beta_validation_records,
    validate_beta_validation_records,
)
from albumentationsx_mcp.evidence import (
    FirstTenMinutesReplayEvidence,
    HostName,
    HostStatus,
    record_first_10_minutes_replay,
    record_host_manual_run,
    summarize_host_manual_runs,
    validate_host_manual_runs,
)
from albumentationsx_mcp.server import ServerSettings, create_mcp_server, settings_from_environment

_SUBCOMMANDS = {"beta", "evidence"}


def main(argv: list[str] | None = None) -> None:
    """Run the requested command."""
    resolved_argv = sys.argv[1:] if argv is None else argv
    if resolved_argv and resolved_argv[0] == "evidence":
        _run_evidence_cli(resolved_argv[1:])
        return
    if resolved_argv and resolved_argv[0] == "beta":
        _run_beta_cli(resolved_argv[1:])
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
            sys.stdout.write(f"recorded {args.host} {args.status} on {args.date} in {args.path}\n")
            return
        if args.command == "record-first-10-minutes":
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
            sys.stdout.write(f"recorded first-10-minutes {args.host} {args.status} on {args.date} in {args.path}\n")
            return
        if args.command == "status":
            sys.stdout.write(f"{summarize_host_manual_runs(validate_host_manual_runs(args.path))}\n")
            return
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
