"""Release owner review pack assembly."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from albumentationsx_mcp.rc_reopen import (
    build_rc_candidate_packet,
    build_release_owner_packet,
    render_rc_candidate_packet_markdown,
    render_release_owner_packet_markdown,
)
from albumentationsx_mcp.trust import (
    build_trust_dashboard_report,
    build_trust_gate_transition_report,
    render_trust_dashboard_markdown,
    render_trust_gate_transition_markdown,
)

ReleaseReviewPackFormat = Literal["markdown", "json"]


@dataclass(frozen=True)
class ReleaseReviewPackRequest:
    """Inputs for one release owner review pack."""

    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    before_host_records_path: Path | None = None
    before_beta_records_path: Path | None = None
    release_tag: str = "v1.15.0-rc.1"
    output_format: ReleaseReviewPackFormat = "markdown"


def build_release_owner_review_pack_artifacts(request: ReleaseReviewPackRequest) -> dict[str, Any]:
    """Build release owner review artifacts without publishing or writing records."""
    artifacts = [
        _trust_dashboard_artifact(
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
            output_format=request.output_format,
        ),
        _gate_transition_artifact(request),
        _rc_candidate_artifact(
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
            output_format=request.output_format,
        ),
        _release_owner_artifact(
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
            output_format=request.output_format,
        ),
    ]
    index = _review_pack_index_artifact(
        artifacts=artifacts,
        release_tag=request.release_tag,
        output_format=request.output_format,
    )
    all_artifacts = [index, *artifacts]
    return {
        "pack_status": "ready_for_owner_review",
        "release_tag": request.release_tag,
        "artifact_count": len(all_artifacts),
        "execution_policy": "Report only; this review pack does not create tags, releases, uploads, or records.",
        "artifacts": all_artifacts,
    }


def _trust_dashboard_artifact(
    *,
    host_records_path: Path,
    beta_records_path: Path,
    release_tag: str,
    output_format: ReleaseReviewPackFormat,
) -> dict[str, str]:
    report = build_trust_dashboard_report(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    content = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if output_format == "json"
        else render_trust_dashboard_markdown(report)
    )
    return {"filename": f"trust-dashboard.{_extension(output_format)}", "content": content}


def _gate_transition_artifact(request: ReleaseReviewPackRequest) -> dict[str, str]:
    report = build_trust_gate_transition_report(
        before_host_records_path=request.before_host_records_path or request.host_records_path,
        before_beta_records_path=request.before_beta_records_path or request.beta_records_path,
        after_host_records_path=request.host_records_path,
        after_beta_records_path=request.beta_records_path,
        release_tag=request.release_tag,
    )
    content = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if request.output_format == "json"
        else render_trust_gate_transition_markdown(report)
    )
    return {"filename": f"trust-gate-transition.{_extension(request.output_format)}", "content": content}


def _rc_candidate_artifact(
    *,
    host_records_path: Path,
    beta_records_path: Path,
    release_tag: str,
    output_format: ReleaseReviewPackFormat,
) -> dict[str, str]:
    packet = build_rc_candidate_packet(
        host_records_path=host_records_path,
        beta_records_path=beta_records_path,
        release_tag=release_tag,
    )
    content = (
        json.dumps(packet, indent=2, sort_keys=True) + "\n"
        if output_format == "json"
        else render_rc_candidate_packet_markdown(packet)
    )
    return {"filename": f"rc-candidate-packet.{_extension(output_format)}", "content": content}


def _release_owner_artifact(
    *,
    host_records_path: Path,
    beta_records_path: Path,
    release_tag: str,
    output_format: ReleaseReviewPackFormat,
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


def _review_pack_index_artifact(
    *,
    artifacts: list[dict[str, str]],
    release_tag: str,
    output_format: ReleaseReviewPackFormat,
) -> dict[str, str]:
    payload = {
        "pack_status": "ready_for_owner_review",
        "release_tag": release_tag,
        "execution_policy": "Report only; this review pack does not create tags, releases, uploads, or records.",
        "artifact_files": [artifact["filename"] for artifact in artifacts],
    }
    content = (
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if output_format == "json"
        else _render_review_pack_index_markdown(payload)
    )
    return {"filename": f"release-owner-review-pack-index.{_extension(output_format)}", "content": content}


def _render_review_pack_index_markdown(payload: dict[str, Any]) -> str:
    artifact_files = "\n".join(f"- `{filename}`" for filename in payload["artifact_files"])
    return (
        "# Release Owner Review Pack\n\n"
        f"Release tag: `{payload['release_tag']}`\n\n"
        f"Pack status: `{payload['pack_status']}`\n\n"
        f"Execution policy: {payload['execution_policy']}\n\n"
        "## Artifact Files\n\n"
        f"{artifact_files}\n"
    )


def _extension(output_format: ReleaseReviewPackFormat) -> str:
    return "md" if output_format == "markdown" else "json"
