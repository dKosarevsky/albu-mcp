"""No-write operator execution pack for collecting real evidence inputs."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from albumentationsx_mcp.beta_validation import build_beta_response_template_artifacts
from albumentationsx_mcp.evidence import (
    P0_REQUIRED_HOSTS,
    HostName,
    build_evidence_session_manifest_artifact,
)

EvidenceExecutionPackFormat = Literal["markdown"]
_BETA_RESPONSE_DIR = "beta-responses"


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
