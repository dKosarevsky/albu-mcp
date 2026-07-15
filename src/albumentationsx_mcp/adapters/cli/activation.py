"""Activation cycle, proof, and product-fix CLI composition."""

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
from albumentationsx_mcp.adapters.cli.contracts import CliGroupSurface
from albumentationsx_mcp.adapters.cli.product_fix import (
    PRODUCT_FIX_COMMANDS,
    PRODUCT_FIX_HANDLERS,
    register_product_fix_parsers,
)
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.evidence_cockpit import (
    EvidenceCockpitRequest,
    build_evidence_cockpit,
    build_evidence_cockpit_artifacts,
    render_evidence_cockpit_markdown,
)
from albumentationsx_mcp.evidence_product_loop import (
    EvidenceProductLoopRequest,
    build_evidence_product_loop,
    build_evidence_product_loop_artifacts,
    render_evidence_product_loop_markdown,
)
from albumentationsx_mcp.first_product_fix_selector import (
    FirstProductFixSelectorRequest,
    build_first_product_fix_selector,
    build_first_product_fix_selector_artifacts,
    render_first_product_fix_selector_json,
    render_first_product_fix_selector_markdown,
)
from albumentationsx_mcp.product_cycle import (
    EvidenceFirstCycleRequest,
    build_evidence_first_cycle,
    build_evidence_first_cycle_artifacts,
    render_evidence_first_cycle_markdown,
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
from albumentationsx_mcp.real_adoption_cycle import (
    RealAdoptionCycleRequest,
    build_real_adoption_cycle,
    build_real_adoption_cycle_artifacts,
    render_real_adoption_cycle_markdown,
)

_CYCLE_COMMANDS = (
    "command-center",
    "runbook",
    "proof-sprint",
    "execution-workspace",
    "real-proof-run",
    "evidence-first-cycle",
    "acquisition-cycle",
    "evidence-cockpit",
    "evidence-product-loop",
    "first-product-fix",
)
SURFACE = CliGroupSurface(
    group="activation",
    commands=_CYCLE_COMMANDS + PRODUCT_FIX_COMMANDS + ("real-adoption-cycle",),
)


def build_activation_parser() -> argparse.ArgumentParser:
    """Build the complete activation command parser."""
    parser = argparse.ArgumentParser(description="Build report-only activation command center packets.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_command_center_parser(subparsers)
    _add_runbook_parser(subparsers)
    _add_proof_flow_parsers(subparsers)
    _add_acquisition_cycle_parser(subparsers)
    _add_evidence_cockpit_parser(subparsers)
    _add_evidence_product_loop_parser(subparsers)
    _add_first_product_fix_parser(subparsers)
    register_product_fix_parsers(subparsers)
    _add_real_adoption_cycle_parser(subparsers)
    return parser


def run_activation(argv: list[str]) -> None:
    """Run an activation command."""
    args = build_activation_parser().parse_args(argv)
    try:
        sys.stdout.write(handle_activation_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def _add_command_center_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser("command-center", help="Build the release activation command center.")
    _add_records_arguments(parser)
    parser.add_argument("--release-tag", default="v1.15.0-rc.1")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_runbook_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser("runbook", help="Build a manual real-evidence intake runbook.")
    _add_records_arguments(parser)
    parser.add_argument("--release-tag", default="v1.15.0-rc.1")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_proof_flow_parsers(subparsers: Any) -> None:
    proof_sprint = subparsers.add_parser("proof-sprint", help="Build a combined external proof sprint.")
    _add_report_arguments(proof_sprint)

    execution_workspace = subparsers.add_parser(
        "execution-workspace",
        help="Build a no-write proof execution workspace.",
    )
    _add_report_arguments(execution_workspace)

    real_proof_run = subparsers.add_parser("real-proof-run", help="Build a no-write real proof run handoff.")
    _add_report_arguments(real_proof_run)

    evidence_first_cycle = subparsers.add_parser(
        "evidence-first-cycle",
        help="Build a no-write evidence-first product cycle.",
    )
    evidence_first_cycle.add_argument("--host", choices=get_args(HostName), required=True)
    _add_records_arguments(evidence_first_cycle)
    evidence_first_cycle.add_argument("--before-host-records", type=Path, default=None)
    evidence_first_cycle.add_argument("--before-beta-records", type=Path, default=None)
    _add_release_output_arguments(evidence_first_cycle)


def _add_acquisition_cycle_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "acquisition-cycle",
        help="Build a no-write real evidence and beta acquisition cycle.",
    )
    _add_host_report_arguments(parser)


def _add_evidence_cockpit_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "evidence-cockpit",
        help="Build a no-write cockpit for one real host evidence run.",
    )
    _add_host_report_arguments(parser)


def _add_evidence_product_loop_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "evidence-product-loop",
        help="Build a no-write evidence-to-product friction loop.",
    )
    _add_host_report_arguments(parser)


def _add_first_product_fix_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "first-product-fix",
        help="Select the first product fix after real adoption gates pass.",
    )
    _add_host_report_arguments(parser)


def _add_real_adoption_cycle_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "real-adoption-cycle",
        help="Build a no-write real adoption cycle.",
    )
    _add_host_report_arguments(parser)


def _add_records_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    parser.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))


def _add_release_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--release-tag", default="v1.15.0-rc.1")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")


def _add_report_arguments(parser: argparse.ArgumentParser) -> None:
    _add_records_arguments(parser)
    _add_release_output_arguments(parser)


