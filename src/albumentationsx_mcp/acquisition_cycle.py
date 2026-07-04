"""No-write real evidence and beta acquisition cycle helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import build_beta_validation_report, validate_beta_validation_records
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.evidence_proof import build_evidence_proof_status
from albumentationsx_mcp.proof_sprint import OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL


@dataclass(frozen=True)
class AcquisitionCycleRequest:
    """Inputs for a no-write real evidence and beta acquisition cycle."""

    host: HostName
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    release_tag: str = "v1.15.0-rc.1"


def build_acquisition_cycle(request: AcquisitionCycleRequest) -> dict[str, Any]:
    """Build one no-write acquisition cycle over real host and beta gates."""
    proof_status = build_evidence_proof_status(records_path=request.host_records_path)
    beta_report = build_beta_validation_report(validate_beta_validation_records(request.beta_records_path))
    lanes = [
        _real_evidence_acquisition_lane(request=request, proof_status=proof_status),
        _beta_acquisition_lane(beta_report=beta_report),
        _product_depth_gate_lane(),
    ]
    blocked = any(lane["status"].startswith("blocked") for lane in lanes)
    return {
        "cycle_status": "blocked" if blocked else "ready_for_product_depth",
        "writes_records": False,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "lane_count": len(lanes),
        "lanes": lanes,
        "next_action": "run_real_evidence_acquisition" if blocked else "run_product_depth_gate",
        "non_fabrication_policy": (
            "This cycle is report-only. Generated packets, templates, transcripts, and fixture output do not count "
            "as P0 host evidence or external beta validation."
        ),
    }


def build_acquisition_cycle_artifacts(
    request: AcquisitionCycleRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build no-write acquisition cycle artifacts for operators."""
    report = build_acquisition_cycle(request)
    artifacts = [
        _cycle_index_artifact(report=report, output_format=output_format),
        *[_cycle_lane_artifact(lane=lane, output_format=output_format) for lane in report["lanes"]],
    ]
    return {
        "pack_status": report["cycle_status"],
        "writes_records": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_acquisition_cycle_markdown(report: dict[str, Any]) -> str:
    """Render the acquisition cycle index as Markdown."""
    return _render_cycle_index_markdown(report)


def _real_evidence_acquisition_lane(
    *,
    request: AcquisitionCycleRequest,
    proof_status: dict[str, Any],
) -> dict[str, Any]:
    blocked = proof_status["status"] != "ready_for_rc_reopen"
    return {
        "id": "real_evidence_acquisition",
        "title": "Real evidence acquisition",
        "status": "blocked_until_real_host_evidence" if blocked else "ready_for_gate_transition",
        "writes_records": False,
        "host": request.host,
        "proof_status": proof_status["status"],
        "blocked_host_count": proof_status["blocked_host_count"],
        "next_commands": [
            "albu-mcp evidence transcript-template",
            "albu-mcp evidence proof-runner",
            "albu-mcp evidence import-manifest",
        ],
    }


def _beta_acquisition_lane(*, beta_report: dict[str, Any]) -> dict[str, Any]:
    blocked = not beta_report["product_depth_allowed"]
    return {
        "id": "beta_acquisition",
        "title": "Beta acquisition",
        "status": "blocked_until_beta_validation" if blocked else "ready_for_product_depth_gate",
        "writes_records": False,
        "summary": beta_report["summary"],
        "docs_link_label": "Official Albumentations MCP docs",
        "docs_link": OFFICIAL_ALBUMENTATIONS_MCP_DOCS_URL,
        "next_commands": [
            "albu-mcp beta loop-pack --output-dir docs/beta-loop --format markdown",
            "albu-mcp beta response-template --output-dir docs/beta-response-templates --format json",
            "albu-mcp beta response-import-dir --input-dir docs/beta-loop --format json",
        ],
    }


def _product_depth_gate_lane() -> dict[str, Any]:
    return {
        "id": "product_depth_gate",
        "title": "Product depth gate",
        "status": "blocked_until_external_gates",
        "implementation_allowed": False,
        "writes_records": False,
    }


def _cycle_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    return {
        "filename": f"acquisition-cycle-index.{_extension(output_format)}",
        "content": _json_dumps(report) if output_format == "json" else _render_cycle_index_markdown(report),
    }


def _cycle_lane_artifact(*, lane: dict[str, Any], output_format: str) -> dict[str, str]:
    return {
        "filename": f"{lane['id'].replace('_', '-')}.{_extension(output_format)}",
        "content": _json_dumps(lane) if output_format == "json" else _render_lane_markdown(lane),
    }


def _render_cycle_index_markdown(report: dict[str, Any]) -> str:
    lanes = "\n".join(
        f"- `{lane['id']}`: `{lane['status']}`; writes_records=`{str(lane['writes_records']).lower()}`"
        for lane in report["lanes"]
    )
    return (
        "# Real Evidence Beta Acquisition Cycle\n\n"
        f"Release tag: `{report['release_tag']}`\n\n"
        f"Host: `{report['host']}`\n\n"
        f"Cycle status: `{report['cycle_status']}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Next action: `{report['next_action']}`\n\n"
        "## Lanes\n\n"
        f"{lanes}\n\n"
        "## Non-Fabrication Policy\n\n"
        f"{report['non_fabrication_policy']}\n"
    )


def _render_lane_markdown(lane: dict[str, Any]) -> str:
    commands = "\n".join(f"- `{command}`" for command in lane.get("next_commands", [])) or "- none"
    summary = "\n".join(f"- `{key}`: `{value}`" for key, value in lane.get("summary", {}).items()) or "- none"
    docs = ""
    if "docs_link" in lane:
        docs = f"\n## Source\n\n- [{lane['docs_link_label']}]({lane['docs_link']})\n"
    return (
        f"# {lane['title']}\n\n"
        f"Lane id: `{lane['id']}`\n\n"
        f"Status: `{lane['status']}`\n\n"
        f"Writes records: `{str(lane['writes_records']).lower()}`\n\n"
        "## Summary\n\n"
        f"{summary}\n\n"
        "## Next Commands\n\n"
        f"{commands}\n"
        f"{docs}"
    )


def _extension(output_format: str) -> str:
    if output_format == "markdown":
        return "md"
    if output_format == "json":
        return "json"
    msg = f"unsupported acquisition cycle format: {output_format}"
    raise ValueError(msg)


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
