"""Validate the first-10-minutes entrypoints for new MCP users."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_DEFAULT_README_PATH = Path("README.md")
_DEFAULT_GUIDE_PATH = Path("docs/FIRST_10_MINUTES.md")
_DEFAULT_PROMPT_PATH = Path("examples/first_10_minutes_prompt.md")
_DEFAULT_DEMO_MANIFEST_PATH = Path("docs/assets/demo/demo_manifest.json")
_DEFAULT_DEMO_REPORT_PATH = Path("docs/assets/demo/demo_report.md")

_GUIDE_REQUIRED_PHRASES = (
    "uvx --from albumentationsx-mcp albumentationsx-mcp",
    "examples/first_10_minutes_prompt.md",
    "docs/assets/demo/demo_report.md",
    "run_host_smoke_check",
    "plan_dataset_onboarding",
    "validate_preview_request",
    "render_preview_batch",
    "compare_preview_runs",
    "export_pipeline",
    "docs/INSTALL.md",
    "docs/USAGE.md",
)
_PROMPT_REQUIRED_PHRASES = (
    "run_host_smoke_check",
    "plan_dataset_onboarding",
    "Do not render anything until validate_preview_request returns valid=true.",
    "render_preview_batch",
    "compare_preview_runs",
    "export_pipeline",
    "docs/assets/demo/demo_report.md",
)


@dataclass(frozen=True)
class FirstTenMinutesConfig:
    """Inputs for first-10-minutes readiness checks."""

    readme_path: Path = _DEFAULT_README_PATH
    guide_path: Path = _DEFAULT_GUIDE_PATH
    prompt_path: Path = _DEFAULT_PROMPT_PATH
    demo_manifest_path: Path = _DEFAULT_DEMO_MANIFEST_PATH
    demo_report_path: Path = _DEFAULT_DEMO_REPORT_PATH


@dataclass(frozen=True)
class FirstTenMinutesCheck:
    """One first-10-minutes readiness check result."""

    name: str
    ok: bool
    message: str


@dataclass(frozen=True)
class FirstTenMinutesReport:
    """Aggregate first-10-minutes readiness result."""

    checks: list[FirstTenMinutesCheck]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    @property
    def by_name(self) -> dict[str, FirstTenMinutesCheck]:
        return {check.name: check for check in self.checks}


def check_first_10_minutes(config: FirstTenMinutesConfig | None = None) -> FirstTenMinutesReport:
    """Validate that quick-start entrypoints stay linked and actionable."""
    config = config or FirstTenMinutesConfig()
    checks = [
        _check_readme_entrypoint(config.readme_path),
        _check_required_text("quickstart_guide", config.guide_path, required_phrases=_GUIDE_REQUIRED_PHRASES),
        _check_required_text("host_prompt", config.prompt_path, required_phrases=_PROMPT_REQUIRED_PHRASES),
        _check_demo_artifacts(config.demo_manifest_path, config.demo_report_path),
    ]
    return FirstTenMinutesReport(checks=checks)


def main() -> None:
    """CLI entrypoint for local and CI first-10-minutes checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", type=Path, default=_DEFAULT_README_PATH)
    parser.add_argument("--guide", type=Path, default=_DEFAULT_GUIDE_PATH)
    parser.add_argument("--prompt", type=Path, default=_DEFAULT_PROMPT_PATH)
    parser.add_argument("--demo-manifest", type=Path, default=_DEFAULT_DEMO_MANIFEST_PATH)
    parser.add_argument("--demo-report", type=Path, default=_DEFAULT_DEMO_REPORT_PATH)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    report = check_first_10_minutes(
        FirstTenMinutesConfig(
            readme_path=args.readme,
            guide_path=args.guide,
            prompt_path=args.prompt,
            demo_manifest_path=args.demo_manifest,
            demo_report_path=args.demo_report,
        )
    )
    if args.format == "json":
        sys.stdout.write(json.dumps(_report_payload(report), indent=2))
        sys.stdout.write("\n")
    if not report.ok:
        if args.format == "text":
            _write_text_failures(report)
        raise SystemExit(1)
    if args.format == "text":
        checked = ", ".join(check.name for check in report.checks)
        sys.stdout.write(f"first-10-minutes checks passed: {checked}\n")


def _check_readme_entrypoint(path: Path) -> FirstTenMinutesCheck:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return FirstTenMinutesCheck(name="readme_entrypoint", ok=False, message=str(exc))
    required_link = "[docs/FIRST_10_MINUTES.md](docs/FIRST_10_MINUTES.md)"
    if required_link not in text:
        return FirstTenMinutesCheck(
            name="readme_entrypoint",
            ok=False,
            message=f"README must link to {required_link}",
        )
    return FirstTenMinutesCheck(
        name="readme_entrypoint",
        ok=True,
        message="README links to the first-10-minutes guide",
    )


def _check_required_text(name: str, path: Path, *, required_phrases: tuple[str, ...]) -> FirstTenMinutesCheck:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return FirstTenMinutesCheck(name=name, ok=False, message=str(exc))
    missing = [phrase for phrase in required_phrases if phrase not in text]
    if missing:
        return FirstTenMinutesCheck(
            name=name,
            ok=False,
            message=f"{path} is missing required phrases: {', '.join(missing)}",
        )
    return FirstTenMinutesCheck(name=name, ok=True, message=f"{path} has the required workflow anchors")


def _check_demo_artifacts(manifest_path: Path, report_path: Path) -> FirstTenMinutesCheck:
    missing = [str(path) for path in (manifest_path, report_path) if not path.exists()]
    if missing:
        return FirstTenMinutesCheck(
            name="demo_artifacts",
            ok=False,
            message=f"missing first-10-minutes demo artifacts: {', '.join(missing)}",
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return FirstTenMinutesCheck(name="demo_artifacts", ok=False, message=str(exc))
    missing_keys = [key for key in ("workflow", "demo_report") if key not in manifest]
    if missing_keys:
        return FirstTenMinutesCheck(
            name="demo_artifacts",
            ok=False,
            message=f"{manifest_path} is missing keys: {', '.join(missing_keys)}",
        )
    return FirstTenMinutesCheck(name="demo_artifacts", ok=True, message="demo report and manifest are present")


def _write_text_failures(report: FirstTenMinutesReport) -> None:
    for check in report.checks:
        if not check.ok:
            sys.stderr.write(f"[{check.name}] {check.message}\n")


def _report_payload(report: FirstTenMinutesReport) -> dict[str, object]:
    return {"ok": report.ok, "checks": [asdict(check) for check in report.checks]}


if __name__ == "__main__":
    main()
