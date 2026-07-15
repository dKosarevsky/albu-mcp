"""First-preview operator handoff CLI adapter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from albumentationsx_mcp.adapters.cli.contracts import CliGroupSurface
from albumentationsx_mcp.first_preview import build_first_preview_pack, render_first_preview_pack_markdown

SURFACE = CliGroupSurface(group="preview", commands=("first-pack",))


def build_preview_parser() -> argparse.ArgumentParser:
    """Build the first-preview command parser."""
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
    return parser


def run_preview(argv: list[str]) -> None:
    """Run a first-preview command."""
    args = build_preview_parser().parse_args(argv)
    try:
        sys.stdout.write(handle_preview_command(args))
    except (ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc


def handle_preview_command(args: argparse.Namespace) -> str:
    """Execute one parsed first-preview command."""
    if args.command != "first-pack":
        message = f"unsupported preview command: {args.command}"
        raise ValueError(message)
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
