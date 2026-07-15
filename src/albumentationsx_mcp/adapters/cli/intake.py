"""Manual evidence and beta intake bundle CLI adapter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from albumentationsx_mcp.adapters.cli.contracts import CliGroupSurface
from albumentationsx_mcp.intake import build_intake_bundle_artifacts

SURFACE = CliGroupSurface(group="intake", commands=("bundle",))


def build_intake_parser() -> argparse.ArgumentParser:
    """Build the release-safe intake command parser."""
    parser = argparse.ArgumentParser(description="Write release-safe manual intake bundles.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bundle = subparsers.add_parser("bundle", help="Write one manual evidence and beta intake bundle.")
    bundle.add_argument("--host-records", type=Path, default=Path("docs/HOST_MANUAL_RUNS.json"))
    bundle.add_argument("--beta-records", type=Path, default=Path("docs/BETA_VALIDATION_RECORDS.json"))
    bundle.add_argument("--output-dir", type=Path, required=True)
    bundle.add_argument("--release-tag", default="v1.15.0-rc.1")
    bundle.add_argument("--participant-role", default="ML practitioner")
    bundle.add_argument("--format", choices=["markdown", "json"], default="markdown")
    return parser


def run_intake(argv: list[str]) -> None:
    """Run an intake-bundle command."""
    args = build_intake_parser().parse_args(argv)
    try:
        sys.stdout.write(handle_intake_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def handle_intake_command(args: argparse.Namespace) -> str:
    """Execute one parsed intake command."""
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
