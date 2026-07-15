"""RC, distribution, and trust CLI adapters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from albumentationsx_mcp.adapters.cli.contracts import CliGroupSurface
from albumentationsx_mcp.distribution import build_distribution_readiness_report
from albumentationsx_mcp.rc_reopen import (
    build_rc_candidate_packet,
    build_rc_go_check_report,
    build_rc_rehearsal_report,
    build_rc_reopen_report,
    build_release_owner_packet,
    render_rc_candidate_packet_markdown,
    render_rc_go_check_markdown,
    render_release_owner_packet_markdown,
)
from albumentationsx_mcp.release_review import ReleaseReviewPackRequest, build_release_owner_review_pack_artifacts
from albumentationsx_mcp.trust import (
    build_trust_audit_report,
    build_trust_dashboard_report,
    build_trust_gate_transition_report,
    build_trust_next_action,
    render_trust_dashboard_markdown,
    render_trust_gate_transition_markdown,
)

RC_SURFACE = CliGroupSurface(
    group="rc",
    commands=("reopen", "rehearse", "candidate-packet", "go-check", "release-owner-packet", "review-pack"),
)
DISTRIBUTION_SURFACE = CliGroupSurface(group="distribution", commands=("readiness",))
TRUST_SURFACE = CliGroupSurface(group="trust", commands=("audit", "next", "dashboard", "gate-transition"))


def build_rc_parser() -> argparse.ArgumentParser:
    """Build the RC readiness command parser."""
    parser = argparse.ArgumentParser(description="Report RC reopen readiness without mutating release state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    reopen = subparsers.add_parser("reopen", help="Build an RC reopen go/no-go report.")
    _add_release_record_arguments(reopen)
    reopen.add_argument("--format", choices=["text", "json"], default="text")

    rehearse = subparsers.add_parser("rehearse", help="Build an RC reopen rehearsal report.")
    _add_release_record_arguments(rehearse)
    rehearse.add_argument("--format", choices=["text", "json"], default="text")

    candidate_packet = subparsers.add_parser("candidate-packet", help="Build an RC candidate packet.")
    _add_release_record_arguments(candidate_packet)
    candidate_packet.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    go_check = subparsers.add_parser("go-check", help="Build a final report-only RC go/no-go check.")
    _add_release_record_arguments(go_check)
    go_check.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    release_owner_packet = subparsers.add_parser(
        "release-owner-packet",
        help="Build a release-owner handoff packet without publish actions.",
    )
    _add_release_record_arguments(release_owner_packet)
    release_owner_packet.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    review_pack = subparsers.add_parser("review-pack", help="Write release owner review artifacts.")
    review_pack.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    review_pack.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    review_pack.add_argument("--before-host-records", type=Path, default=None)
    review_pack.add_argument("--before-beta-records", type=Path, default=None)
    review_pack.add_argument("--output-dir", type=Path, required=True)
    review_pack.add_argument("--release-tag", default="v1.15.0-rc.1")
    review_pack.add_argument("--format", choices=["markdown", "json"], default="markdown")
    return parser


def run_rc(argv: list[str]) -> None:
    """Run an RC readiness command."""
    args = build_rc_parser().parse_args(argv)
    try:
        sys.stdout.write(handle_rc_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def handle_rc_command(args: argparse.Namespace) -> str:
    """Execute one parsed RC readiness command."""
    handlers = {
        "reopen": _handle_rc_reopen,
        "rehearse": _handle_rc_rehearse,
        "candidate-packet": _handle_rc_candidate_packet,
        "go-check": _handle_rc_go_check,
        "release-owner-packet": _handle_rc_release_owner_packet,
        "review-pack": _handle_rc_review_pack,
    }
    return handlers[args.command](args)


def _handle_rc_reopen(args: argparse.Namespace) -> str:
    report = build_rc_reopen_report(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    return (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else f"rc reopen {report['rc_decision']} (publish_allowed={str(report['publish_allowed']).lower()})\n"
    )


def _handle_rc_rehearse(args: argparse.Namespace) -> str:
    report = build_rc_rehearsal_report(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    return (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else f"rc rehearse {report['rehearsal_status']} for {args.release_tag}\n"
    )


def _handle_rc_release_owner_packet(args: argparse.Namespace) -> str:
    packet = build_release_owner_packet(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.format == "json":
        return json.dumps(packet, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_release_owner_packet_markdown(packet)
    return (
        f"rc release-owner-packet {packet['packet_status']} "
        f"(publish_allowed={str(packet['publish_allowed']).lower()})\n"
    )


def _handle_rc_go_check(args: argparse.Namespace) -> str:
    report = build_rc_go_check_report(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_rc_go_check_markdown(report)
    return (
        f"rc go-check {report['go_decision']} "
        f"(can_create_release_artifacts={str(report['can_create_release_artifacts']).lower()})\n"
    )


def _handle_rc_review_pack(args: argparse.Namespace) -> str:
    pack = build_release_owner_review_pack_artifacts(
        ReleaseReviewPackRequest(
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
            before_host_records_path=args.before_host_records,
            before_beta_records_path=args.before_beta_records,
            release_tag=args.release_tag,
            output_format=args.format,
        )
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for artifact in pack["artifacts"]:
        (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
    return f"wrote rc review-pack with {pack['artifact_count']} artifacts to {args.output_dir}\n"


def _handle_rc_candidate_packet(args: argparse.Namespace) -> str:
    packet = build_rc_candidate_packet(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.format == "json":
        return json.dumps(packet, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_rc_candidate_packet_markdown(packet)
    return (
        f"rc candidate-packet {packet['candidate_status']} (publish_allowed={str(packet['publish_allowed']).lower()})\n"
    )


def build_distribution_parser() -> argparse.ArgumentParser:
    """Build the public distribution readiness parser."""
    parser = argparse.ArgumentParser(description="Report public distribution readiness without publishing.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    readiness = subparsers.add_parser("readiness", help="Build a public distribution readiness report.")
    _add_release_record_arguments(readiness)
    readiness.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def run_distribution(argv: list[str]) -> None:
    """Run the distribution readiness command."""
    args = build_distribution_parser().parse_args(argv)
    try:
        sys.stdout.write(handle_distribution_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def handle_distribution_command(args: argparse.Namespace) -> str:
    """Execute the parsed distribution readiness command."""
    report = build_distribution_readiness_report(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return (
        f"distribution readiness {report['distribution_status']} "
        f"(publish_allowed={str(report['publish_allowed']).lower()})\n"
    )


def build_trust_parser() -> argparse.ArgumentParser:
    """Build the trust gate audit parser."""
    parser = argparse.ArgumentParser(description="Audit trust gates without mutating release state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Build a unified evidence, beta, and distribution audit.")
    _add_release_record_arguments(audit)
    audit.add_argument("--format", choices=["text", "json"], default="text")

    next_action = subparsers.add_parser("next", help="Print the next safest trust-gate action.")
    _add_release_record_arguments(next_action)
    next_action.add_argument("--format", choices=["text", "json"], default="text")

    dashboard = subparsers.add_parser("dashboard", help="Build a unified trust gate dashboard.")
    _add_release_record_arguments(dashboard)
    dashboard.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    gate_transition = subparsers.add_parser(
        "gate-transition",
        help="Compare trust gates before and after importing real records.",
    )
    gate_transition.add_argument("--before-host-records", type=Path, required=True)
    gate_transition.add_argument("--before-beta-records", type=Path, required=True)
    gate_transition.add_argument("--after-host-records", type=Path, required=True)
    gate_transition.add_argument("--after-beta-records", type=Path, required=True)
    gate_transition.add_argument("--release-tag", default="v1.15.0-rc.1")
    gate_transition.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    return parser


def run_trust(argv: list[str]) -> None:
    """Run a trust gate command."""
    args = build_trust_parser().parse_args(argv)
    try:
        sys.stdout.write(handle_trust_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def handle_trust_command(args: argparse.Namespace) -> str:
    """Execute one parsed trust gate command."""
    handlers = {
        "audit": _handle_trust_audit,
        "next": _handle_trust_next,
        "dashboard": _handle_trust_dashboard,
        "gate-transition": _handle_trust_gate_transition,
    }
    return handlers[args.command](args)


def _handle_trust_audit(args: argparse.Namespace) -> str:
    report = build_trust_audit_report(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    return (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else (
            f"trust audit {report['audit_status']} "
            f"(trust_score={report['trust_score']}, next='{report['recommended_next_command']}')\n"
        )
    )


def _handle_trust_next(args: argparse.Namespace) -> str:
    report = build_trust_next_action(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    return (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else f"trust next {report['next_status']} {report['recommended_command']}\n"
    )


def _handle_trust_gate_transition(args: argparse.Namespace) -> str:
    report = build_trust_gate_transition_report(
        before_host_records_path=args.before_host_records,
        before_beta_records_path=args.before_beta_records,
        after_host_records_path=args.after_host_records,
        after_beta_records_path=args.after_beta_records,
        release_tag=args.release_tag,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_trust_gate_transition_markdown(report)
    return (
        f"trust gate-transition {report['transition_status']} "
        f"(before={report['before_trust_score']}, after={report['after_trust_score']})\n"
    )


def _handle_trust_dashboard(args: argparse.Namespace) -> str:
    report = build_trust_dashboard_report(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_trust_dashboard_markdown(report)
    return (
        f"trust dashboard {report['dashboard_status']} "
        f"(trust_score={report['trust_score']}, next='{report['recommended_command']}')\n"
    )


def _add_release_record_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    parser.add_argument("--release-tag", default="v1.15.0-rc.1")
