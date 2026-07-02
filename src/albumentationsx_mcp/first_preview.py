"""Report-only first-preview operator handoffs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_MCP_SEQUENCE = [
    {
        "tool": "run_host_smoke_check",
        "gate": "continue only when preview_ready=true",
        "purpose": "Confirm the host can see tools, resources, roots, and preview limits.",
    },
    {
        "tool": "plan_dataset_onboarding",
        "gate": "continue only when preview_ready=true",
        "purpose": "Inspect the local folder and generate a safe preview request template.",
    },
    {
        "tool": "build_review_packet",
        "gate": "continue only when recommended_next_tool=validate_preview_request",
        "purpose": "Create a compact first-preview handoff for the host.",
    },
    {
        "tool": "validate_preview_request",
        "gate": "continue only when valid=true",
        "purpose": "Validate paths, masks, annotations, variants, and local root boundaries before rendering.",
    },
    {
        "tool": "render_preview_batch",
        "gate": "render one small batch only",
        "purpose": "Create the first contact sheet after validation passes.",
    },
    {
        "tool": "compare_preview_runs",
        "gate": "run after a baseline and candidate exist",
        "purpose": "Compare readability, intensity, geometry, and artifact signals.",
    },
    {
        "tool": "plan_preview_review",
        "gate": "use concrete user feedback tags",
        "purpose": "Decide whether to accept, adjust, rerender, or export.",
    },
    {
        "tool": "export_pipeline",
        "gate": "export only after human acceptance",
        "purpose": "Write a reproducible AlbumentationsX pipeline after the review loop.",
    },
]


def build_first_preview_pack(
    *,
    dataset_path: Path,
    allowed_root: Path,
    artifact_root: Path,
    task: str = "classification",
    max_images: int = 8,
) -> dict[str, Any]:
    """Build a short first-preview handoff without rendering or writing artifacts."""
    dataset_resolved = dataset_path.expanduser().resolve()
    allowed_resolved = allowed_root.expanduser().resolve()
    artifact_resolved = artifact_root.expanduser().resolve()
    root_ok = _is_relative_to(dataset_resolved, allowed_resolved)
    dataset_ok = dataset_resolved.exists() and dataset_resolved.is_dir()
    return {
        "pack_status": "ready_to_run" if root_ok and dataset_ok else "blocked",
        "writes_records": False,
        "renders_images": False,
        "dataset_path": str(dataset_path),
        "task": task,
        "bounded_roots": {
            "allowed_root": str(allowed_root),
            "artifact_root": str(artifact_root),
            "dataset_inside_allowed_root": root_ok,
        },
        "dataset_check": {
            "exists": dataset_resolved.exists(),
            "is_dir": dataset_resolved.is_dir(),
            "max_images": max_images,
        },
        "host_instruction": _host_instruction(dataset_path=dataset_path, task=task, max_images=max_images),
        "mcp_sequence": [dict(step) for step in _MCP_SEQUENCE],
        "operator_notes": [
            "This command does not render images; it prepares the host-facing first-preview path.",
            "Keep max_images small until the first contact sheet is readable.",
            "Do not increase variants_per_image before inspecting the first contact sheet.",
            "Use concrete feedback tags before adjusting or exporting a pipeline.",
        ],
        "next_actions": _next_actions(root_ok=root_ok, dataset_ok=dataset_ok),
        "resolved_paths": {
            "dataset_path": str(dataset_resolved),
            "allowed_root": str(allowed_resolved),
            "artifact_root": str(artifact_resolved),
        },
    }


def render_first_preview_pack_markdown(pack: dict[str, Any]) -> str:
    """Render a first-preview handoff as Markdown."""
    sequence = "\n".join(
        f"{index}. `{step['tool']}`: {step['purpose']} Gate: `{step['gate']}`"
        for index, step in enumerate(pack["mcp_sequence"], start=1)
    )
    notes = "\n".join(f"- {note}" for note in pack["operator_notes"])
    next_actions = "\n".join(f"- {action}" for action in pack["next_actions"])
    return (
        "# First Preview Operator Pack\n\n"
        f"Pack status: `{pack['pack_status']}`\n\n"
        f"Writes records: `{str(pack['writes_records']).lower()}`\n\n"
        f"Renders images: `{str(pack['renders_images']).lower()}`\n\n"
        f"Dataset path: `{pack['dataset_path']}`\n\n"
        f"Task: `{pack['task']}`\n\n"
        "## Host Instruction\n\n"
        f"{pack['host_instruction']}\n\n"
        "## MCP Sequence\n\n"
        f"{sequence}\n\n"
        "## Operator Notes\n\n"
        f"{notes}\n\n"
        "## Next Actions\n\n"
        f"{next_actions}\n"
    )


def _host_instruction(*, dataset_path: Path, task: str, max_images: int) -> str:
    return (
        "Read albumentationsx://examples/first-preview, then call run_host_smoke_check. "
        f"If preview_ready is true, call plan_dataset_onboarding with dataset_path={dataset_path!s}, "
        f"task={task}, max_images={max_images}; then build_review_packet, validate_preview_request, and render "
        "one small preview batch only after valid=true."
    )


def _next_actions(*, root_ok: bool, dataset_ok: bool) -> list[str]:
    if not root_ok:
        return ["Move the dataset under --allowed-root or choose a smaller allowed root that contains it."]
    if not dataset_ok:
        return ["Create the dataset directory or pass an existing local image folder."]
    return [
        "Run the host instruction in the MCP host UI.",
        "Call validate_preview_request before rendering.",
        "Inspect the first contact sheet before changing intensity or variants.",
    ]


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
