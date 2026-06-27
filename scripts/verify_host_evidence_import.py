"""Verify proposed host evidence imports without writing manual records."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_host_manual_runs import HostName, HostStatus, validate_host_manual_runs

CandidateKind = Literal["manual_host_ui", "host-ui", "first_10_minutes_replay", "first-10-minutes"]
NormalizedKind = Literal["manual_host_ui", "first_10_minutes_replay"]
ImportStatus = Literal["ready_to_record", "partial_ready_to_record", "blocked"]

_DEFAULT_RECORDS_PATH = Path("docs/HOST_MANUAL_RUNS.json")
_P0_HOSTS: tuple[HostName, ...] = ("Codex", "Claude Code")
_P0_GATES: tuple[NormalizedKind, ...] = ("first_10_minutes_replay", "manual_host_ui")
_NON_FABRICATION_POLICY = (
    "This helper is verify-only: it validates proposed manual evidence and returns recording commands."
)
_PLACEHOLDER_FRAGMENTS = (
    "<redacted evidence>",
    "<symptom>",
    "<first failing gate>",
    "yyyy-mm-dd",
    "todo",
    "placeholder",
    "fake evidence",
    "lorem ipsum",
    "no reviewer-observed real ui evidence recorded",
    "passed in the real host ui with redacted reviewer-observed evidence",
)
_MIN_REVIEWER_EVIDENCE_LENGTH = 30


class HostEvidenceCandidate(BaseModel):
    """One proposed evidence record before it is written to HOST_MANUAL_RUNS.json."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: CandidateKind
    host: HostName
    status: HostStatus
    date: date
    evidence: str = Field(min_length=1)
    artifacts: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_replay_artifacts_for_passed_runs(self) -> HostEvidenceCandidate:
        """Keep passed first-10-minutes records reproducible."""
        if self.normalized_kind == "first_10_minutes_replay" and self.status == "passed" and not self.artifacts:
            msg = "passed first_10_minutes_replay records require at least one artifact"
            raise ValueError(msg)
        if self.normalized_kind == "manual_host_ui" and self.artifacts:
            msg = "manual_host_ui records must not include artifacts"
            raise ValueError(msg)
        return self

    @property
    def normalized_kind(self) -> NormalizedKind:
        """Return the canonical record kind used by docs/HOST_MANUAL_RUNS.json."""
        if self.kind in {"first_10_minutes_replay", "first-10-minutes"}:
            return "first_10_minutes_replay"
        return "manual_host_ui"


@dataclass(frozen=True)
class HostEvidenceImportReport:
    """Structured verification result for a proposed host evidence import."""

    source_path: str
    records_path: str
    import_status: ImportStatus
    write_performed: bool
    valid_records: list[dict[str, Any]]
    rejected_records: list[dict[str, Any]]
    missing_required_gates: list[tuple[str, str]]
    record_commands: list[str]
    non_fabrication_policy: str = _NON_FABRICATION_POLICY

    @property
    def ok(self) -> bool:
        """Whether every proposed record can be safely recorded."""
        return not self.rejected_records

    @property
    def valid_record_count(self) -> int:
        """Number of proposed records that passed import verification."""
        return len(self.valid_records)


def build_host_evidence_import_guide() -> dict[str, Any]:
    """Build the committed verify-only import guide."""
    return {
        "guide_status": "verify-only",
        "records_path": str(_DEFAULT_RECORDS_PATH),
        "target_hosts": list(_P0_HOSTS),
        "required_gates": list(_P0_GATES),
        "non_fabrication_policy": _NON_FABRICATION_POLICY,
        "verification_command": (
            "uv run python scripts/verify_host_evidence_import.py --input /path/to/host-evidence-candidate.json"
        ),
        "recording_command_source": "The verifier returns copyable scripts/record_host_manual_run.py commands.",
        "after_recording_commands": [
            "uv run python scripts/validate_host_manual_runs.py",
            "uv run python scripts/export_p0_host_evidence_ledger.py --output docs/P0_HOST_EVIDENCE_LEDGER.md",
            "uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md",
            "uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md",
            "uv run python scripts/check_release_readiness.py",
        ],
        "sample_input": {
            "records": [
                {
                    "kind": "manual_host_ui",
                    "host": "Codex",
                    "status": "passed",
                    "date": "2026-06-28",
                    "evidence": (
                        "Codex host UI listed the MCP tools and run_host_smoke_check returned preview_ready true."
                    ),
                },
                {
                    "kind": "first_10_minutes_replay",
                    "host": "Codex",
                    "status": "passed",
                    "date": "2026-06-28",
                    "evidence": (
                        "Codex completed smoke, preview validation, render_preview_batch, comparison, and export."
                    ),
                    "artifacts": ["docs/assets/demo/demo_report.md"],
                },
            ]
        },
    }


