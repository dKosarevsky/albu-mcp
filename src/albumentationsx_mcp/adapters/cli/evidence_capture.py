"""Evidence capture, import, execution-pack, and preflight CLI adapter."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, get_args

from albumentationsx_mcp.evidence import (
    EvidenceArtifactImport,
    FirstTenMinutesReplayEvidence,
    HostName,
    HostStatus,
    build_evidence_session_folder_artifacts,
    build_evidence_session_manifest_artifact,
    import_evidence_artifacts,
    import_evidence_session_manifest,
    load_evidence_session_manifest,
    record_first_10_minutes_replay,
    record_host_manual_run,
    validate_evidence_artifact_import,
    validate_evidence_session_manifest,
)
from albumentationsx_mcp.evidence_execution_pack import (
    EvidenceExecutionPackAuditRequest,
    EvidenceExecutionPackProgressRequest,
    EvidenceExecutionPackRequest,
    build_evidence_execution_pack_artifacts,
    build_evidence_execution_pack_audit,
    build_evidence_execution_pack_progress,
    render_evidence_execution_pack_audit_json,
    render_evidence_execution_pack_audit_markdown,
    render_evidence_execution_pack_progress_json,
    render_evidence_execution_pack_progress_markdown,
)
from albumentationsx_mcp.evidence_execution_pack_status import (
    EvidenceExecutionPackStatusRequest,
    build_evidence_execution_pack_status,
    render_evidence_execution_pack_status_json,
    render_evidence_execution_pack_status_markdown,
)
from albumentationsx_mcp.evidence_import_wizard import (
    EvidenceImportWizardRequest,
    build_evidence_import_wizard,
    render_evidence_import_wizard_json,
    render_evidence_import_wizard_markdown,
)
from albumentationsx_mcp.evidence_preflight import (
    DEFAULT_TEMPLATE_BETA_DIR,
    DEFAULT_TEMPLATE_HOST_MANIFEST_PATHS,
    EvidencePreflightRequest,
    build_evidence_preflight,
    render_evidence_preflight_json,
    render_evidence_preflight_markdown,
)
from albumentationsx_mcp.evidence_template_guard import (
    EvidenceTemplateGuardRequest,
    build_evidence_template_guard,
    render_evidence_template_guard_json,
    render_evidence_template_guard_markdown,
    strict_template_guard_error,
)

CAPTURE_COMMANDS = (
    "record-host-ui",
    "record-first-10-minutes",
    "import-artifacts",
    "validate-import",
    "session-manifest",
    "session-folder",
    "execution-pack",
    "execution-pack-audit",
    "execution-pack-progress",
    "execution-pack-status",
    "validate-manifest",
    "import-manifest",
    "import-wizard",
    "template-guard",
    "preflight",
)

CommandHandler = Callable[[argparse.Namespace], str]


def register_capture_parsers(subparsers: Any) -> None:
    """Register capture and import commands in compatibility order."""
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

    _add_execution_pack_parsers(subparsers)

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

    _add_template_guard_parser(subparsers)
    _add_preflight_parser(subparsers)


def _add_execution_pack_parsers(subparsers: Any) -> None:
    execution_pack = subparsers.add_parser(
        "execution-pack",
        help="Write one no-write operator pack for real host and beta evidence capture.",
    )
    execution_pack.add_argument("--host", action="append", choices=get_args(HostName), default=[])
    execution_pack.add_argument("--date", required=True, help="ISO date, for example 2026-07-09.")
    execution_pack.add_argument("--reviewer", required=True)
    execution_pack.add_argument("--output-dir", type=Path, required=True)
    execution_pack.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    execution_pack.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    execution_pack.add_argument("--format", choices=["markdown"], default="markdown")

    for command, help_text in (
        ("execution-pack-audit", "Audit one generated execution pack without writing records."),
        ("execution-pack-progress", "Report fill progress for one generated execution pack without writing records."),
        (
            "execution-pack-status",
            "Summarize execution-pack audit, progress, and import readiness without writing records.",
        ),
    ):
        parser = subparsers.add_parser(command, help=help_text)
        parser.add_argument("--input-dir", type=Path, required=True)
        parser.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
        parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
        parser.add_argument("--format", choices=["json", "markdown"], default="json")
        parser.add_argument("--output", type=Path, default=None)


def _add_template_guard_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "template-guard",
        help="Check that committed evidence templates are still blocked from import.",
    )
    parser.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    parser.add_argument("--host-manifest", action="append", type=Path, default=[])
    parser.add_argument("--beta-dir", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_preflight_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "preflight",
        help="Build one no-write evidence preflight across templates, import readiness, and release blockers.",
    )
    parser.add_argument("--host", choices=get_args(HostName), default="Codex")
    parser.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    parser.add_argument("--host-manifest", action="append", type=Path, default=[])
    parser.add_argument("--beta-dir", type=Path, default=DEFAULT_TEMPLATE_BETA_DIR)
    parser.add_argument("--template-host-manifest", action="append", type=Path, default=[])
    parser.add_argument("--template-beta-dir", type=Path, default=DEFAULT_TEMPLATE_BETA_DIR)
    parser.add_argument("--release-tag", default="v1.15.0-rc.1")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--output", type=Path, default=None)


def _add_host_record_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    parser.add_argument("--host", choices=get_args(HostName), required=True)
    parser.add_argument("--status", choices=get_args(HostStatus), required=True)
    parser.add_argument("--date", required=True, help="ISO date, for example 2026-06-28.")
    parser.add_argument("--evidence", required=True)


def _handle_record_host_ui(args: argparse.Namespace) -> str:
    record_host_manual_run(
        path=args.path,
        host=args.host,
        status=args.status,
        run_date=args.date,
        evidence=args.evidence,
    )
    return f"recorded {args.host} {args.status} on {args.date} in {args.path}\n"


def _handle_record_first_ten_minutes(args: argparse.Namespace) -> str:
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


def _handle_import_artifacts(args: argparse.Namespace) -> str:
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


def _handle_validate_import(args: argparse.Namespace) -> str:
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


def _handle_session_manifest(args: argparse.Namespace) -> str:
    artifact = build_evidence_session_manifest_artifact(
        host=args.host,
        run_date=args.date,
        reviewer=args.reviewer,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / artifact["filename"]
    manifest_path.write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence session-manifest for {args.host} to {manifest_path}\n"


def _handle_session_folder(args: argparse.Namespace) -> str:
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


def _handle_execution_pack(args: argparse.Namespace) -> str:
    pack = build_evidence_execution_pack_artifacts(
        EvidenceExecutionPackRequest(
            run_date=args.date,
            reviewer=args.reviewer,
            output_dir=args.output_dir,
            hosts=tuple(args.host),
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
            output_format=args.format,
        )
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for artifact in pack["artifacts"]:
        artifact_path = args.output_dir / artifact["filename"]
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(artifact["content"], encoding="utf-8")
    return f"wrote evidence execution-pack with {pack['artifact_count']} artifacts to {args.output_dir}\n"


def _handle_execution_pack_audit(args: argparse.Namespace) -> str:
    report = build_evidence_execution_pack_audit(
        EvidenceExecutionPackAuditRequest(
            input_dir=args.input_dir,
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
        )
    )
    content = (
        render_evidence_execution_pack_audit_markdown(report)
        if args.format == "markdown"
        else render_evidence_execution_pack_audit_json(report)
    )
    return _write_optional_output(args, content, "execution-pack-audit")


def _handle_execution_pack_progress(args: argparse.Namespace) -> str:
    report = build_evidence_execution_pack_progress(
        EvidenceExecutionPackProgressRequest(
            input_dir=args.input_dir,
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
        )
    )
    content = (
        render_evidence_execution_pack_progress_markdown(report)
        if args.format == "markdown"
        else render_evidence_execution_pack_progress_json(report)
    )
    return _write_optional_output(args, content, "execution-pack-progress")


def _handle_execution_pack_status(args: argparse.Namespace) -> str:
    report = build_evidence_execution_pack_status(
        EvidenceExecutionPackStatusRequest(
            input_dir=args.input_dir,
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
        )
    )
    content = (
        render_evidence_execution_pack_status_markdown(report)
        if args.format == "markdown"
        else render_evidence_execution_pack_status_json(report)
    )
    return _write_optional_output(args, content, "execution-pack-status")


def _handle_validate_manifest(args: argparse.Namespace) -> str:
    report = validate_evidence_session_manifest(
        manifest=load_evidence_session_manifest(args.input),
        records_path=args.path,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"evidence validate-manifest {report['validation_status']} for {report['host']}\n"


def _handle_import_manifest(args: argparse.Namespace) -> str:
    report = import_evidence_session_manifest(
        manifest=load_evidence_session_manifest(args.input),
        records_path=args.path,
    )
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    return f"evidence import-manifest {report['import_status']} for {report['host']}\n"


def _handle_import_wizard(args: argparse.Namespace) -> str:
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
    return _write_optional_output(args, content, "import-wizard")


def _handle_template_guard(args: argparse.Namespace) -> str:
    report = build_evidence_template_guard(
        EvidenceTemplateGuardRequest(
            host_manifest_paths=tuple(args.host_manifest),
            beta_dir_path=args.beta_dir,
            host_records_path=args.host_records,
        )
    )
    if args.strict and report["guard_status"] != "passed":
        raise strict_template_guard_error(report)
    if args.format == "json":
        return render_evidence_template_guard_json(report)
    if args.format == "markdown":
        return render_evidence_template_guard_markdown(report)
    return (
        f"evidence template-guard {report['guard_status']} "
        f"(violations={report['violation_count']}, writes_records=false)\n"
    )


def _handle_preflight(args: argparse.Namespace) -> str:
    report = build_evidence_preflight(
        EvidencePreflightRequest(
            host_manifest_paths=tuple(args.host_manifest) or DEFAULT_TEMPLATE_HOST_MANIFEST_PATHS,
            beta_dir_path=args.beta_dir,
            template_host_manifest_paths=tuple(args.template_host_manifest) or DEFAULT_TEMPLATE_HOST_MANIFEST_PATHS,
            template_beta_dir_path=args.template_beta_dir,
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
            host=args.host,
            release_tag=args.release_tag,
        )
    )
    if args.format == "json":
        content = render_evidence_preflight_json(report)
    elif args.format == "markdown":
        content = render_evidence_preflight_markdown(report)
    else:
        content = (
            f"evidence preflight {report['preflight_status']} "
            f"(template_guard={report['template_guard_status']}, "
            f"import_wizard={report['import_wizard_status']}, writes_records=false)\n"
        )
    return _write_optional_output(args, content, "preflight")


def _write_optional_output(args: argparse.Namespace, content: str, command: str) -> str:
    if args.output is None:
        return content
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    return f"wrote evidence {command} to {args.output}\n"


CAPTURE_HANDLERS: dict[str, CommandHandler] = {
    "record-host-ui": _handle_record_host_ui,
    "record-first-10-minutes": _handle_record_first_ten_minutes,
    "import-artifacts": _handle_import_artifacts,
    "validate-import": _handle_validate_import,
    "session-manifest": _handle_session_manifest,
    "session-folder": _handle_session_folder,
    "execution-pack": _handle_execution_pack,
    "execution-pack-audit": _handle_execution_pack_audit,
    "execution-pack-progress": _handle_execution_pack_progress,
    "execution-pack-status": _handle_execution_pack_status,
    "validate-manifest": _handle_validate_manifest,
    "import-manifest": _handle_import_manifest,
    "import-wizard": _handle_import_wizard,
    "template-guard": _handle_template_guard,
    "preflight": _handle_preflight,
}
