"""No-write operator execution pack for collecting real evidence inputs."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from albumentationsx_mcp.beta_validation import (
    build_beta_response_template_artifacts,
    load_beta_response_draft,
    validate_beta_response_draft,
)
from albumentationsx_mcp.evidence import (
    P0_REQUIRED_HOSTS,
    HostName,
    build_evidence_session_manifest_artifact,
    load_evidence_session_manifest,
    validate_evidence_session_manifest,
)

EvidenceExecutionPackFormat = Literal["markdown"]
EvidenceExecutionPackAuditFormat = Literal["json", "markdown"]
_BETA_RESPONSE_DIR = "beta-responses"
_REQUIRED_PACK_FILES = ("README.md", "session-plan.md", "operator-checklist.md", "post-session-commands.md")
_REQUIRED_BETA_RESPONSE_FILENAMES = (
    "dataset-health-before-training-beta-response.json",
    "noisy-preview-tuning-beta-response.json",
    "robustness-distortion-variants-beta-response.json",
)


@dataclass(frozen=True)
class EvidenceExecutionPackRequest:
    """Inputs for one no-write real evidence execution pack."""

    run_date: str
    reviewer: str
    output_dir: Path
    hosts: tuple[HostName, ...] = P0_REQUIRED_HOSTS
    output_format: EvidenceExecutionPackFormat = "markdown"
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")


@dataclass(frozen=True)
class EvidenceExecutionPackAuditRequest:
    """Inputs for auditing one generated execution pack without writing records."""

    input_dir: Path
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")


def build_evidence_execution_pack_artifacts(request: EvidenceExecutionPackRequest) -> dict[str, Any]:
    """Build a no-write folder of operator artifacts for real host and beta capture."""
    if request.output_format != "markdown":
        msg = f"unsupported evidence execution-pack format: {request.output_format}"
        raise ValueError(msg)

    hosts = request.hosts or P0_REQUIRED_HOSTS
    host_manifests = [
        build_evidence_session_manifest_artifact(host=host, run_date=request.run_date, reviewer=request.reviewer)
        for host in hosts
    ]
    beta_templates = build_beta_response_template_artifacts(attempt_date=request.run_date)
    manifest_filenames = [artifact["filename"] for artifact in host_manifests]
    beta_filenames = [f"{_BETA_RESPONSE_DIR}/{artifact['filename']}" for artifact in beta_templates]
    artifacts = [
        {
            "filename": "README.md",
            "content": _render_readme(
                request=request,
                hosts=hosts,
                manifest_filenames=manifest_filenames,
                beta_filenames=beta_filenames,
            ),
        },
        {
            "filename": "session-plan.md",
            "content": _render_session_plan(request=request, hosts=hosts),
        },
        {
            "filename": "operator-checklist.md",
            "content": _render_operator_checklist(request=request, hosts=hosts),
        },
        {
            "filename": "post-session-commands.md",
            "content": _render_post_session_commands(
                request=request,
                manifest_filenames=manifest_filenames,
                beta_filenames=beta_filenames,
            ),
        },
        *host_manifests,
        *[
            {
                "filename": f"{_BETA_RESPONSE_DIR}/{artifact['filename']}",
                "content": artifact["content"],
            }
            for artifact in beta_templates
        ],
    ]
    return {
        "pack_status": "ready_for_real_session",
        "writes_records": False,
        "output_format": request.output_format,
        "output_dir": str(request.output_dir),
        "host_count": len(hosts),
        "beta_draft_count": len(beta_templates),
        "artifact_count": len(artifacts),
        "hosts": list(hosts),
        "artifacts": artifacts,
        "next_action": "run_real_host_and_beta_session_then_validate_inputs",
    }


def build_evidence_execution_pack_audit(request: EvidenceExecutionPackAuditRequest) -> dict[str, Any]:
    """Audit one generated execution pack folder without recording evidence."""
    missing_files, blocking_reasons = _pack_missing_files(request.input_dir)
    host_manifests, host_blockers = _audit_host_manifests(request)
    beta_drafts, beta_blockers = _audit_beta_drafts(request.input_dir)
    command_blockers = _audit_post_session_commands(request.input_dir)
    blocking_reasons.extend([*host_blockers, *beta_blockers, *command_blockers])

    audit_status = _execution_pack_audit_status(
        blocking_reasons=blocking_reasons,
        host_manifests=host_manifests,
        beta_drafts=beta_drafts,
    )
    return {
        "audit_status": audit_status,
        "writes_records": False,
        "input_dir": str(request.input_dir),
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "missing_files": missing_files,
        "blocking_reasons": blocking_reasons,
        "host_manifest_count": len(host_manifests),
        "beta_draft_count": len(beta_drafts),
        "host_manifests": host_manifests,
        "beta_drafts": beta_drafts,
        "next_commands": _execution_pack_audit_next_commands(
            request=request,
            audit_status=audit_status,
            host_manifests=host_manifests,
        ),
        "non_fabrication_policy": (
            "Execution pack audit is report-only. It checks generated operator files and validation readiness "
            "without writing evidence records or treating templates as real host or beta evidence."
        ),
    }


def render_evidence_execution_pack_audit_json(report: dict[str, Any]) -> str:
    """Render an execution pack audit report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_evidence_execution_pack_audit_markdown(report: dict[str, Any]) -> str:
    """Render an execution pack audit report as Markdown."""
    blockers = "\n".join(f"- `{reason}`" for reason in report["blocking_reasons"]) or "- none"
    missing = "\n".join(f"- `{path}`" for path in report["missing_files"]) or "- none"
    hosts = (
        "\n".join(
            f"- `{item['path']}`: `{item['validation_status']}` (`{item['manifest_status']}`)"
            for item in report["host_manifests"]
        )
        or "- none"
    )
    beta = (
        "\n".join(
            f"- `{item['path']}`: `{item['validation_status']}` (`{item['workflow_id']}`)"
            for item in report["beta_drafts"]
        )
        or "- none"
    )
    commands = "\n".join(f"- `{command}`" for command in report["next_commands"]) or "- none"
    return (
        "# Evidence Execution Pack Audit\n\n"
        f"Audit status: `{report['audit_status']}`  \n"
        f"Writes records: `{str(report['writes_records']).lower()}`  \n"
        f"Input dir: `{report['input_dir']}`\n\n"
        "## Missing Files\n\n"
        f"{missing}\n\n"
        "## Blocking Reasons\n\n"
        f"{blockers}\n\n"
        "## Host Manifests\n\n"
        f"{hosts}\n\n"
        "## Beta Drafts\n\n"
        f"{beta}\n\n"
        "## Next Commands\n\n"
        f"{commands}\n"
    )