def render_host_evidence_import_guide_markdown(guide: dict[str, Any]) -> str:
    """Render the verify-only import guide as Markdown."""
    lines = [
        "# P0 Evidence Import Guide",
        "",
        f"Guide status: `{guide['guide_status']}`",
        f"Records path: `{guide['records_path']}`",
        f"Target hosts: `{', '.join(guide['target_hosts'])}`",
        f"Required gates: `{', '.join(guide['required_gates'])}`",
        "",
        "## Policy",
        "",
        f"{guide['non_fabrication_policy']} It does not write `{guide['records_path']}`.",
        "",
        "## Verify Candidate Evidence",
        "",
        "```bash",
        guide["verification_command"],
        "```",
        "",
        "The verifier accepts either a flat `records` list with `kind` or the canonical "
        "`manual_host_ui` / `first_10_minutes_replay` shape.",
        "",
        "## Sample Input",
        "",
        "```json",
        json.dumps(guide["sample_input"], indent=2),
        "```",
        "",
        "## Recording",
        "",
        guide["recording_command_source"],
        "",
        "## After Recording",
        "",
    ]
    lines.extend(f"- `{command}`" for command in guide["after_recording_commands"])
    return "\n".join(lines) + "\n"


def verify_host_evidence_import(
    *,
    source_path: Path,
    records_path: Path = _DEFAULT_RECORDS_PATH,
) -> HostEvidenceImportReport:
    """Verify candidate evidence and return commands that would record it."""
    if records_path.exists():
        validate_host_manual_runs(records_path)

    load_result = _load_candidate_records(source_path)
    rejected_records = list(load_result["rejected_records"])
    valid_candidates: list[HostEvidenceCandidate] = []
    for candidate in load_result["candidates"]:
        issues = _candidate_evidence_issues(candidate)
        if issues:
            rejected_records.append(_rejected_record(candidate, issues=issues))
            continue
        valid_candidates.append(candidate)

    missing_required_gates = _missing_required_gates(valid_candidates)
    import_status: ImportStatus
    if rejected_records:
        import_status = "blocked"
    elif missing_required_gates:
        import_status = "partial_ready_to_record"
    else:
        import_status = "ready_to_record"

    return HostEvidenceImportReport(
        source_path=str(source_path),
        records_path=str(records_path),
        import_status=import_status,
        write_performed=False,
        valid_records=[_candidate_payload(candidate) for candidate in valid_candidates],
        rejected_records=rejected_records,
        missing_required_gates=missing_required_gates,
        record_commands=[_record_command(candidate) for candidate in valid_candidates],
    )


def render_host_evidence_import_report_markdown(report: HostEvidenceImportReport) -> str:
    """Render one verification report as Markdown."""
    lines = [
        "# Host Evidence Import Verification",
        "",
        f"Source path: `{report.source_path}`",
        f"Records path: `{report.records_path}`",
        f"Import status: `{report.import_status}`",
        f"Write performed: `{str(report.write_performed).lower()}`",
        "",
        "## Policy",
        "",
        report.non_fabrication_policy,
        "",
        "## Summary",
        "",
        f"- valid_record_count: `{report.valid_record_count}`",
        f"- rejected_record_count: `{len(report.rejected_records)}`",
        f"- missing_required_gate_count: `{len(report.missing_required_gates)}`",
        "",
    ]
    if report.rejected_records:
        lines.extend(["## Rejected Records", ""])
        lines.extend(
            (
                f"- `{record.get('kind', 'unknown')}` `{record.get('host', 'unknown')}`: "
                f"{'; '.join(str(issue) for issue in record['issues'])}"
            )
            for record in report.rejected_records
        )
        lines.append("")
    if report.missing_required_gates:
        lines.extend(["## Missing Required Gates", ""])
        lines.extend(f"- `{host}` `{gate}`" for host, gate in report.missing_required_gates)
        lines.append("")
    if report.record_commands:
        lines.extend(["## Recording Commands", "", "```bash"])
        lines.extend(report.record_commands)
        lines.extend(["```", ""])
    return "\n".join(lines)


