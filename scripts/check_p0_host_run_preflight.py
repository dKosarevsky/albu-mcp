"""Run local preflight checks before manual P0 host UI sessions."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_demo_assets import check_demo_assets
from scripts.validate_host_manual_runs import validate_host_manual_runs

_DEFAULT_ALLOWED_ROOT = Path("docs/assets/demo/inputs")
_DEFAULT_ARTIFACT_ROOT = Path("docs/assets/demo")
_DEFAULT_PROMPT_PATH = Path("examples/first_10_minutes_prompt.md")
_DEFAULT_SESSION_PATH = Path("docs/P0_HOST_RUN_SESSION.md")
_DEFAULT_MANUAL_RUNS_PATH = Path("docs/HOST_MANUAL_RUNS.json")


@dataclass(frozen=True)
class P0HostRunPreflightConfig:
    """Inputs for local P0 host run preflight checks."""

    allowed_root: Path = _DEFAULT_ALLOWED_ROOT
    artifact_root: Path = _DEFAULT_ARTIFACT_ROOT
    prompt_path: Path = _DEFAULT_PROMPT_PATH
    run_session_path: Path = _DEFAULT_SESSION_PATH
    manual_runs_path: Path = _DEFAULT_MANUAL_RUNS_PATH


@dataclass(frozen=True)
class P0HostRunPreflightCheck:
    """One P0 host run preflight result."""

    name: str
    ok: bool
    message: str


@dataclass(frozen=True)
class P0HostRunPreflightReport:
    """Aggregate P0 host run preflight result."""

    checks: list[P0HostRunPreflightCheck]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    @property
    def by_name(self) -> dict[str, P0HostRunPreflightCheck]:
        return {check.name: check for check in self.checks}


def check_p0_host_run_preflight(
    config: P0HostRunPreflightConfig | None = None,
) -> P0HostRunPreflightReport:
    """Check local prerequisites before starting real host UI evidence runs."""
    config = config or P0HostRunPreflightConfig()
    checks = [
        _check_package_import(),
        _check_directory("allowed_root", config.allowed_root),
        _check_directory("artifact_root", config.artifact_root),
        _check_demo_assets(config.artifact_root),
        _check_host_prompt(config.prompt_path),
        _check_run_session_doc(config.run_session_path),
        _check_manual_records(config.manual_runs_path),
    ]
    return P0HostRunPreflightReport(checks=checks)


def render_p0_host_run_preflight_markdown(report: P0HostRunPreflightReport) -> str:
    """Render a P0 host run preflight report as Markdown."""
    lines = [
        "# P0 Host Run Preflight",
        "",
        f"Preflight status: `{'passed' if report.ok else 'failed'}`",
        "",
        "Record real host UI evidence only after this preflight passes.",
        "",
        "## Checks",
        "",
        "| Check | Status | Message |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {check.name} | {'passed' if check.ok else 'failed'} | {_escape_markdown_cell(check.message)} |"
        for check in report.checks
    )
    lines.extend(
        [
            "",
            "## Next Commands",
            "",
            "- `uv run python scripts/check_p0_host_run_preflight.py`",
            "- `uv run python scripts/export_p0_host_run_session.py --output docs/P0_HOST_RUN_SESSION.md`",
            "- `uv run python scripts/record_host_manual_run.py ...`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for P0 host run preflight checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allowed-root", type=Path, default=_DEFAULT_ALLOWED_ROOT)
    parser.add_argument("--artifact-root", type=Path, default=_DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--prompt", type=Path, default=_DEFAULT_PROMPT_PATH)
    parser.add_argument("--run-session", type=Path, default=_DEFAULT_SESSION_PATH)
    parser.add_argument("--manual-runs", type=Path, default=_DEFAULT_MANUAL_RUNS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    report = check_p0_host_run_preflight(
        P0HostRunPreflightConfig(
            allowed_root=args.allowed_root,
            artifact_root=args.artifact_root,
            prompt_path=args.prompt,
            run_session_path=args.run_session,
            manual_runs_path=args.manual_runs,
        )
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_p0_host_run_preflight_markdown(report), encoding="utf-8")
    if args.format == "json":
        sys.stdout.write(json.dumps(_report_payload(report), indent=2))
        sys.stdout.write("\n")
    if not report.ok:
        if args.format == "text":
            _write_text_failures(report)
        raise SystemExit(1)
    if args.format == "text":
        checked = ", ".join(check.name for check in report.checks)
        sys.stdout.write(f"p0 host run preflight passed: {checked}\n")


def _check_package_import() -> P0HostRunPreflightCheck:
    try:
        importlib.import_module("albumentationsx_mcp")
    except ImportError as exc:
        return P0HostRunPreflightCheck(name="package_import", ok=False, message=str(exc))
    return P0HostRunPreflightCheck(name="package_import", ok=True, message="albumentationsx_mcp imports")


def _check_directory(name: str, path: Path) -> P0HostRunPreflightCheck:
    if not path.exists():
        return P0HostRunPreflightCheck(name=name, ok=False, message=f"{path} does not exist")
    if not path.is_dir():
        return P0HostRunPreflightCheck(name=name, ok=False, message=f"{path} is not a directory")
    return P0HostRunPreflightCheck(name=name, ok=True, message=str(path))


def _check_demo_assets(artifact_root: Path) -> P0HostRunPreflightCheck:
    report = check_demo_assets(artifact_root, check_fresh=True)
    return P0HostRunPreflightCheck(name="demo_assets", ok=report.ok, message=report.message)


def _check_host_prompt(path: Path) -> P0HostRunPreflightCheck:
    required = ("run_host_smoke_check", "validate_preview_request", "render_preview_batch", "compare_preview_runs")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return P0HostRunPreflightCheck(name="host_prompts", ok=False, message=str(exc))
    missing = [item for item in required if item not in text]
    if missing:
        return P0HostRunPreflightCheck(name="host_prompts", ok=False, message=f"{path} missing: {', '.join(missing)}")
    return P0HostRunPreflightCheck(name="host_prompts", ok=True, message=f"{path} has required host prompts")


def _check_run_session_doc(path: Path) -> P0HostRunPreflightCheck:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return P0HostRunPreflightCheck(name="run_session_doc", ok=False, message=str(exc))
    required = ("# P0 Host Run Session", "Codex", "Claude Code", "record_host_manual_run.py")
    missing = [item for item in required if item not in text]
    if missing:
        return P0HostRunPreflightCheck(
            name="run_session_doc",
            ok=False,
            message=f"{path} missing: {', '.join(missing)}",
        )
    return P0HostRunPreflightCheck(name="run_session_doc", ok=True, message=f"{path} is ready")


def _check_manual_records(path: Path) -> P0HostRunPreflightCheck:
    try:
        records = validate_host_manual_runs(path)
    except (OSError, ValueError) as exc:
        return P0HostRunPreflightCheck(name="manual_records", ok=False, message=str(exc))
    return P0HostRunPreflightCheck(
        name="manual_records",
        ok=True,
        message=f"{path} is valid ({len(records.manual_host_ui)} manual UI records)",
    )


def _write_text_failures(report: P0HostRunPreflightReport) -> None:
    for check in report.checks:
        if not check.ok:
            sys.stderr.write(f"[{check.name}] {check.message}\n")


def _report_payload(report: P0HostRunPreflightReport) -> dict[str, object]:
    return {"ok": report.ok, "checks": [asdict(check) for check in report.checks]}


def _escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


if __name__ == "__main__":
    main()
