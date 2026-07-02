"""Privacy-safe host evidence recording primitives for CLI adapters."""

from __future__ import annotations

import json
import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

HostName = Literal["Claude Desktop", "Claude Code", "Cursor", "Codex"]
HostStatus = Literal["passed", "blocked", "pending"]
OperatorPacketFormat = Literal["json", "markdown"]
HOST_NAMES: tuple[HostName, ...] = ("Claude Desktop", "Claude Code", "Cursor", "Codex")
P0_REQUIRED_HOSTS: tuple[HostName, ...] = ("Codex", "Claude Code")
P0_REQUIRED_GATES: tuple[str, ...] = ("manual_host_ui", "first_10_minutes_replay")
_NON_FABRICATION_POLICY = (
    "Record passed only after reviewer-observed real MCP host UI flow; generated smoke output alone is not accepted "
    "as P0 evidence."
)
_SYNTHETIC_ONLY_MARKERS = ("generated smoke", "smoke output only", "synthetic", "no reviewer-observed")


class HostManualRun(BaseModel):
    """One dated manual UI run record for an MCP host."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    host: HostName
    status: HostStatus
    date: date
    evidence: str = Field(min_length=1)


class FirstTenMinutesReplayRun(HostManualRun):
    """One dated first-10-minutes workflow replay record for an MCP host."""

    artifacts: list[str] = Field(default_factory=list)


class HostManualRuns(BaseModel):
    """Manual UI evidence records loaded from docs/HOST_MANUAL_RUNS.json."""

    model_config = ConfigDict(extra="forbid")

    manual_host_ui: list[HostManualRun] = Field(default_factory=list)
    first_10_minutes_replay: list[FirstTenMinutesReplayRun] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_unique_hosts(self) -> HostManualRuns:
        """Reject ambiguous overlays before generating host acceptance evidence."""
        _require_unique_hosts(self.manual_host_ui, label="manual host UI")
        _require_unique_hosts(self.first_10_minutes_replay, label="first 10 minutes replay")
        return self


@dataclass(frozen=True)
class FirstTenMinutesReplayEvidence:
    """Inputs for one first-10-minutes replay evidence record."""

    host: HostName
    status: HostStatus
    run_date: str
    evidence: str
    artifacts: list[str]


@dataclass(frozen=True)
class EvidenceArtifactImport:
    """Inputs for importing one reviewer-observed evidence session into required P0 gates."""

    path: Path
    host: HostName
    status: HostStatus
    run_date: str
    evidence: str
    artifacts: list[str]
    confirm_real_host_observed: bool = False


class EvidenceSessionManifest(BaseModel):
    """One reviewer-facing manifest for a manual evidence session."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    manifest_status: Literal["template", "filled"] = "template"
    host: HostName
    status: HostStatus = "pending"
    date: date
    reviewer: str = Field(min_length=1)
    evidence: str = "reviewer observed real host UI"
    artifacts: list[str] = Field(default_factory=list)
    commands_used: list[str] = Field(default_factory=list)
    confirm_real_host_observed: bool = False
    private_data_included: bool = False

    @model_validator(mode="after")
    def reject_private_manifest_data(self) -> EvidenceSessionManifest:
        """Keep evidence manifests safe before validation or import."""
        if self.private_data_included:
            msg = "private evidence manifest data must be redacted before validation"
            raise ValueError(msg)
        return self


def validate_host_manual_runs(path: Path = Path("docs/HOST_MANUAL_RUNS.json")) -> HostManualRuns:
    """Load and validate manual host evidence records."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return HostManualRuns.model_validate(payload)
    except json.JSONDecodeError as exc:
        msg = f"{path}: invalid JSON: {exc.msg}"
        raise ValueError(msg) from exc
    except ValidationError as exc:
        msg = f"{path}: invalid manual host run records\n{exc}"
        raise ValueError(msg) from exc


def record_host_manual_run(
    *,
    path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    host: HostName,
    status: HostStatus,
    run_date: str,
    evidence: str,
) -> HostManualRuns:
    """Add or replace one manual host run record and return the validated payload."""
    current = validate_host_manual_runs(path) if path.exists() else HostManualRuns()
    record = HostManualRun(host=host, status=status, date=date.fromisoformat(run_date), evidence=evidence)
    by_host = {item.host: item for item in current.manual_host_ui}
    by_host[record.host] = record
    ordered = [by_host[name] for name in HOST_NAMES if name in by_host]
    updated = HostManualRuns(manual_host_ui=ordered, first_10_minutes_replay=current.first_10_minutes_replay)
    write_host_manual_runs(path, updated)
    return updated


def record_first_10_minutes_replay(
    *,
    path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    replay: FirstTenMinutesReplayEvidence,
) -> HostManualRuns:
    """Add or replace one first-10-minutes host replay record."""
    current = validate_host_manual_runs(path) if path.exists() else HostManualRuns()
    record = FirstTenMinutesReplayRun(
        host=replay.host,
        status=replay.status,
        date=date.fromisoformat(replay.run_date),
        evidence=replay.evidence,
        artifacts=replay.artifacts,
    )
    by_host = {item.host: item for item in current.first_10_minutes_replay}
    by_host[replay.host] = record
    ordered = [by_host[name] for name in HOST_NAMES if name in by_host]
    updated = HostManualRuns(manual_host_ui=current.manual_host_ui, first_10_minutes_replay=ordered)
    write_host_manual_runs(path, updated)
    return updated


def write_host_manual_runs(path: Path, payload: HostManualRuns) -> None:
    """Write host evidence records in the canonical JSON representation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(content, encoding="utf-8")


