"""Command-line entry point for the AlbumentationsX MCP server and operator workflows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, get_args

from pydantic import ValidationError

from albumentationsx_mcp.acquisition_cycle import (
    AcquisitionCycleRequest,
    build_acquisition_cycle,
    build_acquisition_cycle_artifacts,
    render_acquisition_cycle_markdown,
)
from albumentationsx_mcp.activation import (
    build_activation_command_center,
    build_manual_evidence_runbook,
    render_activation_command_center_markdown,
    render_manual_evidence_runbook_markdown,
)
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
from albumentationsx_mcp.distribution import build_distribution_readiness_report
from albumentationsx_mcp.evidence import (
    EvidenceArtifactImport,
    EvidenceCollectWizardRequest,
    FirstTenMinutesReplayEvidence,
    HostName,
    HostStatus,
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
    build_evidence_session_folder_artifacts,
    build_evidence_session_manifest_artifact,
    build_evidence_session_plan,
    build_evidence_unblock_plan,
    import_evidence_artifacts,
    import_evidence_session_manifest,
    load_evidence_session_manifest,
    record_first_10_minutes_replay,
    record_host_manual_run,
    render_evidence_import_checklist_markdown,
    summarize_host_manual_runs,
    validate_evidence_artifact_import,
    validate_evidence_session_manifest,
    validate_host_manual_runs,
)
from albumentationsx_mcp.evidence_cockpit import (
    EvidenceCockpitRequest,
    build_evidence_cockpit,
    build_evidence_cockpit_artifacts,
    render_evidence_cockpit_markdown,
)
from albumentationsx_mcp.evidence_import_wizard import (
    EvidenceImportWizardRequest,
    build_evidence_import_wizard,
    render_evidence_import_wizard_json,
    render_evidence_import_wizard_markdown,
)
from albumentationsx_mcp.evidence_product_loop import (
    EvidenceProductLoopRequest,
    build_evidence_product_loop,
    build_evidence_product_loop_artifacts,
    render_evidence_product_loop_markdown,
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
from albumentationsx_mcp.first_preview import build_first_preview_pack, render_first_preview_pack_markdown
from albumentationsx_mcp.first_product_fix_selector import (
    FirstProductFixSelectorRequest,
    build_first_product_fix_selector,
    build_first_product_fix_selector_artifacts,
    render_first_product_fix_selector_json,
    render_first_product_fix_selector_markdown,
)
from albumentationsx_mcp.host_setup import (
    DEFAULT_ALLOWED_ROOT,
    DEFAULT_ARTIFACT_ROOT,
    build_host_setup_probe,
    render_host_setup_probe_markdown,
)
from albumentationsx_mcp.host_trust import build_host_trust_dashboard, render_host_trust_dashboard_markdown
from albumentationsx_mcp.intake import build_intake_bundle_artifacts
from albumentationsx_mcp.product_cycle import (
    EvidenceFirstCycleRequest,
    build_evidence_first_cycle,
    build_evidence_first_cycle_artifacts,
    render_evidence_first_cycle_markdown,
)
from albumentationsx_mcp.product_fix_closure_import import (
    ProductFixClosureImportRequest,
    build_product_fix_closure_import,
    render_product_fix_closure_import_json,
    render_product_fix_closure_import_markdown,
)
from albumentationsx_mcp.product_fix_closure_pack import (
    ProductFixClosurePackRequest,
    build_product_fix_closure_pack,
    build_product_fix_closure_pack_artifacts,
    render_product_fix_closure_pack_json,
    render_product_fix_closure_pack_markdown,
)
from albumentationsx_mcp.product_fix_closure_pipeline import (
    ProductFixClosurePipelineRequest,
    build_product_fix_closure_pipeline,
    build_product_fix_closure_pipeline_artifacts,
    render_product_fix_closure_pipeline_json,
    render_product_fix_closure_pipeline_markdown,
)
from albumentationsx_mcp.product_fix_closure_receipt import (
    ProductFixClosureReceiptRequest,
    build_product_fix_closure_receipt,
    build_product_fix_closure_receipt_artifacts,
    render_product_fix_closure_receipt_json,
    render_product_fix_closure_receipt_markdown,
)
from albumentationsx_mcp.product_fix_closure_runbook import (
    ProductFixClosureRunbookRequest,
    build_product_fix_closure_runbook,
    build_product_fix_closure_runbook_artifacts,
    render_product_fix_closure_runbook_json,
    render_product_fix_closure_runbook_markdown,
)
from albumentationsx_mcp.product_fix_closure_snapshot import (
    ProductFixClosureSnapshotRequest,
    build_product_fix_closure_snapshot,
    build_product_fix_closure_snapshot_artifacts,
    render_product_fix_closure_snapshot_json,
    render_product_fix_closure_snapshot_markdown,
)
from albumentationsx_mcp.product_fix_execution_guard import (
    ProductFixExecutionGuardRequest,
    build_product_fix_execution_guard,
    build_product_fix_execution_guard_artifacts,
    render_product_fix_execution_guard_json,
    render_product_fix_execution_guard_markdown,
)
from albumentationsx_mcp.product_fix_implementation_plan import (
    ProductFixImplementationPlanRequest,
    build_product_fix_implementation_plan,
    build_product_fix_implementation_plan_artifacts,
    render_product_fix_implementation_plan_json,
    render_product_fix_implementation_plan_markdown,
)
from albumentationsx_mcp.product_fix_outcome import (
    ProductFixOutcomeRequest,
    build_product_fix_outcome,
    build_product_fix_outcome_artifacts,
    render_product_fix_outcome_json,
    render_product_fix_outcome_markdown,
)
from albumentationsx_mcp.product_fix_outcome_capture import (
    ProductFixOutcomeCaptureRequest,
    build_product_fix_outcome_capture,
    build_product_fix_outcome_capture_artifacts,
    render_product_fix_outcome_capture_json,
    render_product_fix_outcome_capture_markdown,
)
from albumentationsx_mcp.product_fix_outcome_import_guard import (
    ProductFixOutcomeImportGuardRequest,
    build_product_fix_outcome_import_guard,
    build_product_fix_outcome_import_guard_artifacts,
    render_product_fix_outcome_import_guard_json,
    render_product_fix_outcome_import_guard_markdown,
)
from albumentationsx_mcp.product_fix_outcome_rehearsal import (
    ProductFixOutcomeRehearsalRequest,
    build_product_fix_outcome_rehearsal,
    build_product_fix_outcome_rehearsal_artifacts,
    render_product_fix_outcome_rehearsal_json,
    render_product_fix_outcome_rehearsal_markdown,
)
from albumentationsx_mcp.product_fix_validation import (
    ProductFixValidationRequest,
    build_product_fix_validation,
    build_product_fix_validation_artifacts,
    render_product_fix_validation_json,
    render_product_fix_validation_markdown,
)
from albumentationsx_mcp.proof_sprint import (
    build_combined_proof_sprint,
    build_combined_proof_sprint_artifacts,
    build_proof_execution_workspace,
    build_proof_execution_workspace_artifacts,
    build_real_proof_run_1,
    build_real_proof_run_1_artifacts,
    render_combined_proof_sprint_markdown,
    render_proof_execution_workspace_markdown,
    render_real_proof_run_1_markdown,
)
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
from albumentationsx_mcp.real_adoption_cycle import (
    RealAdoptionCycleRequest,
    build_real_adoption_cycle,
    build_real_adoption_cycle_artifacts,
    render_real_adoption_cycle_markdown,
)
from albumentationsx_mcp.release_review import ReleaseReviewPackRequest, build_release_owner_review_pack_artifacts
from albumentationsx_mcp.server import ServerSettings, create_mcp_server, settings_from_environment
from albumentationsx_mcp.trust import (
    build_trust_audit_report,
    build_trust_dashboard_report,
    build_trust_gate_transition_report,
    build_trust_next_action,
    render_trust_dashboard_markdown,
    render_trust_gate_transition_markdown,
)

_SUBCOMMANDS = {"activation", "beta", "distribution", "evidence", "host", "intake", "preview", "rc", "trust"}


def main(argv: list[str] | None = None) -> None:
    """Run the requested command."""
    resolved_argv = sys.argv[1:] if argv is None else argv
    if resolved_argv and resolved_argv[0] in _SUBCOMMANDS:
        _run_cli_subcommand(name=resolved_argv[0], argv=resolved_argv[1:])
        return
    _run_server(resolved_argv)


def _run_cli_subcommand(*, name: str, argv: list[str]) -> None:
    handlers = {
        "activation": _run_activation_cli,
        "beta": _run_beta_cli,
        "distribution": _run_distribution_cli,
        "evidence": _run_evidence_cli,
        "host": _run_host_cli,
        "intake": _run_intake_cli,
        "preview": _run_preview_cli,
        "rc": _run_rc_cli,
        "trust": _run_trust_cli,
    }
    handlers[name](argv)


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


def _run_intake_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Write release-safe manual intake bundles.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bundle = subparsers.add_parser("bundle", help="Write one manual evidence and beta intake bundle.")
    bundle.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    bundle.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    bundle.add_argument("--output-dir", type=Path, required=True)
    bundle.add_argument("--release-tag", default="v1.15.0-rc.1")
    bundle.add_argument("--participant-role", default="ML practitioner")
    bundle.add_argument("--format", choices=["markdown", "json"], default="markdown")

    args = parser.parse_args(argv)
    try:
        sys.stdout.write(_handle_intake_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _handle_intake_command(args: argparse.Namespace) -> str:
    bundle = build_intake_bundle_artifacts(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
        output_format=args.format,
        participant_role=args.participant_role,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for artifact in bundle["artifacts"]:
        (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
    return f"wrote intake bundle with {bundle['artifact_count']} artifacts to {args.output_dir}\n"


def _run_host_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Inspect host setup readiness before real MCP evidence runs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_probe = subparsers.add_parser("setup-probe", help="Build or run a host setup readiness probe.")
    setup_probe.add_argument("--host", choices=get_args(HostName), default=None)
    setup_probe.add_argument("--live", action="store_true")
    setup_probe.add_argument("--allowed-root", type=Path, default=DEFAULT_ALLOWED_ROOT)
    setup_probe.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    setup_probe.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    setup_probe.add_argument("--output", type=Path, default=None)

    next_action = subparsers.add_parser("next-action", help="Show the next real evidence action per MCP host.")
    next_action.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    next_action.add_argument("--host", choices=get_args(HostName), default=None)
    next_action.add_argument("--include-session", action="store_true")
    next_action.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    next_action.add_argument("--output", type=Path, default=None)

    args = parser.parse_args(argv)
    try:
        sys.stdout.write(_handle_host_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _handle_host_command(args: argparse.Namespace) -> str:
    if args.command == "next-action":
        return _handle_host_next_action(args)
    if args.command != "setup-probe":
        msg = f"unsupported host command: {args.command}"
        raise ValueError(msg)
    probe = build_host_setup_probe(
        host=args.host,
        live=args.live,
        allowed_root=args.allowed_root,
        artifact_root=args.artifact_root,
    )
    if args.format == "json":
        content = json.dumps(probe, indent=2, sort_keys=True) + "\n"
    elif args.format == "markdown":
        content = render_host_setup_probe_markdown(probe)
    else:
        content = (
            f"host setup-probe {probe['probe_status']} "
            f"(hosts={probe['summary']['host_count']}, next_action={probe['next_action']})\n"
        )
    if args.output is None:
        return content
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    return f"wrote host setup-probe to {args.output}\n"


def _handle_host_next_action(args: argparse.Namespace) -> str:
    report = build_host_trust_dashboard(path=args.path, host=args.host, include_session=args.include_session)
    if args.format == "json":
        content = json.dumps(report, indent=2, sort_keys=True) + "\n"
    elif args.format == "markdown":
        content = render_host_trust_dashboard_markdown(report)
    else:
        content = (
            f"host next-action {report['dashboard_status']} "
            f"(next_host={report['next_host'] or 'none'}, next='{report['next_command']}')\n"
        )
    if args.output is None:
        return content
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    return f"wrote host trust dashboard to {args.output}\n"


def _run_preview_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Build report-only preview operator handoffs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    first_pack = subparsers.add_parser("first-pack", help="Build the shortest first-preview operator handoff.")
    first_pack.add_argument("--dataset-path", type=Path, required=True)
    first_pack.add_argument("--allowed-root", type=Path, required=True)
    first_pack.add_argument("--artifact-root", type=Path, required=True)
    first_pack.add_argument("--task", default="classification")
    first_pack.add_argument("--max-images", type=int, default=8)
    first_pack.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    first_pack.add_argument("--output", type=Path, default=None)

    args = parser.parse_args(argv)
    try:
        sys.stdout.write(_handle_preview_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _handle_preview_command(args: argparse.Namespace) -> str:
    if args.command != "first-pack":
        msg = f"unsupported preview command: {args.command}"
        raise ValueError(msg)
    pack = build_first_preview_pack(
        dataset_path=args.dataset_path,
        allowed_root=args.allowed_root,
        artifact_root=args.artifact_root,
        task=args.task,
        max_images=args.max_images,
    )
    if args.format == "json":
        content = json.dumps(pack, indent=2, sort_keys=True) + "\n"
    elif args.format == "markdown":
        content = render_first_preview_pack_markdown(pack)
    else:
        content = f"preview first-pack {pack['pack_status']} (renders_images={str(pack['renders_images']).lower()})\n"
    if args.output is None:
        return content
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    return f"wrote preview first-pack to {args.output}\n"


def _run_activation_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Build report-only activation command center packets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _add_activation_command_center_parser(subparsers)
    _add_activation_runbook_parser(subparsers)
    _add_activation_proof_flow_parsers(subparsers)
    _add_activation_acquisition_cycle_parser(subparsers)
    _add_activation_evidence_cockpit_parser(subparsers)
    _add_activation_evidence_product_loop_parser(subparsers)
    _add_activation_first_product_fix_parser(subparsers)
    _add_activation_product_fix_closure_import_parser(subparsers)
    _add_activation_product_fix_closure_pack_parser(subparsers)
    _add_activation_product_fix_closure_pipeline_parser(subparsers)
    _add_activation_product_fix_closure_receipt_parser(subparsers)
    _add_activation_product_fix_closure_snapshot_parser(subparsers)
    _add_activation_product_fix_closure_runbook_parser(subparsers)
    _add_activation_product_fix_execution_guard_parser(subparsers)
    _add_activation_product_fix_implementation_plan_parser(subparsers)
    _add_activation_product_fix_outcome_capture_parser(subparsers)
    _add_activation_product_fix_outcome_import_guard_parser(subparsers)
    _add_activation_product_fix_outcome_rehearsal_parser(subparsers)
    _add_activation_product_fix_outcome_parser(subparsers)
    _add_activation_product_fix_validation_parser(subparsers)
    _add_activation_real_adoption_cycle_parser(subparsers)

    args = parser.parse_args(argv)
    try:
        sys.stdout.write(_handle_activation_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _add_activation_proof_flow_parsers(subparsers: Any) -> None:
    proof_sprint = subparsers.add_parser("proof-sprint", help="Build a combined external proof sprint.")
    proof_sprint.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    proof_sprint.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    proof_sprint.add_argument("--release-tag", default="v1.15.0-rc.1")
    proof_sprint.add_argument("--output-dir", type=Path, default=None)
    proof_sprint.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    execution_workspace = subparsers.add_parser(
        "execution-workspace",
        help="Build a no-write proof execution workspace.",
    )
    execution_workspace.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    execution_workspace.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    execution_workspace.add_argument("--release-tag", default="v1.15.0-rc.1")
    execution_workspace.add_argument("--output-dir", type=Path, default=None)
    execution_workspace.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    real_proof_run = subparsers.add_parser("real-proof-run", help="Build a no-write real proof run handoff.")
    real_proof_run.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    real_proof_run.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    real_proof_run.add_argument("--release-tag", default="v1.15.0-rc.1")
    real_proof_run.add_argument("--output-dir", type=Path, default=None)
    real_proof_run.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    evidence_first_cycle = subparsers.add_parser(
        "evidence-first-cycle",
        help="Build a no-write evidence-first product cycle.",
    )
    evidence_first_cycle.add_argument("--host", choices=get_args(HostName), required=True)
    evidence_first_cycle.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    evidence_first_cycle.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    evidence_first_cycle.add_argument("--before-host-records", type=Path, default=None)
    evidence_first_cycle.add_argument("--before-beta-records", type=Path, default=None)
    evidence_first_cycle.add_argument("--release-tag", default="v1.15.0-rc.1")
    evidence_first_cycle.add_argument("--output-dir", type=Path, default=None)
    evidence_first_cycle.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_command_center_parser(subparsers: Any) -> None:
    command_center = subparsers.add_parser("command-center", help="Build the release activation command center.")
    command_center.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    command_center.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    command_center.add_argument("--release-tag", default="v1.15.0-rc.1")
    command_center.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_runbook_parser(subparsers: Any) -> None:
    runbook = subparsers.add_parser("runbook", help="Build a manual real-evidence intake runbook.")
    runbook.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    runbook.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    runbook.add_argument("--release-tag", default="v1.15.0-rc.1")
    runbook.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_acquisition_cycle_parser(subparsers: Any) -> None:
    acquisition_cycle = subparsers.add_parser(
        "acquisition-cycle",
        help="Build a no-write real evidence and beta acquisition cycle.",
    )
    acquisition_cycle.add_argument("--host", choices=get_args(HostName), required=True)
    acquisition_cycle.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    acquisition_cycle.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    acquisition_cycle.add_argument("--release-tag", default="v1.15.0-rc.1")
    acquisition_cycle.add_argument("--output-dir", type=Path, default=None)
    acquisition_cycle.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_evidence_cockpit_parser(subparsers: Any) -> None:
    evidence_cockpit = subparsers.add_parser(
        "evidence-cockpit",
        help="Build a no-write cockpit for one real host evidence run.",
    )
    evidence_cockpit.add_argument("--host", choices=get_args(HostName), required=True)
    evidence_cockpit.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    evidence_cockpit.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    evidence_cockpit.add_argument("--release-tag", default="v1.15.0-rc.1")
    evidence_cockpit.add_argument("--output-dir", type=Path, default=None)
    evidence_cockpit.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_evidence_product_loop_parser(subparsers: Any) -> None:
    evidence_product_loop = subparsers.add_parser(
        "evidence-product-loop",
        help="Build a no-write evidence-to-product friction loop.",
    )
    evidence_product_loop.add_argument("--host", choices=get_args(HostName), required=True)
    evidence_product_loop.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    evidence_product_loop.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    evidence_product_loop.add_argument("--release-tag", default="v1.15.0-rc.1")
    evidence_product_loop.add_argument("--output-dir", type=Path, default=None)
    evidence_product_loop.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_real_adoption_cycle_parser(subparsers: Any) -> None:
    real_adoption_cycle = subparsers.add_parser(
        "real-adoption-cycle",
        help="Build a no-write real adoption cycle.",
    )
    real_adoption_cycle.add_argument("--host", choices=get_args(HostName), required=True)
    real_adoption_cycle.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    real_adoption_cycle.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    real_adoption_cycle.add_argument("--release-tag", default="v1.15.0-rc.1")
    real_adoption_cycle.add_argument("--output-dir", type=Path, default=None)
    real_adoption_cycle.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_first_product_fix_parser(subparsers: Any) -> None:
    first_product_fix = subparsers.add_parser(
        "first-product-fix",
        help="Select the first product fix after real adoption gates pass.",
    )
    first_product_fix.add_argument("--host", choices=get_args(HostName), required=True)
    first_product_fix.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    first_product_fix.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    first_product_fix.add_argument("--release-tag", default="v1.15.0-rc.1")
    first_product_fix.add_argument("--output-dir", type=Path, default=None)
    first_product_fix.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_closure_pack_parser(subparsers: Any) -> None:
    closure_pack = subparsers.add_parser(
        "product-fix-closure-pack",
        help="Build a no-write post-import closure pack for one product fix.",
    )
    closure_pack.add_argument("--host", choices=get_args(HostName), required=True)
    closure_pack.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    closure_pack.add_argument("--before-beta-records", type=Path, required=True)
    closure_pack.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    closure_pack.add_argument("--release-tag", default="v1.15.0-rc.1")
    closure_pack.add_argument("--output-dir", type=Path, default=None)
    closure_pack.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_closure_import_parser(subparsers: Any) -> None:
    closure_import = subparsers.add_parser(
        "product-fix-closure-import",
        help="Guard and execute one post-fix beta response import only after explicit confirmation.",
    )
    closure_import.add_argument("--host", choices=get_args(HostName), required=True)
    closure_import.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    closure_import.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    closure_import.add_argument("--input", type=Path, required=True)
    closure_import.add_argument("--snapshot-dir", type=Path, default=Path("docs/product-fix-closure-snapshot"))
    closure_import.add_argument("--closure-output-dir", type=Path, default=Path("docs/product-fix-closure-pack"))
    closure_import.add_argument("--release-tag", default="v1.15.0-rc.1")
    closure_import.add_argument("--confirm-import-ready", action="store_true")
    closure_import.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_closure_pipeline_parser(subparsers: Any) -> None:
    pipeline = subparsers.add_parser(
        "product-fix-closure-pipeline",
        help="Build a no-write pipeline status for closing one product fix.",
    )
    pipeline.add_argument("--host", choices=get_args(HostName), required=True)
    pipeline.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    pipeline.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    pipeline.add_argument("--input", type=Path, required=True)
    pipeline.add_argument("--snapshot-dir", type=Path, default=Path("docs/product-fix-closure-snapshot"))
    pipeline.add_argument("--closure-output-dir", type=Path, default=Path("docs/product-fix-closure-pack"))
    pipeline.add_argument("--receipt-output-dir", type=Path, default=Path("docs/product-fix-closure-receipt"))
    pipeline.add_argument("--final-outcome-output-dir", type=Path, default=Path("docs/product-fix-outcome"))
    pipeline.add_argument("--release-tag", default="v1.15.0-rc.1")
    pipeline.add_argument("--output-dir", type=Path, default=None)
    pipeline.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_closure_receipt_parser(subparsers: Any) -> None:
    receipt = subparsers.add_parser(
        "product-fix-closure-receipt",
        help="Build a no-write receipt for the guarded import-to-closure handoff.",
    )
    receipt.add_argument("--host", choices=get_args(HostName), required=True)
    receipt.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    receipt.add_argument("--before-beta-records", type=Path, required=True)
    receipt.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    receipt.add_argument("--snapshot-path", type=Path, default=None)
    receipt.add_argument("--closure-output-dir", type=Path, default=Path("docs/product-fix-closure-pack"))
    receipt.add_argument("--release-tag", default="v1.15.0-rc.1")
    receipt.add_argument("--output-dir", type=Path, default=None)
    receipt.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_closure_snapshot_parser(subparsers: Any) -> None:
    snapshot = subparsers.add_parser(
        "product-fix-closure-snapshot",
        help="Write a pre-import beta records snapshot and print the guarded import-to-closure sequence.",
    )
    snapshot.add_argument("--host", choices=get_args(HostName), required=True)
    snapshot.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    snapshot.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    snapshot.add_argument("--input", type=Path, required=True)
    snapshot.add_argument("--snapshot-dir", type=Path, default=Path("docs/product-fix-closure-snapshot"))
    snapshot.add_argument("--closure-output-dir", type=Path, default=Path("docs/product-fix-closure-pack"))
    snapshot.add_argument("--release-tag", default="v1.15.0-rc.1")
    snapshot.add_argument("--output-dir", type=Path, default=None)
    snapshot.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_closure_runbook_parser(subparsers: Any) -> None:
    runbook = subparsers.add_parser(
        "product-fix-closure-runbook",
        help="Build a no-write operator runbook from post-fix capture through closure confirmation.",
    )
    runbook.add_argument("--host", choices=get_args(HostName), required=True)
    runbook.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    runbook.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    runbook.add_argument("--input", type=Path, required=True)
    runbook.add_argument("--snapshot-dir", type=Path, default=Path("docs/product-fix-closure-snapshot"))
    runbook.add_argument("--closure-output-dir", type=Path, default=Path("docs/product-fix-closure-pack"))
    runbook.add_argument("--release-tag", default="v1.15.0-rc.1")
    runbook.add_argument("--output-dir", type=Path, default=None)
    runbook.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_implementation_plan_parser(subparsers: Any) -> None:
    implementation_plan = subparsers.add_parser(
        "product-fix-implementation-plan",
        help="Build a no-write TDD plan for the selected product fix.",
    )
    implementation_plan.add_argument("--host", choices=get_args(HostName), required=True)
    implementation_plan.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    implementation_plan.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    implementation_plan.add_argument("--release-tag", default="v1.15.0-rc.1")
    implementation_plan.add_argument("--output-dir", type=Path, default=None)
    implementation_plan.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_execution_guard_parser(subparsers: Any) -> None:
    execution_guard = subparsers.add_parser(
        "product-fix-execution-guard",
        help="Build a no-write guarded branch handoff for the selected product fix.",
    )
    execution_guard.add_argument("--host", choices=get_args(HostName), required=True)
    execution_guard.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    execution_guard.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    execution_guard.add_argument("--release-tag", default="v1.15.0-rc.1")
    execution_guard.add_argument("--output-dir", type=Path, default=None)
    execution_guard.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_validation_parser(subparsers: Any) -> None:
    validation = subparsers.add_parser(
        "product-fix-validation",
        help="Validate the selected product fix against its behavior contract.",
    )
    validation.add_argument("--host", choices=get_args(HostName), required=True)
    validation.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    validation.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    validation.add_argument("--release-tag", default="v1.15.0-rc.1")
    validation.add_argument("--output-dir", type=Path, default=None)
    validation.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_outcome_parser(subparsers: Any) -> None:
    outcome = subparsers.add_parser(
        "product-fix-outcome",
        help="Decide whether a validated product fix is accepted by real beta evidence.",
    )
    outcome.add_argument("--host", choices=get_args(HostName), required=True)
    outcome.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    outcome.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    outcome.add_argument("--release-tag", default="v1.15.0-rc.1")
    outcome.add_argument("--output-dir", type=Path, default=None)
    outcome.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_outcome_capture_parser(subparsers: Any) -> None:
    capture = subparsers.add_parser(
        "product-fix-outcome-capture",
        help="Build a no-write post-fix beta outcome capture pack.",
    )
    capture.add_argument("--host", choices=get_args(HostName), required=True)
    capture.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    capture.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    capture.add_argument("--release-tag", default="v1.15.0-rc.1")
    capture.add_argument("--participant-role", default="ML practitioner")
    capture.add_argument("--attempt-date", default=None)
    capture.add_argument("--output-dir", type=Path, default=None)
    capture.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_outcome_import_guard_parser(subparsers: Any) -> None:
    import_guard = subparsers.add_parser(
        "product-fix-outcome-import-guard",
        help="Validate one post-fix beta response draft before importing it.",
    )
    import_guard.add_argument("--host", choices=get_args(HostName), required=True)
    import_guard.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    import_guard.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    import_guard.add_argument("--input", type=Path, required=True)
    import_guard.add_argument("--release-tag", default="v1.15.0-rc.1")
    import_guard.add_argument("--output-dir", type=Path, default=None)
    import_guard.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_activation_product_fix_outcome_rehearsal_parser(subparsers: Any) -> None:
    rehearsal = subparsers.add_parser(
        "product-fix-outcome-rehearsal",
        help="Rehearse post-fix outcome capture, draft guard, and projected outcome without importing records.",
    )
    rehearsal.add_argument("--host", choices=get_args(HostName), required=True)
    rehearsal.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    rehearsal.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    rehearsal.add_argument("--input", type=Path, required=True)
    rehearsal.add_argument("--release-tag", default="v1.15.0-rc.1")
    rehearsal.add_argument("--output-dir", type=Path, default=None)
    rehearsal.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _handle_activation_command(args: argparse.Namespace) -> str:
    handlers = {
        "acquisition-cycle": _handle_activation_acquisition_cycle,
        "command-center": _handle_activation_command_center,
        "evidence-cockpit": _handle_activation_evidence_cockpit,
        "evidence-first-cycle": _handle_activation_evidence_first_cycle,
        "evidence-product-loop": _handle_activation_evidence_product_loop,
        "execution-workspace": _handle_activation_execution_workspace,
        "first-product-fix": _handle_activation_first_product_fix,
        "product-fix-closure-import": _handle_activation_product_fix_closure_import,
        "product-fix-closure-pack": _handle_activation_product_fix_closure_pack,
        "product-fix-closure-pipeline": _handle_activation_product_fix_closure_pipeline,
        "product-fix-closure-receipt": _handle_activation_product_fix_closure_receipt,
        "product-fix-closure-runbook": _handle_activation_product_fix_closure_runbook,
        "product-fix-closure-snapshot": _handle_activation_product_fix_closure_snapshot,
        "product-fix-execution-guard": _handle_activation_product_fix_execution_guard,
        "product-fix-implementation-plan": _handle_activation_product_fix_implementation_plan,
        "product-fix-outcome-capture": _handle_activation_product_fix_outcome_capture,
        "product-fix-outcome-import-guard": _handle_activation_product_fix_outcome_import_guard,
        "product-fix-outcome-rehearsal": _handle_activation_product_fix_outcome_rehearsal,
        "product-fix-outcome": _handle_activation_product_fix_outcome,
        "product-fix-validation": _handle_activation_product_fix_validation,
        "proof-sprint": _handle_activation_proof_sprint,
        "real-adoption-cycle": _handle_activation_real_adoption_cycle,
        "real-proof-run": _handle_activation_real_proof_run,
        "runbook": _handle_activation_runbook,
    }
    return handlers[args.command](args)


def _handle_activation_real_adoption_cycle(args: argparse.Namespace) -> str:
    request = RealAdoptionCycleRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_real_adoption_cycle_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return f"wrote activation real-adoption-cycle with {pack['artifact_count']} artifacts to {args.output_dir}\n"
    report = build_real_adoption_cycle(request)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_real_adoption_cycle_markdown(report)
    return f"activation real-adoption-cycle {report['cycle_status']} (lanes={report['lane_count']})\n"


def _handle_activation_first_product_fix(args: argparse.Namespace) -> str:
    request = FirstProductFixSelectorRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_first_product_fix_selector_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return f"wrote activation first-product-fix with {pack['artifact_count']} artifacts to {args.output_dir}\n"
    report = build_first_product_fix_selector(request)
    if args.format == "json":
        return render_first_product_fix_selector_json(report)
    if args.format == "markdown":
        return render_first_product_fix_selector_markdown(report)
    return (
        f"activation first-product-fix {report['selector_status']} "
        f"(implementation_allowed={str(report['implementation_allowed']).lower()})\n"
    )


def _handle_activation_product_fix_closure_pack(args: argparse.Namespace) -> str:
    request = ProductFixClosurePackRequest(
        host=args.host,
        host_records_path=args.host_records,
        before_beta_records_path=args.before_beta_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_product_fix_closure_pack_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return (
            f"wrote activation product-fix-closure-pack with {pack['artifact_count']} artifacts to {args.output_dir}\n"
        )
    report = build_product_fix_closure_pack(request)
    if args.format == "json":
        return render_product_fix_closure_pack_json(report)
    if args.format == "markdown":
        return render_product_fix_closure_pack_markdown(report)
    return (
        f"activation product-fix-closure-pack {report['closure_status']} "
        f"(new_records={report['evidence_diff']['new_record_count']})\n"
    )


def _handle_activation_product_fix_closure_import(args: argparse.Namespace) -> str:
    request = ProductFixClosureImportRequest(
        host=args.host,
        input_path=args.input,
        confirm_import_ready=args.confirm_import_ready,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        snapshot_dir=args.snapshot_dir,
        closure_output_dir=args.closure_output_dir,
        release_tag=args.release_tag,
    )
    report = build_product_fix_closure_import(request)
    if args.format == "json":
        return render_product_fix_closure_import_json(report)
    if args.format == "markdown":
        return render_product_fix_closure_import_markdown(report)
    return (
        f"activation product-fix-closure-import {report['import_status']} "
        f"(writes_records={str(report['writes_records']).lower()})\n"
    )


def _handle_activation_product_fix_closure_pipeline(args: argparse.Namespace) -> str:
    request = ProductFixClosurePipelineRequest(
        host=args.host,
        input_path=args.input,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        snapshot_dir=args.snapshot_dir,
        closure_output_dir=args.closure_output_dir,
        receipt_output_dir=args.receipt_output_dir,
        final_outcome_output_dir=args.final_outcome_output_dir,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_product_fix_closure_pipeline_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return (
            "wrote activation product-fix-closure-pipeline "
            f"with {pack['artifact_count']} artifacts to {args.output_dir}\n"
        )
    report = build_product_fix_closure_pipeline(request)
    if args.format == "json":
        return render_product_fix_closure_pipeline_json(report)
    if args.format == "markdown":
        return render_product_fix_closure_pipeline_markdown(report)
    return (
        f"activation product-fix-closure-pipeline {report['pipeline_status']} "
        f"(import_status={report['import_status']})\n"
    )


def _handle_activation_product_fix_closure_receipt(args: argparse.Namespace) -> str:
    request = ProductFixClosureReceiptRequest(
        host=args.host,
        host_records_path=args.host_records,
        before_beta_records_path=args.before_beta_records,
        beta_records_path=args.beta_records,
        snapshot_path=args.snapshot_path,
        closure_output_dir=args.closure_output_dir,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_product_fix_closure_receipt_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return (
            "wrote activation product-fix-closure-receipt "
            f"with {pack['artifact_count']} artifacts to {args.output_dir}\n"
        )
    report = build_product_fix_closure_receipt(request)
    if args.format == "json":
        return render_product_fix_closure_receipt_json(report)
    if args.format == "markdown":
        return render_product_fix_closure_receipt_markdown(report)
    return (
        f"activation product-fix-closure-receipt {report['receipt_status']} "
        f"(new_records={report['new_record_count']})\n"
    )


def _handle_activation_product_fix_closure_snapshot(args: argparse.Namespace) -> str:
    snapshot_dir = args.output_dir if args.output_dir is not None else args.snapshot_dir
    request = ProductFixClosureSnapshotRequest(
        host=args.host,
        input_path=args.input,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        snapshot_dir=snapshot_dir,
        closure_output_dir=args.closure_output_dir,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_product_fix_closure_snapshot_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return (
            "wrote activation product-fix-closure-snapshot "
            f"with {pack['artifact_count']} artifacts to {args.output_dir}\n"
        )
    report = build_product_fix_closure_snapshot(request)
    if args.format == "json":
        return render_product_fix_closure_snapshot_json(report)
    if args.format == "markdown":
        return render_product_fix_closure_snapshot_markdown(report)
    return (
        f"activation product-fix-closure-snapshot {report['snapshot_status']} "
        f"(import_allowed={str(report['import_allowed']).lower()})\n"
    )


def _handle_activation_product_fix_closure_runbook(args: argparse.Namespace) -> str:
    request = ProductFixClosureRunbookRequest(
        host=args.host,
        input_path=args.input,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        snapshot_dir=args.snapshot_dir,
        closure_output_dir=args.closure_output_dir,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_product_fix_closure_runbook_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return (
            "wrote activation product-fix-closure-runbook "
            f"with {pack['artifact_count']} artifacts to {args.output_dir}\n"
        )
    report = build_product_fix_closure_runbook(request)
    if args.format == "json":
        return render_product_fix_closure_runbook_json(report)
    if args.format == "markdown":
        return render_product_fix_closure_runbook_markdown(report)
    return (
        f"activation product-fix-closure-runbook {report['runbook_status']} "
        f"(import_allowed={str(report['import_allowed']).lower()})\n"
    )


def _handle_activation_product_fix_implementation_plan(args: argparse.Namespace) -> str:
    request = ProductFixImplementationPlanRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_product_fix_implementation_plan_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return (
            "wrote activation product-fix-implementation-plan "
            f"with {pack['artifact_count']} artifacts to {args.output_dir}\n"
        )
    report = build_product_fix_implementation_plan(request)
    if args.format == "json":
        return render_product_fix_implementation_plan_json(report)
    if args.format == "markdown":
        return render_product_fix_implementation_plan_markdown(report)
    return (
        f"activation product-fix-implementation-plan {report['plan_status']} "
        f"(implementation_allowed={str(report['implementation_allowed']).lower()})\n"
    )


def _handle_activation_product_fix_execution_guard(args: argparse.Namespace) -> str:
    request = ProductFixExecutionGuardRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_product_fix_execution_guard_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return (
            "wrote activation product-fix-execution-guard "
            f"with {pack['artifact_count']} artifacts to {args.output_dir}\n"
        )
    report = build_product_fix_execution_guard(request)
    if args.format == "json":
        return render_product_fix_execution_guard_json(report)
    if args.format == "markdown":
        return render_product_fix_execution_guard_markdown(report)
    return (
        f"activation product-fix-execution-guard {report['guard_status']} "
        f"(execution_allowed={str(report['execution_allowed']).lower()})\n"
    )


def _handle_activation_product_fix_validation(args: argparse.Namespace) -> str:
    request = ProductFixValidationRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_product_fix_validation_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return f"wrote activation product-fix-validation with {pack['artifact_count']} artifacts to {args.output_dir}\n"
    report = build_product_fix_validation(request)
    if args.format == "json":
        return render_product_fix_validation_json(report)
    if args.format == "markdown":
        return render_product_fix_validation_markdown(report)
    return (
        f"activation product-fix-validation {report['validation_status']} "
        f"(fix_validated={str(report['fix_validated']).lower()})\n"
    )


def _handle_activation_product_fix_outcome(args: argparse.Namespace) -> str:
    request = ProductFixOutcomeRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_product_fix_outcome_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return f"wrote activation product-fix-outcome with {pack['artifact_count']} artifacts to {args.output_dir}\n"
    report = build_product_fix_outcome(request)
    if args.format == "json":
        return render_product_fix_outcome_json(report)
    if args.format == "markdown":
        return render_product_fix_outcome_markdown(report)
    return (
        f"activation product-fix-outcome {report['outcome_status']} (accepted={str(report['fix_accepted']).lower()})\n"
    )


def _handle_activation_product_fix_outcome_capture(args: argparse.Namespace) -> str:
    request = ProductFixOutcomeCaptureRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
        participant_role=args.participant_role,
        attempt_date=args.attempt_date,
    )
    if args.output_dir is not None:
        pack = build_product_fix_outcome_capture_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return (
            "wrote activation product-fix-outcome-capture "
            f"with {pack['artifact_count']} artifacts to {args.output_dir}\n"
        )
    report = build_product_fix_outcome_capture(request)
    if args.format == "json":
        return render_product_fix_outcome_capture_json(report)
    if args.format == "markdown":
        return render_product_fix_outcome_capture_markdown(report)
    return (
        f"activation product-fix-outcome-capture {report['capture_status']} "
        f"(writes_records={str(report['writes_records']).lower()})\n"
    )


def _handle_activation_product_fix_outcome_import_guard(args: argparse.Namespace) -> str:
    request = ProductFixOutcomeImportGuardRequest(
        host=args.host,
        input_path=args.input,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_product_fix_outcome_import_guard_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return (
            "wrote activation product-fix-outcome-import-guard "
            f"with {pack['artifact_count']} artifacts to {args.output_dir}\n"
        )
    report = build_product_fix_outcome_import_guard(request)
    if args.format == "json":
        return render_product_fix_outcome_import_guard_json(report)
    if args.format == "markdown":
        return render_product_fix_outcome_import_guard_markdown(report)
    return (
        f"activation product-fix-outcome-import-guard {report['guard_status']} "
        f"(import_allowed={str(report['import_allowed']).lower()})\n"
    )


def _handle_activation_product_fix_outcome_rehearsal(args: argparse.Namespace) -> str:
    request = ProductFixOutcomeRehearsalRequest(
        host=args.host,
        input_path=args.input,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_product_fix_outcome_rehearsal_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return (
            "wrote activation product-fix-outcome-rehearsal "
            f"with {pack['artifact_count']} artifacts to {args.output_dir}\n"
        )
    report = build_product_fix_outcome_rehearsal(request)
    if args.format == "json":
        return render_product_fix_outcome_rehearsal_json(report)
    if args.format == "markdown":
        return render_product_fix_outcome_rehearsal_markdown(report)
    return (
        f"activation product-fix-outcome-rehearsal {report['rehearsal_status']} "
        f"(import_allowed={str(report['import_allowed']).lower()})\n"
    )


def _handle_activation_evidence_product_loop(args: argparse.Namespace) -> str:
    request = EvidenceProductLoopRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_evidence_product_loop_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return f"wrote activation evidence-product-loop with {pack['artifact_count']} artifacts to {args.output_dir}\n"
    report = build_evidence_product_loop(request)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_evidence_product_loop_markdown(report)
    return f"activation evidence-product-loop {report['loop_status']} (sections={report['section_count']})\n"


def _handle_activation_evidence_cockpit(args: argparse.Namespace) -> str:
    request = EvidenceCockpitRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_evidence_cockpit_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return f"wrote activation evidence-cockpit with {pack['artifact_count']} artifacts to {args.output_dir}\n"
    report = build_evidence_cockpit(request)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_evidence_cockpit_markdown(report)
    return f"activation evidence-cockpit {report['cockpit_status']} (phases={report['phase_count']})\n"


def _handle_activation_acquisition_cycle(args: argparse.Namespace) -> str:
    request = AcquisitionCycleRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_acquisition_cycle_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return f"wrote activation acquisition-cycle with {pack['artifact_count']} artifacts to {args.output_dir}\n"
    report = build_acquisition_cycle(request)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_acquisition_cycle_markdown(report)
    return f"activation acquisition-cycle {report['cycle_status']} (lanes={report['lane_count']})\n"


def _handle_activation_evidence_first_cycle(args: argparse.Namespace) -> str:
    request = EvidenceFirstCycleRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        before_host_records_path=args.before_host_records,
        before_beta_records_path=args.before_beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        pack = build_evidence_first_cycle_artifacts(request, output_format=args.format)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return f"wrote activation evidence-first-cycle with {pack['artifact_count']} artifacts to {args.output_dir}\n"
    report = build_evidence_first_cycle(request)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_evidence_first_cycle_markdown(report)
    return f"activation evidence-first-cycle {report['cycle_status']} (tracks={report['track_count']})\n"


def _handle_activation_runbook(args: argparse.Namespace) -> str:
    report = build_manual_evidence_runbook(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_manual_evidence_runbook_markdown(report)
    return f"activation runbook {report['runbook_status']} (release_tag={report['release_tag']})\n"


def _handle_activation_real_proof_run(args: argparse.Namespace) -> str:
    if args.output_dir is not None:
        pack = build_real_proof_run_1_artifacts(
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
            release_tag=args.release_tag,
            output_format=args.format,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return f"wrote activation real-proof-run with {pack['artifact_count']} artifacts to {args.output_dir}\n"
    report = build_real_proof_run_1(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_real_proof_run_1_markdown(report)
    return f"activation real-proof-run {report['run_status']} (points={report['point_count']})\n"


def _handle_activation_execution_workspace(args: argparse.Namespace) -> str:
    if args.output_dir is not None:
        pack = build_proof_execution_workspace_artifacts(
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
            release_tag=args.release_tag,
            output_format=args.format,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return f"wrote activation execution-workspace with {pack['artifact_count']} artifacts to {args.output_dir}\n"
    report = build_proof_execution_workspace(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_proof_execution_workspace_markdown(report)
    return f"activation execution-workspace {report['workspace_status']} (steps={report['step_count']})\n"


def _handle_activation_proof_sprint(args: argparse.Namespace) -> str:
    if args.output_dir is not None:
        pack = build_combined_proof_sprint_artifacts(
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
            release_tag=args.release_tag,
            output_format=args.format,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for artifact in pack["artifacts"]:
            (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
        return f"wrote activation proof-sprint with {pack['artifact_count']} artifacts to {args.output_dir}\n"
    report = build_combined_proof_sprint(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_combined_proof_sprint_markdown(report)
    return f"activation proof-sprint {report['sprint_status']} (points={report['point_count']})\n"


def _handle_activation_command_center(args: argparse.Namespace) -> str:
    report = build_activation_command_center(
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_activation_command_center_markdown(report)
    return f"activation command-center {report['center_status']} (release_tag={report['release_tag']})\n"


def _run_evidence_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Record and validate real MCP host evidence.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _add_evidence_recording_parsers(subparsers)
    _add_evidence_packet_parsers(subparsers)
    _add_evidence_doctor_parsers(subparsers)

    args = parser.parse_args(argv)
    try:
        sys.stdout.write(_handle_evidence_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _add_evidence_recording_parsers(subparsers: Any) -> None:
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

    session_manifest = subparsers.add_parser(
        "session-manifest",
        help="Write a reviewer-facing evidence session manifest template.",
    )
    session_manifest.add_argument("--host", choices=get_args(HostName), required=True)
    session_manifest.add_argument("--date", required=True, help="ISO date, for example 2026-07-01.")
    session_manifest.add_argument("--reviewer", required=True)
    session_manifest.add_argument("--output-dir", type=Path, required=True)
    session_manifest.add_argument("--format", choices=["json"], default="json")

    session_folder = subparsers.add_parser(
        "session-folder",
        help="Write a no-evidence session folder for one real host evidence run.",
    )
    session_folder.add_argument("--host", choices=get_args(HostName), required=True)
    session_folder.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    session_folder.add_argument("--date", required=True, help="ISO date, for example 2026-07-02.")
    session_folder.add_argument("--reviewer", required=True)
    session_folder.add_argument("--output-dir", type=Path, required=True)
    session_folder.add_argument("--format", choices=["markdown", "json"], default="markdown")

    validate_manifest = subparsers.add_parser(
        "validate-manifest",
        help="Validate a filled evidence session manifest without writing records.",
    )
    validate_manifest.add_argument("--input", type=Path, required=True)
    validate_manifest.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    validate_manifest.add_argument("--format", choices=["text", "json"], default="text")

    import_manifest = subparsers.add_parser(
        "import-manifest",
        help="Import a validated reviewer-observed evidence session manifest into P0 records.",
    )
    import_manifest.add_argument("--input", type=Path, required=True)
    import_manifest.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    import_manifest.add_argument("--format", choices=["text", "json"], default="text")

    import_wizard = subparsers.add_parser(
        "import-wizard",
        help="Validate host manifests and beta drafts before importing real evidence records.",
    )
    import_wizard.add_argument("--host", choices=get_args(HostName), default="Codex")
    import_wizard.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    import_wizard.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    import_wizard.add_argument("--host-manifest", action="append", type=Path, default=[])
    import_wizard.add_argument("--beta-dir", type=Path, required=True)
    import_wizard.add_argument("--release-tag", default="v1.15.0-rc.1")
    import_wizard.add_argument("--import-ready", action="store_true")
    import_wizard.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    import_wizard.add_argument("--output", type=Path, default=None)


def _add_evidence_packet_parsers(subparsers: Any) -> None:
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

    _add_evidence_proof_loop_parsers(subparsers)


def _add_evidence_proof_loop_parsers(subparsers: Any) -> None:
    proof_runner = subparsers.add_parser(
        "proof-runner",
        help="Validate one evidence manifest and print the safe import sequence.",
    )
    proof_runner.add_argument("--input", type=Path, required=True)
    proof_runner.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    proof_runner.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    proof_runner.add_argument("--format", choices=["text", "json"], default="text")

    proof_status = subparsers.add_parser(
        "proof-status",
        help="Report required P0 host evidence gaps.",
    )
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


def _add_evidence_doctor_parsers(subparsers: Any) -> None:
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


def _handle_evidence_command(args: argparse.Namespace) -> str:
    handlers = {
        "record-host-ui": _handle_evidence_record_host_ui,
        "record-first-10-minutes": _handle_evidence_record_first_10_minutes,
        "run-session": _handle_evidence_run_session,
        "execution-packet": _handle_evidence_execution_packet,
        "operator-packet": _handle_evidence_operator_packet,
        "packet-bundle": _handle_evidence_packet_bundle,
        "replay-fixture-pack": _handle_evidence_replay_fixture_pack,
        "collect": _handle_evidence_collect,
        "proof-runner": _handle_evidence_proof_runner,
        "proof-status": _handle_evidence_proof_status,
        "transition-pack": _handle_evidence_transition_pack,
        "rc-unblock-preview": _handle_evidence_rc_unblock_preview,
        "transcript-template": _handle_evidence_transcript_template,
        "import-artifacts": _handle_evidence_import_artifacts,
        "validate-import": _handle_evidence_validate_import,
        "session-manifest": _handle_evidence_session_manifest,
        "session-folder": _handle_evidence_session_folder,
        "validate-manifest": _handle_evidence_validate_manifest,
        "import-manifest": _handle_evidence_import_manifest,
        "import-wizard": _handle_evidence_import_wizard,
        "import-checklist": _handle_evidence_import_checklist,
        "doctor": _handle_evidence_doctor,
        "artifact-doctor": _handle_evidence_artifact_doctor,
        "privacy-doctor": _handle_evidence_privacy_doctor,
        "unblock-plan": _handle_evidence_unblock_plan,
        "status": _handle_evidence_status,
        "close-host": _handle_evidence_close_host,
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


def _handle_evidence_packet_bundle(args: argparse.Namespace) -> str:
    bundle = build_evidence_packet_bundle_artifacts(path=args.path, output_format=args.format)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    index_path = args.output_dir / bundle["index"]["filename"]
    index_path.write_text(bundle["index"]["content"], encoding="utf-8")
    for artifact in bundle["packets"]:
        (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence packet-bundle for {bundle['host_count']} P0 hosts to {index_path}\n"


def _handle_evidence_replay_fixture_pack(args: argparse.Namespace) -> str:
    artifact = build_evidence_replay_fixture_pack_artifact(output_format=args.format)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pack_path = args.output_dir / artifact["filename"]
    pack_path.write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence replay-fixture-pack to {pack_path}\n"


def _handle_evidence_collect(args: argparse.Namespace) -> str:
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


def _handle_evidence_proof_runner(args: argparse.Namespace) -> str:
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


def _handle_evidence_proof_status(args: argparse.Namespace) -> str:
    report = build_evidence_proof_status(records_path=args.path)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return (
        f"evidence proof-status {report['status']} "
        f"(blocked_hosts={report['blocked_host_count']}/{report['host_count']})\n"
    )


def _handle_evidence_transition_pack(args: argparse.Namespace) -> str:
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


def _handle_evidence_rc_unblock_preview(args: argparse.Namespace) -> str:
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


def _handle_evidence_transcript_template(args: argparse.Namespace) -> str:
    artifact = build_operator_transcript_template_artifact(host=args.host, output_format=args.format)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    template_path = args.output_dir / artifact["filename"]
    template_path.write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence transcript-template for {args.host} to {template_path}\n"


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


def _handle_evidence_session_manifest(args: argparse.Namespace) -> str:
    artifact = build_evidence_session_manifest_artifact(
        host=args.host,
        run_date=args.date,
        reviewer=args.reviewer,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / artifact["filename"]
    manifest_path.write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence session-manifest for {args.host} to {manifest_path}\n"


def _handle_evidence_session_folder(args: argparse.Namespace) -> str:
    folder = build_evidence_session_folder_artifacts(
        host=args.host,
        path=args.path,
        run_date=args.date,
        reviewer=args.reviewer,
        output_format=args.format,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for artifact in folder["artifacts"]:
        (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence session-folder with {folder['artifact_count']} artifacts to {args.output_dir}\n"


def _handle_evidence_validate_manifest(args: argparse.Namespace) -> str:
    report = validate_evidence_session_manifest(
        manifest=load_evidence_session_manifest(args.input),
        records_path=args.path,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"evidence validate-manifest {report['validation_status']} for {report['host']}\n"


def _handle_evidence_import_manifest(args: argparse.Namespace) -> str:
    report = import_evidence_session_manifest(
        manifest=load_evidence_session_manifest(args.input),
        records_path=args.path,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"evidence import-manifest {report['import_status']} for {report['host']}\n"


def _handle_evidence_import_wizard(args: argparse.Namespace) -> str:
    report = build_evidence_import_wizard(
        EvidenceImportWizardRequest(
            host_manifest_paths=tuple(args.host_manifest),
            beta_dir_path=args.beta_dir,
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
            host=args.host,
            release_tag=args.release_tag,
            import_ready=args.import_ready,
        )
    )
    if args.format == "json":
        content = render_evidence_import_wizard_json(report)
    elif args.format == "markdown":
        content = render_evidence_import_wizard_markdown(report)
    else:
        content = (
            f"evidence import-wizard {report['wizard_status']} "
            f"(host_manifests={report['host_manifest_count']}, "
            f"beta_drafts={report['beta_draft_count']}, "
            f"writes_records={str(report['writes_records']).lower()})\n"
        )
    if args.output is None:
        return content
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    return f"wrote evidence import-wizard to {args.output}\n"


def _handle_evidence_import_checklist(args: argparse.Namespace) -> str:
    checklist = build_evidence_import_checklist(host=args.host, path=args.path)
    if args.format == "json":
        return json.dumps(checklist, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_evidence_import_checklist_markdown(checklist)
    return f"evidence import-checklist {checklist['checklist_status']} for {args.host}\n"


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


def _handle_evidence_privacy_doctor(args: argparse.Namespace) -> str:
    report = build_evidence_privacy_doctor_report(args.path)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"evidence privacy-doctor {report['privacy_status']} (issues={report['issue_count']})\n"


def _handle_evidence_unblock_plan(args: argparse.Namespace) -> str:
    plan = build_evidence_unblock_plan(args.path)
    if args.format == "json":
        return json.dumps(plan, indent=2, sort_keys=True) + "\n"
    return f"evidence unblock-plan {plan['plan_status']} (blocked_hosts={plan['blocked_host_count']})\n"


def _handle_evidence_status(args: argparse.Namespace) -> str:
    return f"{summarize_host_manual_runs(validate_host_manual_runs(args.path))}\n"


def _handle_evidence_close_host(args: argparse.Namespace) -> str:
    report = build_evidence_close_host_report(host=args.host, path=args.path)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return (
        f"evidence close-host {report['closure_status']} for {args.host} "
        f"(missing_gates={len(report['missing_gates'])})\n"
    )


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

    loop_pack = subparsers.add_parser("loop-pack", help="Write a privacy-safe beta validation loop pack.")
    loop_pack.add_argument("--path", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    loop_pack.add_argument("--output-dir", type=Path, required=True)
    loop_pack.add_argument("--participant-role", default="ML practitioner")
    loop_pack.add_argument("--format", choices=["markdown", "json"], default="markdown")

    _add_beta_response_parsers(subparsers)

    args = parser.parse_args(argv)
    try:
        sys.stdout.write(_handle_beta_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _add_beta_response_parsers(subparsers: Any) -> None:
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


def _handle_beta_command(args: argparse.Namespace) -> str:
    handlers = {
        "record-attempt": _handle_beta_record_attempt,
        "status": _handle_beta_status,
        "triage": _handle_beta_triage,
        "report": _handle_beta_report,
        "campaign-plan": _handle_beta_campaign_plan,
        "trial-pack": _handle_beta_trial_pack,
        "intake-wizard": _handle_beta_intake_wizard,
        "loop-pack": _handle_beta_loop_pack,
        "response-validate": _handle_beta_response_validate,
        "response-import": _handle_beta_response_import,
        "response-import-dir": _handle_beta_response_import_dir,
        "response-template": _handle_beta_response_template,
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


def _handle_beta_loop_pack(args: argparse.Namespace) -> str:
    pack = build_beta_loop_pack_artifacts(
        validate_beta_validation_records(args.path),
        participant_role=args.participant_role,
        output_format=args.format,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for artifact in pack["artifacts"]:
        (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
    return f"wrote beta loop-pack with {pack['artifact_count']} artifacts to {args.output_dir}\n"


def _handle_beta_response_validate(args: argparse.Namespace) -> str:
    report = validate_beta_response_draft(load_beta_response_draft(args.input))
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"beta response-validate {report['validation_status']} for {report['record']['workflow_id']}\n"


def _handle_beta_response_import(args: argparse.Namespace) -> str:
    draft = load_beta_response_draft(args.input)
    import_beta_response_draft(path=args.path, draft=draft)
    return f"imported beta response {draft.workflow_id} into {args.path}\n"


def _handle_beta_response_import_dir(args: argparse.Namespace) -> str:
    report = import_beta_response_draft_dir(input_dir=args.input_dir, path=args.path)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"imported {report['imported_count']} beta responses into {args.path}\n"


def _handle_beta_response_template(args: argparse.Namespace) -> str:
    artifacts = build_beta_response_template_artifacts(participant_role=args.participant_role)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for artifact in artifacts:
        (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
    return f"wrote {len(artifacts)} beta response-template files to {args.output_dir}\n"


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

    go_check = subparsers.add_parser("go-check", help="Build a final report-only RC go/no-go check.")
    go_check.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    go_check.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    go_check.add_argument("--release-tag", default="v1.15.0-rc.1")
    go_check.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    release_owner_packet = subparsers.add_parser(
        "release-owner-packet",
        help="Build a release-owner handoff packet without publish actions.",
    )
    release_owner_packet.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    release_owner_packet.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    release_owner_packet.add_argument("--release-tag", default="v1.15.0-rc.1")
    release_owner_packet.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    review_pack = subparsers.add_parser("review-pack", help="Write release owner review artifacts.")
    review_pack.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    review_pack.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    review_pack.add_argument("--before-host-records", type=Path, default=None)
    review_pack.add_argument("--before-beta-records", type=Path, default=None)
    review_pack.add_argument("--output-dir", type=Path, required=True)
    review_pack.add_argument("--release-tag", default="v1.15.0-rc.1")
    review_pack.add_argument("--format", choices=["markdown", "json"], default="markdown")

    args = parser.parse_args(argv)
    try:
        sys.stdout.write(_handle_rc_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _handle_rc_command(args: argparse.Namespace) -> str:
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

    args = parser.parse_args(argv)
    try:
        sys.stdout.write(_handle_trust_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _handle_trust_command(args: argparse.Namespace) -> str:
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


def _add_host_record_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    parser.add_argument("--host", choices=get_args(HostName), required=True)
    parser.add_argument("--status", choices=get_args(HostStatus), required=True)
    parser.add_argument("--date", required=True, help="ISO date, for example 2026-06-28.")
    parser.add_argument("--evidence", required=True)


if __name__ == "__main__":
    main()
