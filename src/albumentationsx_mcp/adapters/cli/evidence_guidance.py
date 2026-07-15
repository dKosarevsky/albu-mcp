"""Evidence packet, proof, doctor, and status CLI adapter."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, get_args

from albumentationsx_mcp.evidence import (
    EvidenceCollectWizardRequest,
    HostName,
    build_evidence_artifact_doctor_report,
    build_evidence_close_host_report,
    build_evidence_collect_wizard,
    build_evidence_doctor_report,
    build_evidence_execution_packet,
    build_evidence_import_checklist,
    build_evidence_operator_packet_artifact,
    build_evidence_packet_bundle_artifacts,
    build_evidence_privacy_doctor_report,
    build_evidence_replay_fixture_pack_artifact,
    build_evidence_session_plan,
    build_evidence_unblock_plan,
    render_evidence_import_checklist_markdown,
    summarize_host_manual_runs,
    validate_host_manual_runs,
)
from albumentationsx_mcp.evidence_proof import (
    EvidenceProofRequest,
    EvidenceTransitionPackRequest,
    RcUnblockPreviewRequest,
    build_evidence_proof_runner,
    build_evidence_proof_status,
    build_evidence_transition_pack_artifacts,
    build_operator_transcript_template_artifact,
    build_rc_unblock_preview,
)

GUIDANCE_COMMANDS = (
    "run-session",
    "execution-packet",
    "operator-packet",
    "packet-bundle",
    "import-checklist",
    "replay-fixture-pack",
    "collect",
    "proof-runner",
    "proof-status",
    "transition-pack",
    "rc-unblock-preview",
    "transcript-template",
    "doctor",
    "artifact-doctor",
    "privacy-doctor",
    "unblock-plan",
    "status",
    "close-host",
)

CommandHandler = Callable[[argparse.Namespace], str]


def register_guidance_parsers(subparsers: Any) -> None:
    """Register packet, proof, doctor, and status commands."""
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

    packet_bundle = subparsers.add_parser(
        "packet-bundle",
        help="Write P0 host evidence operator packet artifacts.",
    )
    packet_bundle.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    packet_bundle.add_argument("--output-dir", type=Path, required=True)
    packet_bundle.add_argument("--format", choices=["markdown", "json"], default="markdown")

    import_checklist = subparsers.add_parser(
        "import-checklist",
        help="Build a no-write evidence import checklist.",
    )
    import_checklist.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    import_checklist.add_argument("--host", choices=get_args(HostName), required=True)
    import_checklist.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    replay_fixture_pack = subparsers.add_parser(
        "replay-fixture-pack",
        help="Write a safe local replay fixture pack that is not evidence.",
    )
    replay_fixture_pack.add_argument("--output-dir", type=Path, required=True)
    replay_fixture_pack.add_argument("--format", choices=["markdown", "json"], default="markdown")

    collect = subparsers.add_parser(
        "collect",
        help="Build a no-write operator wizard for collecting real host evidence.",
    )
    collect.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    collect.add_argument("--host", choices=get_args(HostName), required=True)
    collect.add_argument("--date", required=True)
    collect.add_argument("--reviewer", required=True)
    collect.add_argument("--output-dir", type=Path, default=Path("evidence-session"))
    collect.add_argument("--artifact", default="docs/assets/demo/demo_report.md")
    collect.add_argument("--format", choices=["text", "json"], default="text")

    _add_proof_parsers(subparsers)
    _add_doctor_parsers(subparsers)


def _add_proof_parsers(subparsers: Any) -> None:
    proof_runner = subparsers.add_parser(
        "proof-runner",
        help="Validate one evidence manifest and print the safe import sequence.",
    )
    proof_runner.add_argument("--input", type=Path, required=True)
    proof_runner.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    proof_runner.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    proof_runner.add_argument("--format", choices=["text", "json"], default="text")

    proof_status = subparsers.add_parser("proof-status", help="Report required P0 host evidence gaps.")
    proof_status.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    proof_status.add_argument("--format", choices=["text", "json"], default="text")

    transition_pack = subparsers.add_parser(
        "transition-pack",
        help="Write a no-record trust transition and RC go-check preview pack.",
    )
    transition_pack.add_argument("--before-host-records", type=Path, required=True)
    transition_pack.add_argument("--after-host-records", type=Path, required=True)
    transition_pack.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    transition_pack.add_argument("--output-dir", type=Path, required=True)
    transition_pack.add_argument("--release-tag", default="v1.15.0-rc.1")
    transition_pack.add_argument("--format", choices=["markdown", "json"], default="markdown")

    rc_unblock_preview = subparsers.add_parser(
        "rc-unblock-preview",
        help="Preview RC blockers and no-write unlock commands.",
    )
    rc_unblock_preview.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    rc_unblock_preview.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    rc_unblock_preview.add_argument("--release-tag", default="v1.15.0-rc.1")
    rc_unblock_preview.add_argument("--format", choices=["text", "json"], default="text")

    transcript_template = subparsers.add_parser(
        "transcript-template",
        help="Write a privacy-safe operator transcript template.",
    )
    transcript_template.add_argument("--host", choices=get_args(HostName), required=True)
    transcript_template.add_argument("--output-dir", type=Path, required=True)
    transcript_template.add_argument("--format", choices=["markdown", "json"], default="markdown")


def _add_doctor_parsers(subparsers: Any) -> None:
    doctor = subparsers.add_parser("doctor", help="Inspect P0 evidence gates and print remediation actions.")
    doctor.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    doctor.add_argument("--format", choices=["text", "json"], default="text")

    artifact_doctor = subparsers.add_parser("artifact-doctor", help="Inspect evidence artifact completeness.")
    artifact_doctor.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    artifact_doctor.add_argument("--format", choices=["text", "json"], default="text")

    privacy_doctor = subparsers.add_parser("privacy-doctor", help="Inspect evidence privacy and artifact refs.")
    privacy_doctor.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    privacy_doctor.add_argument("--format", choices=["text", "json"], default="text")

    unblock_plan = subparsers.add_parser("unblock-plan", help="Build a prioritized real-host unblock plan.")
    unblock_plan.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    unblock_plan.add_argument("--format", choices=["text", "json"], default="text")

    status = subparsers.add_parser("status", help="Validate host evidence records and print a compact count.")
    status.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))

    close_host = subparsers.add_parser("close-host", help="Report whether one host evidence gate is closed.")
    close_host.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    close_host.add_argument("--host", choices=get_args(HostName), required=True)
    close_host.add_argument("--format", choices=["text", "json"], default="text")


def _handle_run_session(args: argparse.Namespace) -> str:
    plan = build_evidence_session_plan(host=args.host, path=args.path)
    if args.format == "json":
        return json.dumps(plan, indent=2, sort_keys=True) + "\n"
    return (
        f"evidence session {plan['session_status']} for {args.host}; "
        "follow operator_steps and import artifacts after reviewer observation\n"
    )


def _handle_execution_packet(args: argparse.Namespace) -> str:
    packet = build_evidence_execution_packet(host=args.host, path=args.path)
    if args.format == "json":
        return json.dumps(packet, indent=2, sort_keys=True) + "\n"
    return f"evidence execution-packet {packet['packet_status']} for {args.host}\n"


def _handle_operator_packet(args: argparse.Namespace) -> str:
    artifact = build_evidence_operator_packet_artifact(
        host=args.host,
        path=args.path,
        output_format=args.format,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    packet_path = args.output_dir / artifact["filename"]
    packet_path.write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence operator-packet for {args.host} to {packet_path}\n"


def _handle_packet_bundle(args: argparse.Namespace) -> str:
    bundle = build_evidence_packet_bundle_artifacts(path=args.path, output_format=args.format)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    index_path = args.output_dir / bundle["index"]["filename"]
    index_path.write_text(bundle["index"]["content"], encoding="utf-8")
    for artifact in bundle["packets"]:
        (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence packet-bundle for {bundle['host_count']} P0 hosts to {index_path}\n"


def _handle_import_checklist(args: argparse.Namespace) -> str:
    checklist = build_evidence_import_checklist(host=args.host, path=args.path)
    if args.format == "json":
        return json.dumps(checklist, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_evidence_import_checklist_markdown(checklist)
    return f"evidence import-checklist {checklist['checklist_status']} for {args.host}\n"


def _handle_replay_fixture_pack(args: argparse.Namespace) -> str:
    artifact = build_evidence_replay_fixture_pack_artifact(output_format=args.format)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pack_path = args.output_dir / artifact["filename"]
    pack_path.write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence replay-fixture-pack to {pack_path}\n"


def _handle_collect(args: argparse.Namespace) -> str:
    wizard = build_evidence_collect_wizard(
        EvidenceCollectWizardRequest(
            host=args.host,
            path=args.path,
            run_date=args.date,
            reviewer=args.reviewer,
            output_dir=args.output_dir,
            artifact_ref=args.artifact,
        )
    )
    if args.format == "json":
        return json.dumps(wizard, indent=2, sort_keys=True) + "\n"
    return (
        f"evidence collect {wizard['wizard_status']} for {args.host} "
        f"(writes_records={str(wizard['writes_records']).lower()})\n"
    )


def _handle_proof_runner(args: argparse.Namespace) -> str:
    report = build_evidence_proof_runner(
        EvidenceProofRequest(
            manifest_path=args.input,
            records_path=args.path,
            beta_records_path=args.beta_records,
        )
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"evidence proof-runner {report['runner_status']} for {report['host']}\n"


def _handle_proof_status(args: argparse.Namespace) -> str:
    report = build_evidence_proof_status(records_path=args.path)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return (
        f"evidence proof-status {report['status']} "
        f"(blocked_hosts={report['blocked_host_count']}/{report['host_count']})\n"
    )


def _handle_transition_pack(args: argparse.Namespace) -> str:
    pack = build_evidence_transition_pack_artifacts(
        EvidenceTransitionPackRequest(
            before_host_records_path=args.before_host_records,
            after_host_records_path=args.after_host_records,
            beta_records_path=args.beta_records,
            release_tag=args.release_tag,
            output_format=args.format,
        )
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for artifact in pack["artifacts"]:
        (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence transition-pack with {pack['artifact_count']} artifacts to {args.output_dir}\n"


def _handle_rc_unblock_preview(args: argparse.Namespace) -> str:
    preview = build_rc_unblock_preview(
        RcUnblockPreviewRequest(
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
            release_tag=args.release_tag,
        )
    )
    if args.format == "json":
        return json.dumps(preview, indent=2, sort_keys=True) + "\n"
    return (
        f"evidence rc-unblock-preview {preview['preview_status']} "
        f"(blocked_reasons={len(preview['blocked_reasons'])}, publish_allowed="
        f"{str(preview['publish_allowed']).lower()})\n"
    )


def _handle_transcript_template(args: argparse.Namespace) -> str:
    artifact = build_operator_transcript_template_artifact(host=args.host, output_format=args.format)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    template_path = args.output_dir / artifact["filename"]
    template_path.write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence transcript-template for {args.host} to {template_path}\n"


def _handle_doctor(args: argparse.Namespace) -> str:
    report = build_evidence_doctor_report(args.path)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return (
        f"evidence doctor rc_reopen_allowed={str(report['rc_reopen_allowed']).lower()} "
        f"(passed={report['summary']['passed_gate_count']}/{report['summary']['required_gate_count']})\n"
    )


def _handle_artifact_doctor(args: argparse.Namespace) -> str:
    report = build_evidence_artifact_doctor_report(args.path)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"evidence artifact-doctor {report['artifact_status']} (issues={report['issue_count']})\n"


def _handle_privacy_doctor(args: argparse.Namespace) -> str:
    report = build_evidence_privacy_doctor_report(args.path)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"evidence privacy-doctor {report['privacy_status']} (issues={report['issue_count']})\n"


def _handle_unblock_plan(args: argparse.Namespace) -> str:
    plan = build_evidence_unblock_plan(args.path)
    if args.format == "json":
        return json.dumps(plan, indent=2, sort_keys=True) + "\n"
    return f"evidence unblock-plan {plan['plan_status']} (blocked_hosts={plan['blocked_host_count']})\n"


def _handle_status(args: argparse.Namespace) -> str:
    return f"{summarize_host_manual_runs(validate_host_manual_runs(args.path))}\n"


def _handle_close_host(args: argparse.Namespace) -> str:
    report = build_evidence_close_host_report(host=args.host, path=args.path)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return (
        f"evidence close-host {report['closure_status']} for {args.host} "
        f"(missing_gates={len(report['missing_gates'])})\n"
    )


GUIDANCE_HANDLERS: dict[str, CommandHandler] = {
    "run-session": _handle_run_session,
    "execution-packet": _handle_execution_packet,
    "operator-packet": _handle_operator_packet,
    "packet-bundle": _handle_packet_bundle,
    "import-checklist": _handle_import_checklist,
    "replay-fixture-pack": _handle_replay_fixture_pack,
    "collect": _handle_collect,
    "proof-runner": _handle_proof_runner,
    "proof-status": _handle_proof_status,
    "transition-pack": _handle_transition_pack,
    "rc-unblock-preview": _handle_rc_unblock_preview,
    "transcript-template": _handle_transcript_template,
    "doctor": _handle_doctor,
    "artifact-doctor": _handle_artifact_doctor,
    "privacy-doctor": _handle_privacy_doctor,
    "unblock-plan": _handle_unblock_plan,
    "status": _handle_status,
    "close-host": _handle_close_host,
}