def summarize_host_manual_runs(records: HostManualRuns) -> str:
    """Return a compact human-readable evidence record count."""
    return (
        "host evidence records are valid "
        f"(manual_host_ui={len(records.manual_host_ui)}, "
        f"first_10_minutes_replay={len(records.first_10_minutes_replay)})"
    )


def build_evidence_session_plan(
    *,
    host: HostName,
    path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
) -> dict[str, Any]:
    """Build a guided real-host evidence session plan without writing evidence records."""
    records = validate_host_manual_runs(path) if path.exists() else HostManualRuns()
    host_status = _host_gate_status(host=host, records=records)
    return {
        "host": host,
        "records_path": str(path),
        "session_status": "ready_to_record" if host_status["overall_status"] == "passed" else "operator_run_required",
        "writes_records": False,
        "non_fabrication_policy": _NON_FABRICATION_POLICY,
        "current_host_status": host_status,
        "operator_steps": _operator_steps(host),
        "recording_commands": {
            "passed": (
                "albu-mcp evidence import-artifacts "
                f"--host {host!r} --status passed --date YYYY-MM-DD --evidence '...' "
                "--artifact docs/assets/demo/demo_report.md --confirm-real-host-observed"
            ),
            "blocked": (
                "albu-mcp evidence import-artifacts "
                f"--host {host!r} --status blocked --date YYYY-MM-DD --evidence '...'"
            ),
        },
    }


def build_evidence_collect_wizard(
    *,
    host: HostName,
    path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    run_date: str,
    reviewer: str,
    output_dir: Path = Path("evidence-session"),
    artifact_ref: str = "docs/assets/demo/demo_report.md",
) -> dict[str, Any]:
    """Build one no-write operator path for collecting real host evidence."""
    date.fromisoformat(run_date)
    records = validate_host_manual_runs(path) if path.exists() else HostManualRuns()
    host_status = _host_gate_status(host=host, records=records)
    wizard_status = "ready_for_rc_review" if host_status["overall_status"] == "passed" else "operator_run_required"
    return {
        "wizard_status": wizard_status,
        "host": host,
        "records_path": str(path),
        "run_date": run_date,
        "reviewer": reviewer,
        "writes_records": False,
        "current_host_status": host_status,
        "non_fabrication_policy": _NON_FABRICATION_POLICY,
        "steps": _collect_wizard_steps(
            host=host,
            path=path,
            run_date=run_date,
            reviewer=reviewer,
            output_dir=output_dir,
            artifact_ref=artifact_ref,
        ),
        "next_actions": [
            "Run the setup probe from the same shell or app context that starts the real MCP host.",
            "Continue only after a reviewer observes the real MCP host UI and first-preview replay.",
            "Run validate-manifest before import-artifacts; import-artifacts is the first command that writes records.",
            "Run privacy-doctor and rc go-check after any real evidence import.",
        ],
    }


def import_evidence_artifacts(request: EvidenceArtifactImport) -> HostManualRuns:
    """Import one reviewer-observed host evidence session into both required P0 gates."""
    validate_evidence_artifact_import(request)
    record_host_manual_run(
        path=request.path,
        host=request.host,
        status=request.status,
        run_date=request.run_date,
        evidence=request.evidence,
    )
    return record_first_10_minutes_replay(
        path=request.path,
        replay=FirstTenMinutesReplayEvidence(
            host=request.host,
            status=request.status,
            run_date=request.run_date,
            evidence=request.evidence,
            artifacts=request.artifacts,
        ),
    )


def validate_evidence_artifact_import(request: EvidenceArtifactImport) -> dict[str, Any]:
    """Validate a reviewer-observed host evidence import without writing records."""
    if request.status == "passed" and not request.confirm_real_host_observed:
        msg = "--confirm-real-host-observed is required when recording passed evidence"
        raise ValueError(msg)
    if request.status == "passed" and not request.artifacts:
        msg = "at least one --artifact is required when validating passed first-10-minutes evidence"
        raise ValueError(msg)
    if request.status == "passed" and _looks_synthetic_only(request.evidence):
        msg = "passed evidence must not be synthetic-only"
        raise ValueError(msg)
    return {
        "validation_status": "ready_to_import" if request.status == "passed" else "ready_to_record_blocker",
        "writes_records": False,
        "records_path": str(request.path),
        "host": request.host,
        "status": request.status,
        "run_date": request.run_date,
        "artifact_count": len(request.artifacts),
        "required_gate_writes": list(P0_REQUIRED_GATES),
        "non_fabrication_policy": _NON_FABRICATION_POLICY,
        "next_actions": [
            "Run albu-mcp evidence import-artifacts with the same fields after reviewing this validation payload.",
            "Rerun albu-mcp evidence artifact-doctor --format json after import.",
        ],
    }


def build_evidence_session_manifest_artifact(
    *,
    host: HostName,
    run_date: str,
    reviewer: str,
) -> dict[str, str]:
    """Build a JSON evidence session manifest template without recording evidence."""
    manifest = EvidenceSessionManifest(
        host=host,
        date=date.fromisoformat(run_date),
        reviewer=reviewer,
        artifacts=["docs/assets/demo/demo_report.md"],
        commands_used=_session_manifest_commands(host),
    )
    return {
        "host": host,
        "filename": f"{_host_slug(host)}-evidence-session-manifest.json",
        "content": json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
    }


