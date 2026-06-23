"""Validate Host Proof Sprint runbook links and replay evidence plumbing."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_DEFAULT_README_PATH = Path("README.md")
_DEFAULT_RUNBOOK_PATH = Path("docs/HOST_PROOF_SPRINT.md")
_DEFAULT_SCHEMA_PATH = Path("docs/HOST_MANUAL_RUNS.schema.json")
_DEFAULT_ACCEPTANCE_PATH = Path("docs/HOST_ACCEPTANCE.md")

_RUNBOOK_REQUIRED_PHRASES = (
    "docs/FIRST_10_MINUTES.md",
    "examples/first_10_minutes_prompt.md",
    "scripts/export_manual_host_acceptance_packet.py",
    "scripts/record_host_manual_run.py --kind first-10-minutes",
    "scripts/check_first_10_minutes_replay.py",
    "docs/HOST_ACCEPTANCE_EVIDENCE.md",
    "Codex",
    "Claude Code",
)
_ACCEPTANCE_REQUIRED_PHRASES = (
    "scripts/check_first_10_minutes_replay.py",
    "--kind first-10-minutes",
)


@dataclass(frozen=True)
class HostProofSprintConfig:
    """Inputs for Host Proof Sprint readiness checks."""

    readme_path: Path = _DEFAULT_README_PATH
    runbook_path: Path = _DEFAULT_RUNBOOK_PATH
    manual_runs_schema_path: Path = _DEFAULT_SCHEMA_PATH
    host_acceptance_path: Path = _DEFAULT_ACCEPTANCE_PATH


@dataclass(frozen=True)
class HostProofSprintCheck:
    """One Host Proof Sprint readiness check result."""

    name: str
    ok: bool
    message: str


@dataclass(frozen=True)
class HostProofSprintReport:
    """Aggregate Host Proof Sprint readiness result."""

    checks: list[HostProofSprintCheck]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    @property
    def by_name(self) -> dict[str, HostProofSprintCheck]:
        return {check.name: check for check in self.checks}


def check_host_proof_sprint(config: HostProofSprintConfig | None = None) -> HostProofSprintReport:
    """Validate that host proof sprint materials can guide real replay evidence capture."""
    config = config or HostProofSprintConfig()
    return HostProofSprintReport(
        checks=[
            _check_required_text("runbook", config.runbook_path, required_phrases=_RUNBOOK_REQUIRED_PHRASES),
            _check_schema(config.manual_runs_schema_path),
            _check_readme_link(config.readme_path),
            _check_required_text(
                "acceptance_docs",
                config.host_acceptance_path,
                required_phrases=_ACCEPTANCE_REQUIRED_PHRASES,
            ),
        ]
    )


def main() -> None:
    """CLI entrypoint for local and release Host Proof Sprint checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", type=Path, default=_DEFAULT_README_PATH)
    parser.add_argument("--runbook", type=Path, default=_DEFAULT_RUNBOOK_PATH)
    parser.add_argument("--manual-runs-schema", type=Path, default=_DEFAULT_SCHEMA_PATH)
    parser.add_argument("--host-acceptance", type=Path, default=_DEFAULT_ACCEPTANCE_PATH)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    report = check_host_proof_sprint(
        HostProofSprintConfig(
            readme_path=args.readme,
            runbook_path=args.runbook,
            manual_runs_schema_path=args.manual_runs_schema,
            host_acceptance_path=args.host_acceptance,
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
        sys.stdout.write(f"host proof sprint checks passed: {checked}\n")


def _check_required_text(name: str, path: Path, *, required_phrases: tuple[str, ...]) -> HostProofSprintCheck:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return HostProofSprintCheck(name=name, ok=False, message=str(exc))
    missing = [phrase for phrase in required_phrases if phrase not in text]
    if missing:
        return HostProofSprintCheck(name=name, ok=False, message=f"{path} missing: {', '.join(missing)}")
    return HostProofSprintCheck(name=name, ok=True, message=f"{path} contains required host proof anchors")


def _check_schema(path: Path) -> HostProofSprintCheck:
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return HostProofSprintCheck(name="manual_runs_schema", ok=False, message=str(exc))
    replay = _nested_dict(schema, "properties", "first_10_minutes_replay", "items", "properties")
    if replay is None:
        return HostProofSprintCheck(
            name="manual_runs_schema",
            ok=False,
            message=f"{path} must define first_10_minutes_replay items",
        )
    if "artifacts" not in replay:
        return HostProofSprintCheck(
            name="manual_runs_schema",
            ok=False,
            message=f"{path} must define first_10_minutes_replay artifacts",
        )
    return HostProofSprintCheck(
        name="manual_runs_schema",
        ok=True,
        message=f"{path} defines first_10_minutes_replay artifacts",
    )


def _check_readme_link(path: Path) -> HostProofSprintCheck:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return HostProofSprintCheck(name="readme_link", ok=False, message=str(exc))
    link = "[docs/HOST_PROOF_SPRINT.md](docs/HOST_PROOF_SPRINT.md)"
    if link not in text:
        return HostProofSprintCheck(name="readme_link", ok=False, message=f"README must link to {link}")
    return HostProofSprintCheck(name="readme_link", ok=True, message="README links to Host Proof Sprint")


def _nested_dict(value: dict[str, Any], *keys: str) -> dict[str, Any] | None:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, dict) else None


def _write_text_failures(report: HostProofSprintReport) -> None:
    for check in report.checks:
        if not check.ok:
            sys.stderr.write(f"[{check.name}] {check.message}\n")


def _report_payload(report: HostProofSprintReport) -> dict[str, object]:
    return {"ok": report.ok, "checks": [asdict(check) for check in report.checks]}


if __name__ == "__main__":
    main()