def _render_readme(
    *,
    request: EvidenceExecutionPackRequest,
    hosts: tuple[HostName, ...],
    manifest_filenames: list[str],
    beta_filenames: list[str],
) -> str:
    filenames = [
        "README.md",
        "session-plan.md",
        "operator-checklist.md",
        "post-session-commands.md",
        *manifest_filenames,
        *beta_filenames,
    ]
    file_list = "\n".join(f"- `{filename}`" for filename in filenames)
    host_list = ", ".join(hosts)
    return (
        "# Evidence Execution Pack\n\n"
        "Generated execution packs are not evidence. They are private operator workspace files for collecting "
        "reviewer-observed host evidence and privacy-safe beta responses.\n\n"
        f"- run_date: `{request.run_date}`\n"
        f"- reviewer: `{request.reviewer}`\n"
        f"- hosts: `{host_list}`\n"
        "- writes_records: `false`\n"
        "- import policy: fill, validate, review, then run the explicit import command in "
        "`post-session-commands.md`.\n\n"
        "## Files\n\n"
        f"{file_list}\n\n"
        "## Evidence Boundary\n\n"
        "Only manually filled manifests and beta responses that pass validation can be imported as real evidence. "
        "Do not commit private screenshots, full host logs, local paths, dataset contents, credentials, "
        "or raw user data.\n"
    )


def _render_session_plan(*, request: EvidenceExecutionPackRequest, hosts: tuple[HostName, ...]) -> str:
    host_sections = "\n".join(_render_host_session_section(host) for host in hosts)
    return (
        "# Real Evidence Session Plan\n\n"
        f"Date: `{request.run_date}`  \n"
        f"Reviewer: `{request.reviewer}`\n\n"
        "Run this plan in a real MCP host session. Keep outputs redacted and bounded to local review artifacts.\n\n"
        f"{host_sections}\n"
        "## Beta Response Capture\n\n"
        "After the host run, collect privacy-safe participant summaries in every file under `beta-responses/`. "
        "Replace placeholder summaries with concrete outcomes, keep `private_data_included` false, and reference only "
        "redacted artifacts.\n"
    )