def load_evidence_session_manifest(path: Path) -> EvidenceSessionManifest:
    """Load and validate one evidence session manifest."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return EvidenceSessionManifest.model_validate(payload)
    except json.JSONDecodeError as exc:
        msg = f"{path}: invalid JSON: {exc.msg}"
        raise ValueError(msg) from exc
    except ValidationError as exc:
        msg = f"{path}: invalid evidence session manifest\n{exc}"
        raise ValueError(msg) from exc


def validate_evidence_session_manifest(
    *,
    manifest: EvidenceSessionManifest,
    records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
) -> dict[str, Any]:
    """Validate a session manifest through the existing no-write import validator."""
    report = validate_evidence_artifact_import(
        EvidenceArtifactImport(
            path=records_path,
            host=manifest.host,
            status=manifest.status,
            run_date=manifest.date.isoformat(),
            evidence=manifest.evidence,
            artifacts=manifest.artifacts,
            confirm_real_host_observed=manifest.confirm_real_host_observed,
        )
    )
    return {
        **report,
        "manifest_status": manifest.manifest_status,
        "reviewer": manifest.reviewer,
        "commands_used": manifest.commands_used,
    }


def build_evidence_doctor_report(path: Path = Path("docs/HOST_MANUAL_RUNS.json")) -> dict[str, Any]:
    """Inspect P0 host evidence records and return actionable remediation for missing gates."""
    records = validate_host_manual_runs(path) if path.exists() else HostManualRuns()
    host_statuses = {host: _host_gate_status(host=host, records=records) for host in P0_REQUIRED_HOSTS}
    flat_gates = [
        gate
        for status in host_statuses.values()
        for gate in [status["manual_host_ui"], status["first_10_minutes_replay"]]
    ]
    summary = {
        "required_gate_count": len(P0_REQUIRED_HOSTS) * len(P0_REQUIRED_GATES),
        "passed_gate_count": sum(gate == "passed" for gate in flat_gates),
        "blocked_gate_count": sum(gate == "blocked" for gate in flat_gates),
        "missing_gate_count": sum(gate == "missing" for gate in flat_gates),
    }
    return {
        "records_path": str(path),
        "rc_reopen_allowed": summary["passed_gate_count"] == summary["required_gate_count"],
        "non_fabrication_policy": _NON_FABRICATION_POLICY,
        "summary": summary,
        "host_statuses": host_statuses,
        "next_actions": _doctor_next_actions(summary),
    }


def build_evidence_unblock_plan(path: Path = Path("docs/HOST_MANUAL_RUNS.json")) -> dict[str, Any]:
    """Build a prioritized P0 real-host evidence unblock plan without writing records."""
    doctor = build_evidence_doctor_report(path)
    host_unblock_queue = [
        _host_unblock_item(host=host, status=status)
        for host, status in doctor["host_statuses"].items()
        if status["overall_status"] != "passed"
    ]
    return {
        "plan_status": "ready_for_rc_reopen" if not host_unblock_queue else "blocked",
        "records_path": str(path),
        "writes_records": False,
        "non_fabrication_policy": _NON_FABRICATION_POLICY,
        "blocked_host_count": len(host_unblock_queue),
        "first_blocker": host_unblock_queue[0] if host_unblock_queue else None,
        "host_unblock_queue": host_unblock_queue,
        "next_actions": _unblock_next_actions(host_unblock_queue),
    }


def build_evidence_execution_packet(
    *,
    host: HostName,
    path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
) -> dict[str, Any]:
    """Build a host-specific real MCP evidence execution packet without writing records."""
    session_plan = build_evidence_session_plan(host=host, path=path)
    return {
        "packet_status": "ready"
        if session_plan["current_host_status"]["overall_status"] == "passed"
        else "operator_action_required",
        "host": host,
        "records_path": str(path),
        "writes_records": False,
        "non_fabrication_policy": _NON_FABRICATION_POLICY,
        "host_setup_steps": _host_setup_steps(host),
        "expected_tools": _expected_mcp_tools(),
        "smoke_call": {
            "tool": "run_host_smoke_check",
            "required_result": "preview_ready=true",
            "failure_next_tool": "diagnose_environment",
        },
        "artifact_checklist": [
            "host_ui_screenshot_or_terminal_capture",
            "run_host_smoke_check_json",
            "first_10_minutes_replay_notes",
            "preview_or_contact_sheet_artifact_ref",
        ],
        "recording_commands": session_plan["recording_commands"],
        "current_host_status": session_plan["current_host_status"],
        "next_actions": [
            "Complete setup steps in the real MCP host UI.",
            "Run the smoke call and save redacted artifact references.",
            "Import passed evidence only after reviewer observation.",
        ],
    }


def build_evidence_operator_packet_artifact(
    *,
    host: HostName,
    path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    output_format: OperatorPacketFormat = "markdown",
) -> dict[str, str]:
    """Render a host-specific operator packet artifact without recording evidence."""
    packet = build_evidence_execution_packet(host=host, path=path)
    content = (
        json.dumps(packet, indent=2, sort_keys=True) + "\n"
        if output_format == "json"
        else _render_evidence_operator_packet_markdown(packet)
    )
    return {
        "host": host,
        "format": output_format,
        "filename": f"{_host_slug(host)}-evidence-operator-packet.{_operator_packet_extension(output_format)}",
        "content": content,
    }


def build_evidence_packet_bundle_artifacts(
    *,
    path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    output_format: OperatorPacketFormat = "markdown",
) -> dict[str, Any]:
    """Render P0 host operator packet artifacts plus a bundle index."""
    packet_artifacts = [
        build_evidence_operator_packet_artifact(host=host, path=path, output_format=output_format)
        for host in P0_REQUIRED_HOSTS
    ]
    index_filename = f"p0-evidence-packet-bundle.{_operator_packet_extension(output_format)}"
    index_content = (
        json.dumps(
            {
                "bundle_status": "ready_to_run",
                "records_path": str(path),
                "p0_hosts": list(P0_REQUIRED_HOSTS),
                "packet_files": [artifact["filename"] for artifact in packet_artifacts],
                "non_fabrication_policy": _NON_FABRICATION_POLICY,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
        if output_format == "json"
        else _render_evidence_packet_bundle_markdown(
            path=path,
            packet_artifacts=packet_artifacts,
        )
    )
    return {
        "bundle_status": "ready_to_run",
        "records_path": str(path),
        "format": output_format,
        "host_count": len(packet_artifacts),
        "index": {"filename": index_filename, "content": index_content},
        "packets": packet_artifacts,
    }


def build_evidence_replay_fixture_pack_artifact(
    *,
    output_format: OperatorPacketFormat = "markdown",
) -> dict[str, str]:
    """Render a local replay fixture pack that is explicitly not evidence."""
    pack = build_evidence_replay_fixture_pack()
    content = (
        json.dumps(pack, indent=2, sort_keys=True) + "\n"
        if output_format == "json"
        else _render_evidence_replay_fixture_pack_markdown(pack)
    )
    return {
        "format": output_format,
        "filename": f"real-host-replay-fixture-pack.{_operator_packet_extension(output_format)}",
        "content": content,
    }


def build_evidence_replay_fixture_pack() -> dict[str, Any]:
    """Build a safe fixture pack for replaying a real host flow without closing gates."""
    return {
        "pack_status": "ready_to_run",
        "writes_records": False,
        "evidence_status": "not_evidence",
        "fixture_policy": (
            "This fixture pack is not P0 evidence. It only gives an operator safe demo material for a real MCP "
            "host run; passed evidence still requires reviewer-observed host UI output."
        ),
        "safe_demo_assets": [
            "docs/assets/demo/inputs/sample-grid.png",
            "docs/assets/demo/contact_sheet.png",
            "docs/assets/demo/comparison_contact_sheet.png",
            "docs/assets/demo/demo_manifest.json",
            "docs/assets/demo/demo_report.md",
        ],
        "expected_preview_flow": [
            {
                "tool": "run_host_smoke_check",
                "expected_result": "preview_ready=true",
            },
            {
                "tool": "render_preview_batch",
                "expected_result": "preview artifact or contact sheet artifact reference",
            },
            {
                "tool": "compare_preview_runs",
                "expected_result": "baseline versus candidate comparison summary",
            },
            {
                "tool": "plan_preview_review",
                "expected_result": "human review checklist for too-noisy or off-goal variants",
            },
        ],
        "expected_artifact_refs": [
            "docs/assets/demo/demo_report.md",
            "docs/assets/demo/contact_sheet.png",
            "docs/assets/demo/comparison_contact_sheet.png",
        ],
        "operator_commands": [
            "albu-mcp activation runbook --format markdown",
            "albu-mcp evidence import-checklist --host Codex --format markdown",
            (
                "albu-mcp evidence validate-import --host Codex --status passed --date YYYY-MM-DD "
                "--evidence 'reviewer observed real host UI' --artifact docs/assets/demo/demo_report.md "
                "--confirm-real-host-observed --format json"
            ),
        ],
        "next_actions": [
            "Use these fixtures only inside a real MCP host session.",
            "Replace expected artifact refs with reviewer-observed artifact refs before importing passed evidence.",
            "Run privacy-doctor after any evidence import.",
        ],
    }


def build_evidence_import_checklist(
    *,
    host: HostName,
    path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
) -> dict[str, Any]:
    """Build a no-write checklist for one reviewer-observed evidence import."""
    return {
        "checklist_status": "ready_to_fill",
        "host": host,
        "records_path": str(path),
        "writes_records": False,
        "reviewer_confirmation_policy": _NON_FABRICATION_POLICY,
        "required_fields": [
            "host",
            "status",
            "date",
            "evidence",
            "artifact",
            "confirm_real_host_observed",
        ],
        "artifact_requirements": [
            "Use redacted artifact refs only.",
            "Attach at least one first-10-minutes replay artifact for passed evidence.",
            "Do not use private local dataset paths as committed artifact refs.",
        ],
        "validate_command": (
            "albu-mcp evidence validate-import "
            f"--host {host!r} --status passed --date YYYY-MM-DD "
            "--evidence 'reviewer observed real host UI' --artifact docs/assets/demo/demo_report.md "
            "--confirm-real-host-observed --format json"
        ),
        "import_command": (
            "albu-mcp evidence import-artifacts "
            f"--host {host!r} --status passed --date YYYY-MM-DD "
            "--evidence 'reviewer observed real host UI' --artifact docs/assets/demo/demo_report.md "
            "--confirm-real-host-observed"
        ),
        "next_actions": [
            "Run validate_command before importing.",
            "Run import_command only after reviewer-observed real host UI evidence exists.",
            "Run albu-mcp evidence privacy-doctor --format json after import.",
        ],
    }


def render_evidence_import_checklist_markdown(checklist: dict[str, Any]) -> str:
    """Render an evidence import checklist as Markdown."""
    required_fields = "\n".join(f"- `{field}`" for field in checklist["required_fields"])
    artifact_requirements = "\n".join(f"- {item}" for item in checklist["artifact_requirements"])
    next_actions = "\n".join(f"- {item}" for item in checklist["next_actions"])
    return (
        f"# {checklist['host']} Evidence Import Checklist\n\n"
        f"Records path: `{checklist['records_path']}`\n\n"
        f"Writes records: `{str(checklist['writes_records']).lower()}`\n\n"
        "## Reviewer Confirmation Policy\n\n"
        f"{checklist['reviewer_confirmation_policy']}\n\n"
        "## Required Fields\n\n"
        f"{required_fields}\n\n"
        "## Artifact Requirements\n\n"
        f"{artifact_requirements}\n\n"
        "## Validate Command\n\n"
        "```bash\n"
        f"{checklist['validate_command']}\n"
        "```\n\n"
        "## Import Command\n\n"
        "```bash\n"
        f"{checklist['import_command']}\n"
        "```\n\n"
        "## Next Actions\n\n"
        f"{next_actions}\n"
    )


def _render_evidence_replay_fixture_pack_markdown(pack: dict[str, Any]) -> str:
    safe_assets = "\n".join(f"- `{asset}`" for asset in pack["safe_demo_assets"])
    expected_preview_flow = "\n".join(
        f"- `{step['tool']}`: {step['expected_result']}" for step in pack["expected_preview_flow"]
    )
    expected_artifacts = "\n".join(f"- `{artifact}`" for artifact in pack["expected_artifact_refs"])
    operator_commands = "\n".join(f"{command}" for command in pack["operator_commands"])
    next_actions = "\n".join(f"- {action}" for action in pack["next_actions"])
    return (
        "# Real Host Replay Fixture Pack\n\n"
        f"Pack status: `{pack['pack_status']}`\n\n"
        f"Writes records: `{str(pack['writes_records']).lower()}`\n\n"
        f"Evidence status: `{pack['evidence_status']}`\n\n"
        "## Fixture Policy\n\n"
        f"{pack['fixture_policy']}\n\n"
        "## Safe Demo Assets\n\n"
        f"{safe_assets}\n\n"
        "## expected_preview_flow\n\n"
        f"{expected_preview_flow}\n\n"
        "## Expected Artifact Refs\n\n"
        f"{expected_artifacts}\n\n"
        "## Operator Commands\n\n"
        "```bash\n"
        f"{operator_commands}\n"
        "```\n\n"
        "## Next Actions\n\n"
        f"{next_actions}\n"
    )


def build_evidence_artifact_doctor_report(path: Path = Path("docs/HOST_MANUAL_RUNS.json")) -> dict[str, Any]:
    """Inspect evidence artifacts and flag synthetic-only or incomplete P0 records."""
    records = validate_host_manual_runs(path) if path.exists() else HostManualRuns()
    issues = _artifact_doctor_issues(records)
    passed_gate_count = _passed_gate_count(records)
    required_gate_count = len(P0_REQUIRED_HOSTS) * len(P0_REQUIRED_GATES)
    return {
        "artifact_status": "ready" if not issues and passed_gate_count == required_gate_count else "blocked",
        "records_path": str(path),
        "non_fabrication_policy": _NON_FABRICATION_POLICY,
        "passed_gate_count": passed_gate_count,
        "required_gate_count": required_gate_count,
        "issue_count": len(issues),
        "issues": issues,
        "next_actions": _artifact_doctor_next_actions(issues),
    }


def build_evidence_privacy_doctor_report(path: Path = Path("docs/HOST_MANUAL_RUNS.json")) -> dict[str, Any]:
    """Inspect evidence records for private artifact references and unsafe evidence notes."""
    records = validate_host_manual_runs(path) if path.exists() else HostManualRuns()
    issues = _privacy_doctor_issues(records)
    return {
        "privacy_status": "ready" if not issues else "blocked",
        "records_path": str(path),
        "non_fabrication_policy": _NON_FABRICATION_POLICY,
        "issue_count": len(issues),
        "issues": issues,
        "next_actions": _privacy_doctor_next_actions(issues),
    }


def _require_unique_hosts(records: Sequence[HostManualRun], *, label: str) -> None:
    seen: set[str] = set()
    for record in records:
        if record.host in seen:
            msg = f"Duplicate {label} record for {record.host!r}"
            raise ValueError(msg)
        seen.add(record.host)


def _host_gate_status(*, host: HostName, records: HostManualRuns) -> dict[str, Any]:
    manual = next((record for record in records.manual_host_ui if record.host == host), None)
    replay = next((record for record in records.first_10_minutes_replay if record.host == host), None)
    manual_status = manual.status if manual else "missing"
    replay_status = replay.status if replay else "missing"
    overall_status = _overall_host_status(manual_status=manual_status, replay_status=replay_status)
    return {
        "overall_status": overall_status,
        "manual_host_ui": manual_status,
        "first_10_minutes_replay": replay_status,
        "missing_gates": [
            gate
            for gate, status in [("manual_host_ui", manual_status), ("first_10_minutes_replay", replay_status)]
            if status != "passed"
        ],
        "remediation_actions": _remediation_actions(host=host, overall_status=overall_status),
    }


def _overall_host_status(*, manual_status: str, replay_status: str) -> str:
    if manual_status == "passed" and replay_status == "passed":
        return "passed"
    if manual_status == "blocked" or replay_status == "blocked":
        return "blocked"
    return "missing"


def _operator_steps(host: HostName) -> list[dict[str, str]]:
    return [
        {
            "step": "connect_host",
            "action": f"Open {host} with the AlbumentationsX MCP server configured and visible.",
        },
        {
            "step": "smoke_check",
            "action": "Call run_host_smoke_check and continue only when preview_ready is true.",
        },
        {
            "step": "first_preview",
            "action": "Replay the first-10-minutes workflow and keep redacted artifact references.",
        },
        {
            "step": "record",
            "action": "Run import-artifacts only after the reviewer observed the real host UI session.",
        },
    ]


def _collect_wizard_steps(
    *,
    host: HostName,
    path: Path,
    run_date: str,
    reviewer: str,
    output_dir: Path,
    artifact_ref: str,
) -> list[dict[str, str | bool]]:
    host_arg = _quote_cli(host)
    output_arg = _quote_cli(str(output_dir))
    path_arg = _quote_cli(str(path))
    artifact_arg = _quote_cli(artifact_ref)
    reviewer_arg = _quote_cli(reviewer)
    return [
        {
            "code": "setup_probe",
            "writes_records": False,
            "command": f"albu-mcp host setup-probe --host {host_arg} --live --format json",
            "expected_result": "probe_status is passed or blocking checks are explicit.",
        },
        {
            "code": "host_smoke",
            "writes_records": False,
            "command": "run_host_smoke_check",
            "expected_result": "preview_ready=true in the real MCP host UI.",
        },
        {
            "code": "first_preview_replay",
            "writes_records": False,
            "command": "Follow docs/FIRST_10_MINUTES.md in the real MCP host UI.",
            "expected_result": "reviewer-observed first-preview replay artifact refs.",
        },
        {
            "code": "session_manifest",
            "writes_records": False,
            "command": (
                f"albu-mcp evidence session-manifest --host {host_arg} --date {run_date} "
                f"--reviewer {reviewer_arg} --output-dir {output_arg} --format json"
            ),
            "expected_result": "filled evidence session manifest with redacted artifact refs.",
        },
        {
            "code": "validate_manifest",
            "writes_records": False,
            "command": (
                f"albu-mcp evidence validate-manifest --input {output_arg}/{_host_slug(host)}-evidence-session-manifest.json "
                f"--path {path_arg} --format json"
            ),
            "expected_result": "validation_status is ready_to_import.",
        },
        {
            "code": "import_artifacts",
            "writes_records": True,
            "command": (
                f"albu-mcp evidence import-artifacts --host {host_arg} --status passed --date {run_date} "
                f"--evidence 'reviewer observed real MCP host UI and first-10-minutes replay' "
                f"--artifact {artifact_arg} --confirm-real-host-observed --path {path_arg}"
            ),
            "expected_result": "manual_host_ui and first_10_minutes_replay records are written.",
        },
        {
            "code": "privacy_doctor",
            "writes_records": False,
            "command": f"albu-mcp evidence privacy-doctor --path {path_arg} --format json",
            "expected_result": "privacy_status is ready.",
        },
        {
            "code": "rc_go_check",
            "writes_records": False,
            "command": "albu-mcp rc go-check --format json",
            "expected_result": "go_decision reflects current real evidence and beta records.",
        },
    ]


def _quote_cli(value: str) -> str:
    return shlex.quote(value)


def _session_manifest_commands(host: HostName) -> list[str]:
    return [
        "run_host_smoke_check",
        "render_preview_batch",
        f"albu-mcp evidence import-checklist --host {host!r} --format markdown",
        "albu-mcp evidence validate-manifest --input evidence-session-manifest.json --format json",
    ]


def _remediation_actions(*, host: HostName, overall_status: str) -> list[dict[str, str]]:
    if overall_status == "passed":
        return []
    actions = {
        "Codex": [
            {
                "code": "run_codex_visible_tool_approval",
                "message": "Run Codex with visible MCP tool approval and complete run_host_smoke_check.",
            }
        ],
        "Claude Code": [
            {
                "code": "install_or_expose_claude_cli",
                "message": "Install or expose the Claude Code CLI, then import the AlbumentationsX MCP config.",
            }
        ],
        "Cursor": [
            {
                "code": "refresh_cursor_mcp_tools",
                "message": "Refresh Cursor MCP server discovery before running the preview smoke path.",
            }
        ],
        "Claude Desktop": [
            {
                "code": "refresh_claude_desktop_config",
                "message": "Reload Claude Desktop MCP config and confirm AlbumentationsX tools are listed.",
            }
        ],
    }
    return actions[host]


def _host_setup_steps(host: HostName) -> list[dict[str, str]]:
    host_steps = {
        "Codex": [
            {
                "code": "run_codex_visible_tool_approval",
                "message": "Open Codex with visible MCP tool approval and the AlbumentationsX server configured.",
            }
        ],
        "Claude Code": [
            {
                "code": "install_or_expose_claude_cli",
                "message": "Install or expose the Claude Code CLI, then import the AlbumentationsX MCP config.",
            }
        ],
        "Cursor": [
            {
                "code": "refresh_cursor_mcp_tools",
                "message": "Refresh Cursor MCP tools and confirm the AlbumentationsX server is enabled.",
            }
        ],
        "Claude Desktop": [
            {
                "code": "refresh_claude_desktop_config",
                "message": "Reload Claude Desktop MCP config and confirm AlbumentationsX tools are listed.",
            }
        ],
    }
    return host_steps[host]


def _expected_mcp_tools() -> list[str]:
    return [
        "run_host_smoke_check",
        "plan_dataset_onboarding",
        "validate_preview_request",
        "render_preview_batch",
        "compare_preview_runs",
        "plan_preview_review",
    ]


def _render_evidence_operator_packet_markdown(packet: dict[str, Any]) -> str:
    host = packet["host"]
    setup_steps = "\n".join(f"- `{step['code']}`: {step['message']}" for step in packet["host_setup_steps"])
    expected_tools = "\n".join(f"- `{tool}`" for tool in packet["expected_tools"])
    artifact_checklist = "\n".join(f"- `{item}`" for item in packet["artifact_checklist"])
    next_actions = "\n".join(f"- {item}" for item in packet["next_actions"])
    missing_gates = "\n".join(f"- `{gate}`" for gate in packet["current_host_status"]["missing_gates"]) or "- none"
    return (
        f"# {host} Evidence Operator Packet\n\n"
        f"Packet status: `{packet['packet_status']}`\n\n"
        f"Records path: `{packet['records_path']}`\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{packet['non_fabrication_policy']}\n\n"
        "## Current Host Status\n\n"
        f"- Overall: `{packet['current_host_status']['overall_status']}`\n"
        f"- Manual host UI: `{packet['current_host_status']['manual_host_ui']}`\n"
        f"- First 10 minutes replay: `{packet['current_host_status']['first_10_minutes_replay']}`\n"
        f"- Missing gates:\n{missing_gates}\n\n"
        "## Host Setup\n\n"
        f"{setup_steps}\n\n"
        "## Smoke Call\n\n"
        f"- Tool: `{packet['smoke_call']['tool']}`\n"
        f"- Required result: `{packet['smoke_call']['required_result']}`\n"
        f"- Failure next tool: `{packet['smoke_call']['failure_next_tool']}`\n\n"
        "## Expected MCP Tools\n\n"
        f"{expected_tools}\n\n"
        "## Artifact Checklist\n\n"
        f"{artifact_checklist}\n\n"
        "## Recording Commands\n\n"
        "Passed evidence:\n\n"
        "```bash\n"
        f"{packet['recording_commands']['passed']}\n"
        "```\n\n"
        "Blocked evidence:\n\n"
        "```bash\n"
        f"{packet['recording_commands']['blocked']}\n"
        "```\n\n"
        "## Next Actions\n\n"
        f"{next_actions}\n"
    )


def _render_evidence_packet_bundle_markdown(
    *,
    path: Path,
    packet_artifacts: list[dict[str, str]],
) -> str:
    packet_links = "\n".join(f"- `{artifact['filename']}` for `{artifact['host']}`" for artifact in packet_artifacts)
    return (
        "# P0 Evidence Packet Bundle\n\n"
        f"Records path: `{path}`\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{_NON_FABRICATION_POLICY}\n\n"
        "## Included Packets\n\n"
        f"{packet_links}\n\n"
        "## Next Commands\n\n"
        "```bash\n"
        "albu-mcp evidence privacy-doctor --format json\n"
        "albu-mcp evidence import-checklist --host Codex --format markdown\n"
        "albu-mcp evidence import-checklist --host 'Claude Code' --format markdown\n"
        "```\n"
    )


def _host_slug(host: HostName) -> str:
    return host.lower().replace(" ", "-")


def _operator_packet_extension(output_format: OperatorPacketFormat) -> str:
    return "md" if output_format == "markdown" else "json"


def _artifact_doctor_issues(records: HostManualRuns) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    manual_by_host = {record.host: record for record in records.manual_host_ui}
    replay_by_host = {record.host: record for record in records.first_10_minutes_replay}
    for host in P0_REQUIRED_HOSTS:
        manual = manual_by_host.get(host)
        replay = replay_by_host.get(host)
        if manual is None or manual.status != "passed":
            issues.append(_artifact_issue(host=host, gate="manual_host_ui", code="missing_required_host_gate"))
        elif _looks_synthetic_only(manual.evidence):
            issues.append(_artifact_issue(host=host, gate="manual_host_ui", code="synthetic_only_evidence"))
        if replay is None or replay.status != "passed":
            issues.append(_artifact_issue(host=host, gate="first_10_minutes_replay", code="missing_required_host_gate"))
        else:
            if _looks_synthetic_only(replay.evidence):
                issues.append(
                    _artifact_issue(host=host, gate="first_10_minutes_replay", code="synthetic_only_evidence")
                )
            if not replay.artifacts:
                issues.append(
                    _artifact_issue(host=host, gate="first_10_minutes_replay", code="missing_replay_artifact")
                )
    return issues


def _privacy_doctor_issues(records: HostManualRuns) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    manual_by_host = {record.host: record for record in records.manual_host_ui}
    replay_by_host = {record.host: record for record in records.first_10_minutes_replay}
    for host in P0_REQUIRED_HOSTS:
        manual = manual_by_host.get(host)
        replay = replay_by_host.get(host)
        if manual is None or manual.status != "passed":
            issues.append(_privacy_issue(host=host, gate="manual_host_ui", code="missing_required_host_gate"))
        elif _looks_synthetic_only(manual.evidence):
            issues.append(_privacy_issue(host=host, gate="manual_host_ui", code="synthetic_only_evidence"))
        if replay is None or replay.status != "passed":
            issues.append(_privacy_issue(host=host, gate="first_10_minutes_replay", code="missing_required_host_gate"))
            continue
        if _looks_synthetic_only(replay.evidence):
            issues.append(_privacy_issue(host=host, gate="first_10_minutes_replay", code="synthetic_only_evidence"))
        if not replay.artifacts:
            issues.append(_privacy_issue(host=host, gate="first_10_minutes_replay", code="missing_replay_artifact"))
        issues.extend(
            [
                _privacy_issue(
                    host=host,
                    gate="first_10_minutes_replay",
                    code="private_local_artifact_ref",
                    artifact_ref=artifact_ref,
                )
                for artifact_ref in replay.artifacts
                if _looks_private_artifact_ref(artifact_ref)
            ]
        )
    return issues


def _artifact_issue(*, host: HostName, gate: str, code: str) -> dict[str, str]:
    messages = {
        "missing_required_host_gate": "Required P0 host gate is not passed.",
        "synthetic_only_evidence": "Evidence text looks synthetic-only or explicitly lacks reviewer observation.",
        "missing_replay_artifact": "First-10-minutes replay needs at least one redacted artifact reference.",
    }
    return {"host": host, "gate": gate, "code": code, "message": messages[code]}


def _privacy_issue(*, host: HostName, gate: str, code: str, artifact_ref: str | None = None) -> dict[str, str]:
    messages = {
        "missing_required_host_gate": "Required P0 host gate is not passed.",
        "synthetic_only_evidence": "Evidence text looks synthetic-only or explicitly lacks reviewer observation.",
        "missing_replay_artifact": "First-10-minutes replay needs at least one redacted artifact reference.",
        "private_local_artifact_ref": "Artifact reference looks like a private local path or file URL.",
    }
    issue = {"host": host, "gate": gate, "code": code, "message": messages[code]}
    if artifact_ref is not None:
        issue["artifact_ref"] = artifact_ref
    return issue


def _looks_synthetic_only(evidence: str) -> bool:
    lowered = evidence.lower()
    return any(marker in lowered for marker in _SYNTHETIC_ONLY_MARKERS)


def _looks_private_artifact_ref(artifact_ref: str) -> bool:
    lowered = artifact_ref.lower()
    private_prefixes = (
        "/users/",
        "/home/",
        "/private/",
        "file://",
    )
    return lowered.startswith(private_prefixes) or lowered[1:3] == ":\\"


def _passed_gate_count(records: HostManualRuns) -> int:
    manual_hosts = {
        record.host
        for record in records.manual_host_ui
        if record.host in P0_REQUIRED_HOSTS and record.status == "passed"
    }
    replay_hosts = {
        record.host
        for record in records.first_10_minutes_replay
        if record.host in P0_REQUIRED_HOSTS and record.status == "passed"
    }
    return len(manual_hosts) + len(replay_hosts)


def _artifact_doctor_next_actions(issues: list[dict[str, str]]) -> list[str]:
    codes = {issue["code"] for issue in issues}
    if not issues:
        return ["Run albu-mcp trust next --format json before attempting RC reopen."]
    actions: list[str] = []
    if "synthetic_only_evidence" in codes:
        actions.append("Replace synthetic-only notes with reviewer-observed real host UI evidence.")
    if "missing_replay_artifact" in codes:
        actions.append("Attach at least one redacted first-10-minutes replay artifact reference.")
    if "missing_required_host_gate" in codes:
        actions.append("Run albu-mcp evidence execution-packet for each missing host gate.")
    return actions


def _privacy_doctor_next_actions(issues: list[dict[str, str]]) -> list[str]:
    if not issues:
        return ["Run albu-mcp rc candidate-packet --format markdown before release-owner review."]
    codes = {issue["code"] for issue in issues}
    actions = ["Run albu-mcp evidence import-checklist for each blocked P0 host."]
    if "private_local_artifact_ref" in codes:
        actions.append(
            "Replace private local artifact refs with redacted docs, artifact://, or public-safe references."
        )
    if "synthetic_only_evidence" in codes:
        actions.append("Replace synthetic-only notes with reviewer-observed real host UI evidence.")
    if "missing_replay_artifact" in codes:
        actions.append("Attach at least one privacy-safe first-10-minutes replay artifact reference.")
    return actions


def _doctor_next_actions(summary: dict[str, int]) -> list[str]:
    if summary["passed_gate_count"] == summary["required_gate_count"]:
        return ["Run albu-mcp rc reopen --format json and review the publish decision."]
    return [
        "Run albu-mcp evidence run-session for each missing or blocked host.",
        "Record passed evidence only with --confirm-real-host-observed after a reviewer observes the real host UI.",
        "Rerun albu-mcp evidence doctor before attempting RC reopen.",
    ]


def _host_unblock_item(*, host: HostName, status: dict[str, Any]) -> dict[str, Any]:
    return {
        "host": host,
        "overall_status": status["overall_status"],
        "missing_gates": status["missing_gates"],
        "remediation_actions": status["remediation_actions"],
        "recommended_command": f"albu-mcp evidence run-session --host {host!r} --format json",
        "acceptance_command": (
            "albu-mcp evidence import-artifacts "
            f"--host {host!r} --status passed --date YYYY-MM-DD --evidence 'reviewer observed real host UI' "
            "--artifact docs/assets/demo/demo_report.md --confirm-real-host-observed"
        ),
    }


def _unblock_next_actions(host_unblock_queue: list[dict[str, Any]]) -> list[str]:
    if not host_unblock_queue:
        return ["Run albu-mcp rc reopen --format json and review report-only publish readiness."]
    return [
        "Run the first recommended_command in a real MCP host session.",
        "Capture redacted artifact references from the reviewer-observed host UI.",
        "Import passed evidence only with --confirm-real-host-observed, then rerun evidence doctor.",
    ]
