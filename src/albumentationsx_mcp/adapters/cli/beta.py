"""Privacy-safe beta validation CLI adapter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, get_args

from pydantic import ValidationError

from albumentationsx_mcp.adapters.cli.contracts import CliGroupSurface
from albumentationsx_mcp.beta_validation import (
    BetaValidationRecord,
    TriageBucket,
    ValidationStatus,
    WorkflowId,
    build_beta_attempt_triage,
    build_beta_campaign_plan,
    build_beta_intake_wizard,
    build_beta_loop_pack_artifacts,
    build_beta_response_template_artifacts,
    build_beta_trial_pack,
    build_beta_validation_report,
    import_beta_response_draft,
    import_beta_response_draft_dir,
    load_beta_response_draft,
    record_beta_validation,
    summarize_beta_validation_records,
    validate_beta_response_draft,
    validate_beta_validation_records,
)

SURFACE = CliGroupSurface(
    group="beta",
    commands=(
        "record-attempt",
        "status",
        "triage",
        "report",
        "campaign-plan",
        "trial-pack",
        "intake-wizard",
        "loop-pack",
        "response-validate",
        "response-import",
        "response-import-dir",
        "response-template",
    ),
)


def build_beta_parser() -> argparse.ArgumentParser:
    """Build the beta validation command parser."""
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

    loop_pack = subparsers.add_parser("loop-pack", help="Write a privacy-safe beta validation loop pack.")
    loop_pack.add_argument("--path", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    loop_pack.add_argument("--output-dir", type=Path, required=True)
    loop_pack.add_argument("--participant-role", default="ML practitioner")
    loop_pack.add_argument("--format", choices=["markdown", "json"], default="markdown")

    _add_response_parsers(subparsers)
    return parser


def _add_response_parsers(subparsers: Any) -> None:
    response_validate = subparsers.add_parser(
        "response-validate",
        help="Validate a privacy-safe beta response draft without writing records.",
    )
    response_validate.add_argument("--input", type=Path, required=True)
    response_validate.add_argument("--format", choices=["text", "json"], default="text")

    response_import = subparsers.add_parser(
        "response-import",
        help="Import a privacy-safe beta response draft into validation records.",
    )
    response_import.add_argument("--input", type=Path, required=True)
    response_import.add_argument("--path", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))

    response_import_dir = subparsers.add_parser(
        "response-import-dir",
        help="Import every privacy-safe beta response draft in a directory.",
    )
    response_import_dir.add_argument("--input-dir", type=Path, required=True)
    response_import_dir.add_argument("--path", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    response_import_dir.add_argument("--format", choices=["text", "json"], default="text")

    response_template = subparsers.add_parser(
        "response-template",
        help="Write privacy-safe beta response JSON templates for all workflows.",
    )
    response_template.add_argument("--output-dir", type=Path, required=True)
    response_template.add_argument("--participant-role", default="ML practitioner")
    response_template.add_argument("--format", choices=["json"], default="json")


def run_beta(argv: list[str]) -> None:
    """Run a beta validation command."""
    args = build_beta_parser().parse_args(argv)
    try:
        sys.stdout.write(handle_beta_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def handle_beta_command(args: argparse.Namespace) -> str:
    """Execute one parsed beta validation command."""
    handlers = {
        "record-attempt": _handle_record_attempt,
        "status": _handle_status,
        "triage": _handle_triage,
        "report": _handle_report,
        "campaign-plan": _handle_campaign_plan,
        "trial-pack": _handle_trial_pack,
        "intake-wizard": _handle_intake_wizard,
        "loop-pack": _handle_loop_pack,
        "response-validate": _handle_response_validate,
        "response-import": _handle_response_import,
        "response-import-dir": _handle_response_import_dir,
        "response-template": _handle_response_template,
    }
    return handlers[args.command](args)


def _handle_record_attempt(args: argparse.Namespace) -> str:
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


def _handle_status(args: argparse.Namespace) -> str:
    return f"{summarize_beta_validation_records(validate_beta_validation_records(args.path))}\n"


def _handle_triage(args: argparse.Namespace) -> str:
    triage_payload = build_beta_attempt_triage(validate_beta_validation_records(args.path))
    if args.format == "json":
        return json.dumps(triage_payload, indent=2, sort_keys=True) + "\n"
    return (
        f"beta triage {triage_payload['triage_status']} "
        f"(records={triage_payload['summary']['record_count']}, "
        f"product_depth_allowed={str(triage_payload['product_depth_allowed']).lower()})\n"
    )


def _handle_report(args: argparse.Namespace) -> str:
    report_payload = build_beta_validation_report(validate_beta_validation_records(args.path))
    if args.format == "json":
        return json.dumps(report_payload, indent=2, sort_keys=True) + "\n"
    return (
        f"beta report {report_payload['report_status']} "
        f"(records={report_payload['summary']['record_count']}, "
        f"candidate_backlog_items={report_payload['summary']['candidate_backlog_item_count']})\n"
    )


def _handle_campaign_plan(args: argparse.Namespace) -> str:
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


def _handle_trial_pack(args: argparse.Namespace) -> str:
    validate_beta_validation_records(args.path)
    trial_pack = build_beta_trial_pack(
        workflow_id=args.workflow_id,
        participant_role=args.participant_role,
    )
    if args.format == "json":
        return json.dumps(trial_pack, indent=2, sort_keys=True) + "\n"
    return f"beta trial-pack {trial_pack['pack_status']} for {args.workflow_id}\n"


def _handle_intake_wizard(args: argparse.Namespace) -> str:
    wizard = build_beta_intake_wizard(
        workflow_id=args.workflow_id,
        participant_role=args.participant_role,
    )
    if args.format == "json":
        return json.dumps(wizard, indent=2, sort_keys=True) + "\n"
    return f"beta intake-wizard {wizard['wizard_status']} for {args.workflow_id}\n"


def _handle_loop_pack(args: argparse.Namespace) -> str:
    pack = build_beta_loop_pack_artifacts(
        validate_beta_validation_records(args.path),
        participant_role=args.participant_role,
        output_format=args.format,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for artifact in pack["artifacts"]:
        (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
    return f"wrote beta loop-pack with {pack['artifact_count']} artifacts to {args.output_dir}\n"


def _handle_response_validate(args: argparse.Namespace) -> str:
    report = validate_beta_response_draft(load_beta_response_draft(args.input))
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"beta response-validate {report['validation_status']} for {report['record']['workflow_id']}\n"


def _handle_response_import(args: argparse.Namespace) -> str:
    draft = load_beta_response_draft(args.input)
    import_beta_response_draft(path=args.path, draft=draft)
    return f"imported beta response {draft.workflow_id} into {args.path}\n"


def _handle_response_import_dir(args: argparse.Namespace) -> str:
    report = import_beta_response_draft_dir(input_dir=args.input_dir, path=args.path)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"imported {report['imported_count']} beta responses into {args.path}\n"


def _handle_response_template(args: argparse.Namespace) -> str:
    artifacts = build_beta_response_template_artifacts(participant_role=args.participant_role)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for artifact in artifacts:
        (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
    return f"wrote {len(artifacts)} beta response-template files to {args.output_dir}\n"
