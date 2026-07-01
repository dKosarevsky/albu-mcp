"""Release-safe intake bundle assembly."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from albumentationsx_mcp.activation import build_manual_evidence_runbook, render_manual_evidence_runbook_markdown
from albumentationsx_mcp.beta_validation import build_beta_response_template_artifacts
from albumentationsx_mcp.evidence import (
    P0_REQUIRED_HOSTS,
    build_evidence_import_checklist,
    build_evidence_replay_fixture_pack_artifact,
    render_evidence_import_checklist_markdown,
)
from albumentationsx_mcp.rc_reopen import build_release_owner_packet, render_release_owner_packet_markdown

IntakeBundleFormat = Literal["markdown", "json"]

_INTAKE_NON_EVIDENCE_POLICY = (
    "Generated fixtures and packets are not P0 evidence. Passed evidence still requires reviewer-observed real MCP "
    "host UI output and redacted artifact references."
)


def build_intake_bundle_artifacts(
    *,
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json"),
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json"),
    release_tag: str = "v1.15.0-rc.1",
    output_format: IntakeBundleFormat = "markdown",
    participant_role: str = "ML practitioner",
) -> dict[str, Any]:
    """Build all artifacts needed for a manual evidence intake pass."""
    artifacts = [
        _manual_runbook_artifact(
            host_records_path=host_records_path,
            beta_records_path=beta_records_path,
            release_tag=release_tag,
            output_format=output_format,
        ),
        build_evidence_replay_fixture_pack_artifact(output_format=output_format),
        *_import_checklist_artifacts(path=host_records_path, output_format=output_format),
        *build_beta_response_template_artifacts(participant_role=participant_role),
        _release_owner_artifact(
            host_records_path=host_records_path,
            beta_records_path=beta_records_path,
            release_tag=release_tag,
            output_format=output_format,
        ),
    ]
    index = _bundle_index_artifact(
        artifacts=artifacts,
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
        output_format=output_format,
    )
    all_artifacts = [index, *artifacts]
    return {
        "bundle_status": "ready_to_run",
        "release_tag": release_tag,
        "artifact_count": len(all_artifacts),
        "non_evidence_policy": _INTAKE_NON_EVIDENCE_POLICY,
        "artifacts": all_artifacts,
    }


def _manual_runbook_artifact(
    *,
    host_records_path: Path,
    beta_records_path: Path,
    release_tag: str,
    output_format: IntakeBundleFormat,
) -> dict[str, str]:
    runbook = build_manual_evidence_runbook(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    content = (
        json.dumps(runbook, indent=2, sort_keys=True) + "\n"
        if output_format == "json"
        else render_manual_evidence_runbook_markdown(runbook)
    )
    return {"filename": f"manual-evidence-runbook.{_extension(output_format)}", "content": content}


def _import_checklist_artifacts(*, path: Path, output_format: IntakeBundleFormat) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    for host in P0_REQUIRED_HOSTS:
        checklist = build_evidence_import_checklist(host=host, path=path)
        content = (
            json.dumps(checklist, indent=2, sort_keys=True) + "\n"
            if output_format == "json"
            else render_evidence_import_checklist_markdown(checklist)
        )
        artifacts.append(
            {
                "filename": f"{host.lower().replace(' ', '-')}-evidence-import-checklist.{_extension(output_format)}",
                "content": content,
            }
        )
    return artifacts


def _release_owner_artifact(
    *,
    host_records_path: Path,
    beta_records_path: Path,
    release_tag: str,
    output_format: IntakeBundleFormat,
) -> dict[str, str]:
    packet = build_release_owner_packet(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    content = (
        json.dumps(packet, indent=2, sort_keys=True) + "\n"
        if output_format == "json"
        else render_release_owner_packet_markdown(packet)
    )
    return {"filename": f"release-owner-packet.{_extension(output_format)}", "content": content}


def _bundle_index_artifact(
    *,
    artifacts: list[dict[str, str]],
    host_records_path: Path,
    beta_records_path: Path,
    release_tag: str,
    output_format: IntakeBundleFormat,
) -> dict[str, str]:
    filename = f"intake-bundle-index.{_extension(output_format)}"
    payload = {
        "bundle_status": "ready_to_run",
        "release_tag": release_tag,
        "host_records_path": str(host_records_path),
        "beta_records_path": str(beta_records_path),
        "non_evidence_policy": _INTAKE_NON_EVIDENCE_POLICY,
        "artifact_files": [artifact["filename"] for artifact in artifacts],
    }
    content = (
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if output_format == "json"
        else _render_bundle_index_markdown(payload)
    )
    return {"filename": filename, "content": content}


def _render_bundle_index_markdown(payload: dict[str, Any]) -> str:
    artifact_files = "\n".join(f"- `{filename}`" for filename in payload["artifact_files"])
    return (
        "# Intake Bundle Index\n\n"
        f"Release tag: `{payload['release_tag']}`\n\n"
        f"Bundle status: `{payload['bundle_status']}`\n\n"
        "## Non-Evidence Policy\n\n"
        f"{payload['non_evidence_policy']}\n\n"
        "## Artifact Files\n\n"
        f"{artifact_files}\n"
    )


def _extension(output_format: IntakeBundleFormat) -> str:
    return "md" if output_format == "markdown" else "json"