def main() -> None:
    """CLI entrypoint for verify-only host evidence imports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=None, help="Candidate evidence JSON to verify.")
    parser.add_argument("--records", type=Path, default=_DEFAULT_RECORDS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.input is None:
        guide = build_host_evidence_import_guide()
        content = (
            json.dumps(guide, indent=2) + "\n"
            if args.format == "json"
            else render_host_evidence_import_guide_markdown(guide)
        )
        _write_or_print(content=content, output=args.output)
        return

    try:
        report = verify_host_evidence_import(source_path=args.input, records_path=args.records)
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc

    content = (
        json.dumps(_report_payload(report), indent=2) + "\n"
        if args.format == "json"
        else render_host_evidence_import_report_markdown(report)
    )
    _write_or_print(content=content, output=args.output)
    if not report.ok:
        raise SystemExit(1)


def _load_candidate_records(source_path: Path) -> dict[str, list[Any]]:
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"{source_path}: invalid JSON: {exc.msg}"
        raise ValueError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"{source_path}: expected a JSON object"
        raise TypeError(msg)

    raw_records = _raw_candidate_records(payload)
    candidates: list[HostEvidenceCandidate] = []
    rejected_records: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_records, start=1):
        if not isinstance(raw, dict):
            rejected_records.append(
                {"index": index, "kind": "unknown", "host": "unknown", "issues": ["record must be a JSON object"]}
            )
            continue
        try:
            candidates.append(HostEvidenceCandidate.model_validate(raw))
        except ValidationError as exc:
            rejected_records.append(_rejected_raw_record(index=index, raw=raw, exc=exc))
    return {"candidates": candidates, "rejected_records": rejected_records}


def _raw_candidate_records(payload: dict[str, Any]) -> list[dict[str, Any] | object]:
    if "records" in payload:
        records = payload["records"]
        if not isinstance(records, list):
            msg = "records must be a list"
            raise ValueError(msg)
        return records

    raw_records: list[dict[str, Any] | object] = []
    for kind in _P0_GATES:
        records = payload.get(kind, [])
        if not isinstance(records, list):
            msg = f"{kind} must be a list"
            raise TypeError(msg)
        raw_records.extend({**record, "kind": kind} if isinstance(record, dict) else record for record in records)
    return raw_records


def _candidate_evidence_issues(candidate: HostEvidenceCandidate) -> list[str]:
    text = candidate.evidence.strip()
    lower_text = text.lower()
    issues: list[str] = []
    if any(fragment in lower_text for fragment in _PLACEHOLDER_FRAGMENTS):
        issues.append("evidence contains placeholder text instead of reviewer-observed host UI evidence")
    if len(text) < _MIN_REVIEWER_EVIDENCE_LENGTH:
        issues.append("evidence is too short to be reviewer-observed host UI evidence")
    if candidate.status == "passed" and candidate.host.lower() not in lower_text:
        issues.append("passed evidence must name the host observed in the UI")
    return issues


def _missing_required_gates(candidates: list[HostEvidenceCandidate]) -> list[tuple[str, str]]:
    passed = {(candidate.host, candidate.normalized_kind) for candidate in candidates if candidate.status == "passed"}
    return [(host, gate) for host in _P0_HOSTS for gate in _P0_GATES if (host, gate) not in passed]


def _rejected_record(candidate: HostEvidenceCandidate, *, issues: list[str]) -> dict[str, Any]:
    payload = _candidate_payload(candidate)
    payload["issues"] = issues
    return payload


def _rejected_raw_record(*, index: int, raw: dict[str, Any], exc: ValidationError) -> dict[str, Any]:
    return {
        "index": index,
        "kind": str(raw.get("kind", "unknown")),
        "host": str(raw.get("host", "unknown")),
        "issues": [f"{error['loc'][0]}: {error['msg']}" for error in exc.errors()],
    }


def _candidate_payload(candidate: HostEvidenceCandidate) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": candidate.normalized_kind,
        "host": candidate.host,
        "status": candidate.status,
        "date": candidate.date.isoformat(),
        "evidence": candidate.evidence,
    }
    if candidate.normalized_kind == "first_10_minutes_replay":
        payload["artifacts"] = list(candidate.artifacts)
    return payload


def _record_command(candidate: HostEvidenceCandidate) -> str:
    args = ["uv", "run", "python", "scripts/record_host_manual_run.py"]
    if candidate.normalized_kind == "first_10_minutes_replay":
        args.extend(["--kind", "first-10-minutes"])
    else:
        args.extend(["--kind", "host-ui"])
    args.extend(
        [
            "--host",
            candidate.host,
            "--status",
            candidate.status,
            "--date",
            candidate.date.isoformat(),
            "--evidence",
            candidate.evidence,
        ]
    )
    for artifact in candidate.artifacts:
        args.extend(["--artifact", artifact])
    return " ".join(shlex.quote(arg) for arg in args)


def _report_payload(report: HostEvidenceImportReport) -> dict[str, object]:
    payload = asdict(report)
    payload["ok"] = report.ok
    payload["valid_record_count"] = report.valid_record_count
    return payload


def _write_or_print(*, content: str, output: Path | None) -> None:
    if output is None:
        sys.stdout.write(content)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
