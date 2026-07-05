"""Artifact-only snapshot before importing post-fix outcome evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from albumentationsx_mcp.beta_validation import validate_beta_validation_records
from albumentationsx_mcp.evidence import HostName
from albumentationsx_mcp.product_fix_outcome_rehearsal import (
    ProductFixOutcomeRehearsalRequest,
    build_product_fix_outcome_rehearsal,
)

_SNAPSHOT_FILENAME = "before-beta-validation-records.json"


@dataclass(frozen=True)
class ProductFixClosureSnapshotRequest:
    """Inputs for building a pre-import product fix closure snapshot."""

    host: HostName
    input_path: Path
    host_records_path: Path = Path("docs/HOST_MANUAL_RUNS.json")
    beta_records_path: Path = Path("docs/BETA_VALIDATION_RECORDS.json")
    snapshot_dir: Path = Path("docs/product-fix-closure-snapshot")
    closure_output_dir: Path = Path("docs/product-fix-closure-pack")
    release_tag: str = "v1.15.0-rc.1"


def build_product_fix_closure_snapshot(request: ProductFixClosureSnapshotRequest) -> dict[str, Any]:
    """Build a pre-import snapshot report without importing the post-fix draft."""
    rehearsal = build_product_fix_outcome_rehearsal(
        ProductFixOutcomeRehearsalRequest(
            host=request.host,
            input_path=request.input_path,
            host_records_path=request.host_records_path,
            beta_records_path=request.beta_records_path,
            release_tag=request.release_tag,
        )
    )
    snapshot_path = request.snapshot_dir / _SNAPSHOT_FILENAME
    records = validate_beta_validation_records(request.beta_records_path)
    snapshot_payload = records.model_dump(mode="json")
    if rehearsal["rehearsal_status"] != "ready_for_guarded_import":
        return {
            "snapshot_status": rehearsal["rehearsal_status"],
            "writes_records": False,
            "writes_snapshot": False,
            "import_allowed": False,
            "blocked_reasons": rehearsal["stop_conditions"],
            "selected_fix": rehearsal["selected_fix"],
            "input_path": str(request.input_path),
            "snapshot_path": str(snapshot_path),
            "snapshot_payload": None,
            "import_command": None,
            "closure_command": None,
            "source_rehearsal": rehearsal,
            "release_tag": request.release_tag,
            "host": request.host,
            "host_records_path": str(request.host_records_path),
            "beta_records_path": str(request.beta_records_path),
            "next_commands": rehearsal["next_commands"],
            "non_fabrication_policy": _non_fabrication_policy(),
        }

    import_command = f"albu-mcp beta response-import --input {request.input_path} --path {request.beta_records_path}"
    closure_command = (
        f"albu-mcp activation product-fix-closure-pack --host {request.host} "
        f"--before-beta-records {snapshot_path} --beta-records {request.beta_records_path} "
        f"--output-dir {request.closure_output_dir} --format markdown"
    )
    return {
        "snapshot_status": "ready_for_import",
        "writes_records": False,
        "writes_snapshot": True,
        "import_allowed": True,
        "blocked_reasons": [],
        "selected_fix": rehearsal["selected_fix"],
        "input_path": str(request.input_path),
        "snapshot_path": str(snapshot_path),
        "snapshot_payload": snapshot_payload,
        "import_command": import_command,
        "closure_command": closure_command,
        "source_rehearsal": rehearsal,
        "release_tag": request.release_tag,
        "host": request.host,
        "host_records_path": str(request.host_records_path),
        "beta_records_path": str(request.beta_records_path),
        "next_commands": [import_command, closure_command],
        "non_fabrication_policy": _non_fabrication_policy(),
    }


def build_product_fix_closure_snapshot_artifacts(
    request: ProductFixClosureSnapshotRequest,
    *,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Build artifact-only pre-import snapshot files."""
    report = build_product_fix_closure_snapshot(request)
    artifacts = [
        _snapshot_index_artifact(report=report, output_format=output_format),
        _commands_artifact(report=report, output_format=output_format),
    ]
    if report["writes_snapshot"]:
        artifacts.insert(0, _before_snapshot_artifact(report=report))
    return {
        "pack_status": report["snapshot_status"],
        "writes_records": False,
        "writes_snapshot": report["writes_snapshot"],
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def render_product_fix_closure_snapshot_json(report: dict[str, Any]) -> str:
    """Render a product fix closure snapshot report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_product_fix_closure_snapshot_markdown(report: dict[str, Any]) -> str:
    """Render a product fix closure snapshot report as Markdown."""
    return (
        "# Product Fix Closure Snapshot\n\n"
        f"Snapshot status: `{report['snapshot_status']}`\n\n"
        f"Snapshot path: `{report['snapshot_path']}`\n\n"
        f"Import allowed: `{str(report['import_allowed']).lower()}`\n\n"
        f"Writes records: `{str(report['writes_records']).lower()}`\n\n"
        f"Writes snapshot: `{str(report['writes_snapshot']).lower()}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(report['blocked_reasons'], code=True)}\n\n"
        "## Commands\n\n"
        f"{_render_list(report['next_commands'], code=True)}\n"
    )


def _before_snapshot_artifact(*, report: dict[str, Any]) -> dict[str, str]:
    return {
        "filename": _SNAPSHOT_FILENAME,
        "content": json.dumps(report["snapshot_payload"], indent=2, sort_keys=True) + "\n",
    }


def _snapshot_index_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "product_fix_closure_snapshot_index",
        "snapshot_status": report["snapshot_status"],
        "snapshot_path": report["snapshot_path"],
        "import_allowed": report["import_allowed"],
        "writes_records": False,
        "writes_snapshot": report["writes_snapshot"],
        "blocked_reasons": report["blocked_reasons"],
        "selected_fix": report["selected_fix"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"product-fix-closure-snapshot-index.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_index_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _commands_artifact(*, report: dict[str, Any], output_format: str) -> dict[str, str]:
    payload = {
        "artifact": "import_and_closure_commands",
        "snapshot_status": report["snapshot_status"],
        "writes_records": False,
        "writes_snapshot": report["writes_snapshot"],
        "import_command": report["import_command"],
        "closure_command": report["closure_command"],
        "next_commands": report["next_commands"],
    }
    return {
        "filename": f"import-and-closure-commands.{_artifact_extension(output_format)}",
        "content": _format_artifact_payload(
            payload=payload,
            markdown=_render_commands_artifact_markdown(payload),
            output_format=output_format,
        ),
    }


def _render_index_artifact_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Product Fix Closure Snapshot Index\n\n"
        f"Snapshot status: `{payload['snapshot_status']}`\n\n"
        f"Snapshot path: `{payload['snapshot_path']}`\n\n"
        f"Import allowed: `{str(payload['import_allowed']).lower()}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Writes snapshot: `{str(payload['writes_snapshot']).lower()}`\n\n"
        "## Blocked Reasons\n\n"
        f"{_render_list(payload['blocked_reasons'], code=True)}\n\n"
        "## Next Commands\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_commands_artifact_markdown(payload: dict[str, Any]) -> str:
    import_command = payload["import_command"] or "none"
    closure_command = payload["closure_command"] or "none"
    return (
        "# Import And Closure Commands\n\n"
        f"Snapshot status: `{payload['snapshot_status']}`\n\n"
        f"Writes records: `{str(payload['writes_records']).lower()}`\n\n"
        f"Writes snapshot: `{str(payload['writes_snapshot']).lower()}`\n\n"
        "## Import\n\n"
        f"- `{import_command}`\n\n"
        "## Closure\n\n"
        f"- `{closure_command}`\n\n"
        "## Full Sequence\n\n"
        f"{_render_list(payload['next_commands'], code=True)}\n"
    )


def _render_list(items: list[str], *, code: bool = False) -> str:
    if not items:
        return "- none"
    if code:
        return "\n".join(f"- `{item}`" for item in items)
    return "\n".join(f"- {item}" for item in items)


def _artifact_extension(output_format: str) -> str:
    if output_format == "markdown":
        return "md"
    if output_format == "json":
        return "json"
    msg = f"unsupported product fix closure snapshot artifact format: {output_format}"
    raise ValueError(msg)


def _format_artifact_payload(*, payload: dict[str, Any], markdown: str, output_format: str) -> str:
    if output_format == "markdown":
        return markdown
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    msg = f"unsupported product fix closure snapshot artifact format: {output_format}"
    raise ValueError(msg)


def _non_fabrication_policy() -> str:
    return (
        "The closure snapshot pack is artifact-only. It copies the current beta records before an explicit "
        "response-import command and never imports post-fix evidence by itself."
    )
