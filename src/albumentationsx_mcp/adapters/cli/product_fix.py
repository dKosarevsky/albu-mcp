"""Product-fix activation command registration and handlers."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any, get_args

from albumentationsx_mcp.evidence import HostName
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

PRODUCT_FIX_COMMANDS = (
    "product-fix-closure-import",
    "product-fix-closure-pack",
    "product-fix-closure-pipeline",
    "product-fix-closure-receipt",
    "product-fix-closure-snapshot",
    "product-fix-closure-runbook",
    "product-fix-execution-guard",
    "product-fix-implementation-plan",
    "product-fix-outcome-capture",
    "product-fix-outcome-import-guard",
    "product-fix-outcome-rehearsal",
    "product-fix-outcome",
    "product-fix-validation",
)

CommandHandler = Callable[[argparse.Namespace], str]


def register_product_fix_parsers(subparsers: Any) -> None:
    """Register product-fix commands in their compatibility order."""
    _add_closure_import_parser(subparsers)
    _add_closure_pack_parser(subparsers)
    _add_closure_pipeline_parser(subparsers)
    _add_closure_receipt_parser(subparsers)
    _add_closure_snapshot_parser(subparsers)
    _add_closure_runbook_parser(subparsers)
    _add_execution_guard_parser(subparsers)
    _add_implementation_plan_parser(subparsers)
    _add_outcome_capture_parser(subparsers)
    _add_outcome_import_guard_parser(subparsers)
    _add_outcome_rehearsal_parser(subparsers)
    _add_outcome_parser(subparsers)
    _add_validation_parser(subparsers)


def _add_closure_import_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-closure-import",
        help="Guard and execute one post-fix beta response import only after explicit confirmation.",
    )
    _add_host_records_arguments(parser)
    parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path, default=Path("docs/product-fix-closure-snapshot"))
    parser.add_argument("--closure-output-dir", type=Path, default=Path("docs/product-fix-closure-pack"))
    parser.add_argument("--release-tag", default="v1.15.0-rc.1")
    parser.add_argument("--confirm-import-ready", action="store_true")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_closure_pack_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-closure-pack",
        help="Build a no-write post-import closure pack for one product fix.",
    )
    _add_host_records_arguments(parser)
    parser.add_argument("--before-beta-records", type=Path, required=True)
    parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    _add_release_output_arguments(parser)


def _add_closure_pipeline_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-closure-pipeline",
        help="Build a no-write pipeline status for closing one product fix.",
    )
    _add_host_records_arguments(parser)
    parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path, default=Path("docs/product-fix-closure-snapshot"))
    parser.add_argument("--closure-output-dir", type=Path, default=Path("docs/product-fix-closure-pack"))
    parser.add_argument("--receipt-output-dir", type=Path, default=Path("docs/product-fix-closure-receipt"))
    parser.add_argument("--final-outcome-output-dir", type=Path, default=Path("docs/product-fix-outcome"))
    _add_release_output_arguments(parser)


def _add_closure_receipt_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-closure-receipt",
        help="Build a no-write receipt for the guarded import-to-closure handoff.",
    )
    _add_host_records_arguments(parser)
    parser.add_argument("--before-beta-records", type=Path, required=True)
    parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    parser.add_argument("--snapshot-path", type=Path, default=None)
    parser.add_argument("--closure-output-dir", type=Path, default=Path("docs/product-fix-closure-pack"))
    _add_release_output_arguments(parser)


def _add_closure_snapshot_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-closure-snapshot",
        help="Write a pre-import beta records snapshot and print the guarded import-to-closure sequence.",
    )
    _add_host_records_arguments(parser)
    parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path, default=Path("docs/product-fix-closure-snapshot"))
    parser.add_argument("--closure-output-dir", type=Path, default=Path("docs/product-fix-closure-pack"))
    _add_release_output_arguments(parser)


def _add_closure_runbook_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-closure-runbook",
        help="Build a no-write operator runbook from post-fix capture through closure confirmation.",
    )
    _add_host_records_arguments(parser)
    parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path, default=Path("docs/product-fix-closure-snapshot"))
    parser.add_argument("--closure-output-dir", type=Path, default=Path("docs/product-fix-closure-pack"))
    _add_release_output_arguments(parser)


def _add_execution_guard_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-execution-guard",
        help="Build a no-write guarded branch handoff for the selected product fix.",
    )
    _add_standard_product_fix_arguments(parser)


def _add_implementation_plan_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-implementation-plan",
        help="Build a no-write TDD plan for the selected product fix.",
    )
    _add_standard_product_fix_arguments(parser)


def _add_outcome_capture_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-outcome-capture",
        help="Build a no-write post-fix beta outcome capture pack.",
    )
    _add_host_records_arguments(parser)
    parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    parser.add_argument("--release-tag", default="v1.15.0-rc.1")
    parser.add_argument("--participant-role", default="ML practitioner")
    parser.add_argument("--attempt-date", default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_outcome_import_guard_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-outcome-import-guard",
        help="Validate one post-fix beta response draft before importing it.",
    )
    _add_input_product_fix_arguments(parser)


def _add_outcome_rehearsal_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-outcome-rehearsal",
        help="Rehearse post-fix outcome capture, draft guard, and projected outcome without importing records.",
    )
    _add_input_product_fix_arguments(parser)


def _add_outcome_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-outcome",
        help="Decide whether a validated product fix is accepted by real beta evidence.",
    )
    _add_standard_product_fix_arguments(parser)


def _add_validation_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "product-fix-validation",
        help="Validate the selected product fix against its behavior contract.",
    )
    _add_standard_product_fix_arguments(parser)


def _add_host_records_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", choices=get_args(HostName), required=True)
    parser.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))


def _add_release_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--release-tag", default="v1.15.0-rc.1")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_standard_product_fix_arguments(parser: argparse.ArgumentParser) -> None:
    _add_host_records_arguments(parser)
    parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    _add_release_output_arguments(parser)


def _add_input_product_fix_arguments(parser: argparse.ArgumentParser) -> None:
    _add_host_records_arguments(parser)
    parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    parser.add_argument("--input", type=Path, required=True)
    _add_release_output_arguments(parser)


def _handle_closure_import(args: argparse.Namespace) -> str:
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


def _handle_closure_pack(args: argparse.Namespace) -> str:
    request = ProductFixClosurePackRequest(
        host=args.host,
        host_records_path=args.host_records,
        before_beta_records_path=args.before_beta_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "product-fix-closure-pack",
            build_product_fix_closure_pack_artifacts(request, output_format=args.format),
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


def _handle_closure_pipeline(args: argparse.Namespace) -> str:
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
        return _write_artifacts(
            args,
            "product-fix-closure-pipeline",
            build_product_fix_closure_pipeline_artifacts(request, output_format=args.format),
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


def _handle_closure_receipt(args: argparse.Namespace) -> str:
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
        return _write_artifacts(
            args,
            "product-fix-closure-receipt",
            build_product_fix_closure_receipt_artifacts(request, output_format=args.format),
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


def _handle_closure_snapshot(args: argparse.Namespace) -> str:
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
        return _write_artifacts(
            args,
            "product-fix-closure-snapshot",
            build_product_fix_closure_snapshot_artifacts(request, output_format=args.format),
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


def _handle_closure_runbook(args: argparse.Namespace) -> str:
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
        return _write_artifacts(
            args,
            "product-fix-closure-runbook",
            build_product_fix_closure_runbook_artifacts(request, output_format=args.format),
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


def _handle_implementation_plan(args: argparse.Namespace) -> str:
    request = ProductFixImplementationPlanRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "product-fix-implementation-plan",
            build_product_fix_implementation_plan_artifacts(request, output_format=args.format),
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


def _handle_execution_guard(args: argparse.Namespace) -> str:
    request = ProductFixExecutionGuardRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "product-fix-execution-guard",
            build_product_fix_execution_guard_artifacts(request, output_format=args.format),
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


def _handle_validation(args: argparse.Namespace) -> str:
    request = ProductFixValidationRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "product-fix-validation",
            build_product_fix_validation_artifacts(request, output_format=args.format),
        )
    report = build_product_fix_validation(request)
    if args.format == "json":
        return render_product_fix_validation_json(report)
    if args.format == "markdown":
        return render_product_fix_validation_markdown(report)
    return (
        f"activation product-fix-validation {report['validation_status']} "
        f"(fix_validated={str(report['fix_validated']).lower()})\n"
    )


def _handle_outcome(args: argparse.Namespace) -> str:
    request = ProductFixOutcomeRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "product-fix-outcome",
            build_product_fix_outcome_artifacts(request, output_format=args.format),
        )
    report = build_product_fix_outcome(request)
    if args.format == "json":
        return render_product_fix_outcome_json(report)
    if args.format == "markdown":
        return render_product_fix_outcome_markdown(report)
    return (
        f"activation product-fix-outcome {report['outcome_status']} (accepted={str(report['fix_accepted']).lower()})\n"
    )


def _handle_outcome_capture(args: argparse.Namespace) -> str:
    request = ProductFixOutcomeCaptureRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
        participant_role=args.participant_role,
        attempt_date=args.attempt_date,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "product-fix-outcome-capture",
            build_product_fix_outcome_capture_artifacts(request, output_format=args.format),
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


def _handle_outcome_import_guard(args: argparse.Namespace) -> str:
    request = ProductFixOutcomeImportGuardRequest(
        host=args.host,
        input_path=args.input,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "product-fix-outcome-import-guard",
            build_product_fix_outcome_import_guard_artifacts(request, output_format=args.format),
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


def _handle_outcome_rehearsal(args: argparse.Namespace) -> str:
    request = ProductFixOutcomeRehearsalRequest(
        host=args.host,
        input_path=args.input,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "product-fix-outcome-rehearsal",
            build_product_fix_outcome_rehearsal_artifacts(request, output_format=args.format),
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


def _write_artifacts(args: argparse.Namespace, command: str, pack: dict[str, Any]) -> str:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for artifact in pack["artifacts"]:
        (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
    return f"wrote activation {command} with {pack['artifact_count']} artifacts to {args.output_dir}\n"


PRODUCT_FIX_HANDLERS: dict[str, CommandHandler] = {
    "product-fix-closure-import": _handle_closure_import,
    "product-fix-closure-pack": _handle_closure_pack,
    "product-fix-closure-pipeline": _handle_closure_pipeline,
    "product-fix-closure-receipt": _handle_closure_receipt,
    "product-fix-closure-snapshot": _handle_closure_snapshot,
    "product-fix-closure-runbook": _handle_closure_runbook,
    "product-fix-execution-guard": _handle_execution_guard,
    "product-fix-implementation-plan": _handle_implementation_plan,
    "product-fix-outcome-capture": _handle_outcome_capture,
    "product-fix-outcome-import-guard": _handle_outcome_import_guard,
    "product-fix-outcome-rehearsal": _handle_outcome_rehearsal,
    "product-fix-outcome": _handle_outcome,
    "product-fix-validation": _handle_validation,
}
