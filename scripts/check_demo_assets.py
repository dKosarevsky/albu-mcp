"""Validate the deterministic public demo asset bundle."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.render_demo_assets import render_demo_assets

_REQUIRED_FILES = (
    "inputs/sample-grid.png",
    "contact_sheet.png",
    "comparison_contact_sheet.png",
    "demo_report.md",
    "demo_manifest.json",
)
_REQUIRED_MANIFEST_KEYS = (
    "workflow",
    "input",
    "contact_sheet",
    "comparison_contact_sheet",
    "baseline_pipeline",
    "candidate_pipeline",
    "compare_preview_runs",
    "demo_report",
)


@dataclass(frozen=True)
class DemoAssetCheckReport:
    """Result of validating the generated public demo asset bundle."""

    ok: bool
    output_dir: Path
    manifest_path: Path
    files: list[str]
    message: str


def check_demo_assets(
    output_dir: Path = Path("docs/assets/demo"),
    *,
    check_fresh: bool = False,
) -> DemoAssetCheckReport:
    """Regenerate deterministic demo assets and validate required bundle files."""
    if check_fresh:
        return _check_committed_demo_assets(output_dir)
    manifest_path = render_demo_assets(output_dir)
    missing, missing_keys = _missing_bundle_parts(output_dir, manifest_path)
    ok = not missing and not missing_keys
    message = _message(missing=missing, missing_keys=missing_keys, stale=[])
    return DemoAssetCheckReport(
        ok=ok,
        output_dir=output_dir,
        manifest_path=manifest_path,
        files=list(_REQUIRED_FILES),
        message=message,
    )


def main() -> None:
    """CLI entrypoint for CI and release demo checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/assets/demo"))
    parser.add_argument("--check", action="store_true", help="Compare committed assets with freshly generated output.")
    args = parser.parse_args()

    report = check_demo_assets(args.output_dir, check_fresh=args.check)
    if report.ok:
        sys.stdout.write(f"demo asset bundle is valid: {report.manifest_path}\n")
        return
    sys.stderr.write(f"{report.message}\n")
    raise SystemExit(1)


def _check_committed_demo_assets(output_dir: Path) -> DemoAssetCheckReport:
    manifest_path = output_dir / "demo_manifest.json"
    missing, missing_keys = _missing_bundle_parts(output_dir, manifest_path)
    with tempfile.TemporaryDirectory(prefix="albu-demo-assets-") as tmp_dir:
        expected_dir = Path(tmp_dir) / "demo"
        render_demo_assets(expected_dir)
        stale = [
            name
            for name in _REQUIRED_FILES
            if (output_dir / name).exists() and (output_dir / name).read_bytes() != (expected_dir / name).read_bytes()
        ]
    ok = not missing and not missing_keys and not stale
    return DemoAssetCheckReport(
        ok=ok,
        output_dir=output_dir,
        manifest_path=manifest_path,
        files=list(_REQUIRED_FILES),
        message=_message(missing=missing, missing_keys=missing_keys, stale=stale),
    )


def _missing_bundle_parts(output_dir: Path, manifest_path: Path) -> tuple[list[str], list[str]]:
    missing = [name for name in _REQUIRED_FILES if not (output_dir / name).exists()]
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        missing_keys = [key for key in _REQUIRED_MANIFEST_KEYS if key not in manifest]
    else:
        missing_keys = list(_REQUIRED_MANIFEST_KEYS)
    return missing, missing_keys


def _message(*, missing: list[str], missing_keys: list[str], stale: list[str]) -> str:
    parts: list[str] = []
    if missing:
        parts.append(f"missing files: {', '.join(missing)}")
    if missing_keys:
        parts.append(f"missing manifest keys: {', '.join(missing_keys)}")
    if stale:
        parts.append(f"stale files: {', '.join(stale)}")
    return "; ".join(parts) if parts else "demo asset bundle is valid"


if __name__ == "__main__":
    main()
