"""Host-facing review packet assembly for first preview handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field

from albumentationsx_mcp.diagnostics import DiagnosticStatus
from albumentationsx_mcp.models import StrictModel
from albumentationsx_mcp.onboarding import RecipeBuilder, build_dataset_onboarding_report
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.presets import Intensity
from albumentationsx_mcp.preview import PathPolicy

_READY_TOOL_SEQUENCE = [
    "validate_preview_request",
    "render_preview_batch",
    "adjust_pipeline",
    "render_preview_batch",
    "compare_preview_runs",
    "export_preview_report",
    "export_pipeline",
]


class ReviewPacket(StrictModel):
    """One compact handoff packet for agent-guided preview review."""

    status: DiagnosticStatus
    preview_ready: bool
    dataset_path: str
    task: str
    targets: list[str]
    review_brief: list[str] = Field(default_factory=list)
    recommended_next_tool: str
    tool_sequence: list[str] = Field(default_factory=list)
    preview_request_template: dict[str, Any] | None = None
    report_handoff: dict[str, Any]
    next_actions: list[str] = Field(default_factory=list)
    remediation_actions: list[dict[str, Any]] = Field(default_factory=list)
    onboarding_report: dict[str, Any]


def build_review_packet(  # noqa: PLR0913
    *,
    dataset_path: Path,
    task: str,
    intensity: Intensity,
    targets: list[str] | None,
    path_policy: PathPolicy,
    pipeline_service: PipelineService,
    recipe_builder: RecipeBuilder,
    max_images: int = 8,
) -> ReviewPacket:
    """Build a single agent-legible packet for first-preview review."""
    onboarding = build_dataset_onboarding_report(
        dataset_path=dataset_path,
        task=task,
        intensity=intensity,
        targets=targets,
        max_images=max_images,
        path_policy=path_policy,
        pipeline_service=pipeline_service,
        recipe_builder=recipe_builder,
    )
    preview_template = (
        onboarding.preview_request_template.model_dump(mode="json", exclude_none=True)
        if onboarding.preview_request_template is not None
        else None
    )
    return ReviewPacket(
        status=onboarding.status,
        preview_ready=onboarding.preview_ready,
        dataset_path=onboarding.dataset_path,
        task=onboarding.recipe.task,
        targets=onboarding.recipe.targets,
        review_brief=onboarding.review_brief,
        recommended_next_tool=_recommended_next_tool(preview_ready=onboarding.preview_ready),
        tool_sequence=list(_READY_TOOL_SEQUENCE) if onboarding.preview_ready else [],
        preview_request_template=preview_template,
        report_handoff=_report_handoff(),
        next_actions=onboarding.next_actions,
        remediation_actions=[action.model_dump(mode="json") for action in onboarding.remediation_actions],
        onboarding_report=onboarding.model_dump(mode="json", exclude_none=True),
    )


def _recommended_next_tool(*, preview_ready: bool) -> str:
    return "validate_preview_request" if preview_ready else "fix_dataset"


def _report_handoff() -> dict[str, Any]:
    return {
        "tool": "export_preview_report",
        "resource": "albumentationsx://examples/report-handoff",
        "when": "After rendering baseline and candidate previews, comparing runs, and recording concrete feedback.",
        "required_inputs": ["baseline_run_id", "candidate_run_ids", "quality_profile"],
    }