def _render_host_session_section(host: HostName) -> str:
    return (
        f"## {host}\n\n"
        "1. Open the host with AlbumentationsX MCP configured from the published package.\n"
        "2. Read `albumentationsx://examples/client-smoke`.\n"
        "3. Call `run_host_smoke_check` and continue only when `preview_ready` is true.\n"
        "4. Run a small bounded preview flow with `validate_preview_request`, `render_preview_batch`, "
        "and a contact sheet.\n"
        "5. Capture redacted reviewer notes in this host's `*-evidence-session-manifest.json`.\n"
        "6. Leave `manifest_status` as `template` until the reviewer has observed the real host UI; set it to `filled` "
        "only after the run is complete and redacted.\n"
    )


def _render_operator_checklist(*, request: EvidenceExecutionPackRequest, hosts: tuple[HostName, ...]) -> str:
    host_items = "\n".join(f"- `{host}` manifest was filled after direct reviewer observation." for host in hosts)
    return (
        "# Operator Checklist\n\n"
        f"- Run date is `{request.run_date}` and reviewer is `{request.reviewer}`.\n"
        f"{host_items}\n"
        "- `confirm_real_host_observed` is true only for real host UI evidence.\n"
        "- `private_data_included` remains false for every manifest and beta response.\n"
        "- Evidence summaries mention concrete observed actions, not generated smoke output alone.\n"
        "- Artifact references are redacted, relative, and safe to share.\n"
        "- No credentials, full logs, raw screenshots, private paths, filenames, labels, or dataset contents "
        "are copied.\n"
        "- Run the validation commands before any import command.\n"
    )


def _render_post_session_commands(
    *,
    request: EvidenceExecutionPackRequest,
    manifest_filenames: list[str],
    beta_filenames: list[str],
) -> str:
    manifest_paths = [_quote_path(request.output_dir / filename) for filename in manifest_filenames]
    beta_paths = [_quote_path(request.output_dir / filename) for filename in beta_filenames]
    beta_dir = _quote_path(request.output_dir / _BETA_RESPONSE_DIR)
    host_records_path = _quote_path(request.host_records_path)
    beta_records_path = _quote_path(request.beta_records_path)
    preflight_path = _quote_path(request.output_dir / "preflight.md")
    import_wizard_path = _quote_path(request.output_dir / "import-wizard.md")
    host_args = " ".join(f"--host-manifest {path}" for path in manifest_paths)
    validate_manifest_commands = "\n".join(
        f"- `albu-mcp evidence validate-manifest --input {path} --path {host_records_path} --format json`"
        for path in manifest_paths
    )
    validate_beta_commands = "\n".join(
        f"- `albu-mcp beta response-validate --input {path} --format json`" for path in beta_paths
    )
    import_wizard_base = (
        f"albu-mcp evidence import-wizard {host_args} --beta-dir {beta_dir} "
        f"--host-records {host_records_path} --beta-records {beta_records_path}"
    )
    return (
        "# Post-Session Commands\n\n"
        "Run these only after the real session artifacts are manually filled and reviewed.\n\n"
        "## Validate Host Manifests\n\n"
        f"{validate_manifest_commands}\n\n"
        "## Validate Beta Responses\n\n"
        f"{validate_beta_commands}\n\n"
        "## Preflight\n\n"
        f"- `{import_wizard_base.replace('import-wizard', 'preflight')} --format markdown "
        f"--output {preflight_path}`\n\n"
        "## Import Wizard\n\n"
        f"- `{import_wizard_base} --format markdown --output {import_wizard_path}`\n"
        f"- `{import_wizard_base} --import-ready --format json`\n\n"
        "The `--import-ready` command writes records. Run it only when the wizard reports ready-to-import inputs "
        "and the reviewer approves the import.\n"
    )


def _quote_path(path: Path) -> str:
    return shlex.quote(str(path))


def _pack_missing_files(input_dir: Path) -> tuple[list[str], list[str]]:
    missing_files: list[str] = []
    blocking_reasons: list[str] = []
    for filename in _REQUIRED_PACK_FILES:
        if not (input_dir / filename).exists():
            missing_files.append(filename)
            blocking_reasons.append(f"missing_pack_file:{filename}")

    beta_dir = input_dir / _BETA_RESPONSE_DIR
    if not beta_dir.exists():
        missing_files.append(_BETA_RESPONSE_DIR)
        blocking_reasons.append(f"missing_pack_dir:{_BETA_RESPONSE_DIR}")
        return missing_files, blocking_reasons

    for filename in _REQUIRED_BETA_RESPONSE_FILENAMES:
        if not (beta_dir / filename).exists():
            missing_files.append(f"{_BETA_RESPONSE_DIR}/{filename}")
            blocking_reasons.append(f"missing_beta_response:{filename}")
    return missing_files, blocking_reasons