def _add_host_report_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", choices=get_args(HostName), required=True)
    _add_report_arguments(parser)


def handle_activation_command(args: argparse.Namespace) -> str:
    """Execute one parsed activation command."""
    handlers = {
        "acquisition-cycle": _handle_acquisition_cycle,
        "command-center": _handle_command_center,
        "evidence-cockpit": _handle_evidence_cockpit,
        "evidence-first-cycle": _handle_evidence_first_cycle,
        "evidence-product-loop": _handle_evidence_product_loop,
        "execution-workspace": _handle_execution_workspace,
        "first-product-fix": _handle_first_product_fix,
        **PRODUCT_FIX_HANDLERS,
        "proof-sprint": _handle_proof_sprint,
        "real-adoption-cycle": _handle_real_adoption_cycle,
        "real-proof-run": _handle_real_proof_run,
        "runbook": _handle_runbook,
    }
    return handlers[args.command](args)


def _handle_real_adoption_cycle(args: argparse.Namespace) -> str:
    request = RealAdoptionCycleRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "real-adoption-cycle",
            build_real_adoption_cycle_artifacts(request, output_format=args.format),
        )
    report = build_real_adoption_cycle(request)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_real_adoption_cycle_markdown(report)
    return f"activation real-adoption-cycle {report['cycle_status']} (lanes={report['lane_count']})\n"


def _handle_first_product_fix(args: argparse.Namespace) -> str:
    request = FirstProductFixSelectorRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "first-product-fix",
            build_first_product_fix_selector_artifacts(request, output_format=args.format),
        )
    report = build_first_product_fix_selector(request)
    if args.format == "json":
        return render_first_product_fix_selector_json(report)
    if args.format == "markdown":
        return render_first_product_fix_selector_markdown(report)
    return (
        f"activation first-product-fix {report['selector_status']} "
        f"(implementation_allowed={str(report['implementation_allowed']).lower()})\n"
    )


def _handle_evidence_product_loop(args: argparse.Namespace) -> str:
    request = EvidenceProductLoopRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "evidence-product-loop",
            build_evidence_product_loop_artifacts(request, output_format=args.format),
        )
    report = build_evidence_product_loop(request)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_evidence_product_loop_markdown(report)
    return f"activation evidence-product-loop {report['loop_status']} (sections={report['section_count']})\n"


def _handle_evidence_cockpit(args: argparse.Namespace) -> str:
    request = EvidenceCockpitRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "evidence-cockpit",
            build_evidence_cockpit_artifacts(request, output_format=args.format),
        )
    report = build_evidence_cockpit(request)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_evidence_cockpit_markdown(report)
    return f"activation evidence-cockpit {report['cockpit_status']} (phases={report['phase_count']})\n"


def _handle_acquisition_cycle(args: argparse.Namespace) -> str:
    request = AcquisitionCycleRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "acquisition-cycle",
            build_acquisition_cycle_artifacts(request, output_format=args.format),
        )
    report = build_acquisition_cycle(request)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_acquisition_cycle_markdown(report)
    return f"activation acquisition-cycle {report['cycle_status']} (lanes={report['lane_count']})\n"


def _handle_evidence_first_cycle(args: argparse.Namespace) -> str:
    request = EvidenceFirstCycleRequest(
        host=args.host,
        host_records_path=args.host_records,
        beta_records_path=args.beta_records,
        before_host_records_path=args.before_host_records,
        before_beta_records_path=args.before_beta_records,
        release_tag=args.release_tag,
    )
    if args.output_dir is not None:
        return _write_artifacts(
            args,
            "evidence-first-cycle",
            build_evidence_first_cycle_artifacts(request, output_format=args.format),
        )
    report = build_evidence_first_cycle(request)
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.format == "markdown":
        return render_evidence_first_cycle_markdown(report)
    return f"activation evidence-first-cycle {report['cycle_status']} (tracks={report['track_count']})\n"


def _handle_runbook(args: argparse.Namespace) -> str:
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


def _handle_real_proof_run(args: argparse.Namespace) -> str:
    if args.output_dir is not None:
        pack = build_real_proof_run_1_artifacts(
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
            release_tag=args.release_tag,
            output_format=args.format,
        )
        return _write_artifacts(args, "real-proof-run", pack)
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


def _handle_execution_workspace(args: argparse.Namespace) -> str:
    if args.output_dir is not None:
        pack = build_proof_execution_workspace_artifacts(
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
            release_tag=args.release_tag,
            output_format=args.format,
        )
        return _write_artifacts(args, "execution-workspace", pack)
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


def _handle_proof_sprint(args: argparse.Namespace) -> str:
    if args.output_dir is not None:
        pack = build_combined_proof_sprint_artifacts(
            host_records_path=args.host_records,
            beta_records_path=args.beta_records,
            release_tag=args.release_tag,
            output_format=args.format,
        )
        return _write_artifacts(args, "proof-sprint", pack)
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


def _handle_command_center(args: argparse.Namespace) -> str:
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


def _write_artifacts(args: argparse.Namespace, command: str, pack: dict[str, Any]) -> str:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for artifact in pack["artifacts"]:
        (args.output_dir / artifact["filename"]).write_text(artifact["content"], encoding="utf-8")
    return f"wrote activation {command} with {pack['artifact_count']} artifacts to {args.output_dir}\n"