def _audit_host_manifests(request: EvidenceExecutionPackAuditRequest) -> tuple[list[dict[str, Any]], list[str]]:
    manifest_paths = sorted(request.input_dir.glob("*-evidence-session-manifest.json"))
    if not manifest_paths:
        return [], ["missing_host_manifest"]

    blockers: list[str] = []
    audited: list[dict[str, Any]] = []
    for path in manifest_paths:
        try:
            manifest = load_evidence_session_manifest(path)
            validation = validate_evidence_session_manifest(manifest=manifest, records_path=request.host_records_path)
        except ValueError as exc:
            blockers.append(f"invalid_host_manifest:{path.name}")
            audited.append(
                {
                    "path": str(path),
                    "status": "blocked",
                    "validation_status": "invalid",
                    "manifest_status": "invalid",
                    "error": str(exc),
                }
            )
            continue
        audited.append(
            {
                "path": str(path),
                "host": manifest.host,
                "status": validation["validation_status"],
                "validation_status": validation["validation_status"],
                "manifest_status": manifest.manifest_status,
                "confirm_real_host_observed": manifest.confirm_real_host_observed,
            }
        )
    return audited, blockers


def _audit_beta_drafts(input_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    blockers: list[str] = []
    audited: list[dict[str, Any]] = []
    for filename in _REQUIRED_BETA_RESPONSE_FILENAMES:
        path = input_dir / _BETA_RESPONSE_DIR / filename
        if not path.exists():
            continue
        try:
            draft = load_beta_response_draft(path)
            validation = validate_beta_response_draft(draft)
        except ValueError as exc:
            blockers.append(f"invalid_beta_response:{filename}")
            audited.append(
                {
                    "path": str(path),
                    "workflow_id": "invalid",
                    "status": "blocked",
                    "validation_status": "invalid",
                    "error": str(exc),
                }
            )
            continue
        audited.append(
            {
                "path": str(path),
                "workflow_id": draft.workflow_id,
                "status": validation["validation_status"],
                "validation_status": validation["validation_status"],
                "private_data_included": draft.private_data_included,
            }
        )
    return audited, blockers


def _audit_post_session_commands(input_dir: Path) -> list[str]:
    path = input_dir / "post-session-commands.md"
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    blockers: list[str] = []
    if "docs/beta-response-templates" in content:
        blockers.append("unsafe_post_session_command:committed_beta_template_dir")
    if str(input_dir / _BETA_RESPONSE_DIR) not in content and f"{_BETA_RESPONSE_DIR}" not in content:
        blockers.append("unsafe_post_session_command:missing_session_beta_dir")
    return blockers


def _execution_pack_audit_status(
    *,
    blocking_reasons: list[str],
    host_manifests: list[dict[str, Any]],
    beta_drafts: list[dict[str, Any]],
) -> str:
    if blocking_reasons:
        return "blocked"
    ready_hosts = all(item["validation_status"] == "ready_to_import" for item in host_manifests)
    ready_beta = all(item["validation_status"] == "ready_to_import" for item in beta_drafts)
    if ready_hosts and ready_beta:
        return "ready_for_import_review"
    return "ready_for_real_session"


def _execution_pack_audit_next_commands(
    *,
    request: EvidenceExecutionPackAuditRequest,
    audit_status: str,
    host_manifests: list[dict[str, Any]],
) -> list[str]:
    if audit_status == "blocked":
        return [
            "Fix missing or invalid pack files, then rerun execution-pack-audit.",
            "Regenerate the pack with albu-mcp evidence execution-pack if structure is incomplete.",
        ]
    host_args = " ".join(f"--host-manifest {_quote_path(Path(item['path']))}" for item in host_manifests)
    import_wizard_command = (
        f"albu-mcp evidence import-wizard {host_args} --beta-dir {_quote_path(request.input_dir / _BETA_RESPONSE_DIR)} "
        f"--host-records {_quote_path(request.host_records_path)} "
        f"--beta-records {_quote_path(request.beta_records_path)} "
        f"--format markdown --output {_quote_path(request.input_dir / 'import-wizard.md')}"
    )
    if audit_status == "ready_for_import_review":
        return [
            import_wizard_command,
            f"{import_wizard_command.replace('--format markdown', '--import-ready --format json')}",
        ]
    return [
        f"Open {_quote_path(request.input_dir / 'session-plan.md')} and run the real host session.",
        f"Fill manifests and beta responses under {_quote_path(request.input_dir)}.",
        "Rerun albu-mcp evidence execution-pack-audit after the session.",
        import_wizard_command,
    ]
