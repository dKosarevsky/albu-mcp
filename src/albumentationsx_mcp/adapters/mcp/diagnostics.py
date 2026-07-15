"""FastMCP diagnostics and workflow resource registration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface, ProfileSurface
from albumentationsx_mcp.capabilities import (
    CORE_PROFILE_MEMBERSHIP,
    DATASET_PROFILE_MEMBERSHIP,
    REVIEW_PROFILE_MEMBERSHIP,
)
from albumentationsx_mcp.diagnostics import build_diagnostics_guide
from albumentationsx_mcp.host_smoke import build_host_smoke_report
from albumentationsx_mcp.models import TargetSpec
from albumentationsx_mcp.presets import Intensity
from albumentationsx_mcp.recipes import recommend_recipe
from albumentationsx_mcp.workflows import (
    HostExampleId,
    get_agent_workflow,
    get_host_example,
    list_agent_workflows,
    list_task_profiles,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from albumentationsx_mcp.diagnostics import DiagnosticsService
    from albumentationsx_mcp.pipeline import PipelineService

_TOOLS = ("diagnose_environment", "run_host_smoke_check", "get_workflow_example")
_RESOURCES = (
    "albumentationsx://capabilities",
    "albumentationsx://diagnostics/guide",
    "albumentationsx://workflows/catalog",
    "albumentationsx://workflows/task-profiles",
    "albumentationsx://workflows/preview-tuning",
    "albumentationsx://workflows/annotation-preview",
    "albumentationsx://examples/client-smoke",
    "albumentationsx://examples/first-preview",
    "albumentationsx://examples/distortion-review",
    "albumentationsx://examples/dataset-onboarding",
    "albumentationsx://examples/diagnostics",
    "albumentationsx://examples/review-loop",
    "albumentationsx://examples/report-handoff",
)
_CORE_RESOURCES = (
    "albumentationsx://capabilities",
    "albumentationsx://diagnostics/guide",
    "albumentationsx://examples/client-smoke",
    "albumentationsx://examples/diagnostics",
)
_REVIEW_RESOURCES = (
    "albumentationsx://workflows/catalog",
    "albumentationsx://workflows/task-profiles",
    "albumentationsx://workflows/preview-tuning",
    "albumentationsx://workflows/annotation-preview",
    "albumentationsx://examples/first-preview",
    "albumentationsx://examples/distortion-review",
    "albumentationsx://examples/review-loop",
    "albumentationsx://examples/report-handoff",
)
_DATASET_RESOURCES = ("albumentationsx://examples/dataset-onboarding",)
SURFACE = AdapterSurface(
    adapter="diagnostics",
    tools=_TOOLS,
    resources=_RESOURCES,
    profile_surfaces=(
        ProfileSurface(profiles=CORE_PROFILE_MEMBERSHIP, tools=_TOOLS, resources=_CORE_RESOURCES),
        ProfileSurface(profiles=REVIEW_PROFILE_MEMBERSHIP, resources=_REVIEW_RESOURCES),
        ProfileSurface(profiles=DATASET_PROFILE_MEMBERSHIP, resources=_DATASET_RESOURCES),
    ),
)


def register_diagnostics_adapter(
    mcp: FastMCP,
    *,
    diagnostics_service: DiagnosticsService,
    pipeline_service: PipelineService,
) -> None:
    """Register capabilities, diagnostics, host smoke, and workflow guides."""

    @mcp.resource("albumentationsx://capabilities")
    def capabilities_resource() -> str:
        """Return operational limits and safety boundaries for this MCP server."""
        public_surface = diagnostics_service.public_surface
        return json.dumps(
            {
                "allowed_roots": [str(path.resolve()) for path in diagnostics_service.allowed_roots],
                "artifact_root": str(diagnostics_service.artifact_root.resolve()),
                "capability_profile": public_surface.capability_profile.value,
                "preview_limits": {
                    "max_input_paths": 32,
                    "max_variants_per_image": 16,
                    "max_side": 4096,
                    "max_preview_runs": diagnostics_service.max_preview_runs,
                },
                "tools": public_surface.tools,
                "prompts": public_surface.prompts,
                "workflow_resources": public_surface.workflow_resources,
            },
            sort_keys=True,
        )

    @mcp.resource("albumentationsx://diagnostics/guide")
    def diagnostics_guide_resource() -> str:
        """Return the MCP host diagnostics playbook."""
        return build_diagnostics_guide().model_dump_json()

    @mcp.resource("albumentationsx://workflows/catalog")
    def workflows_catalog() -> str:
        """Return built-in agent workflow guides as compact JSON."""
        data = [workflow.model_dump(mode="json") for workflow in list_agent_workflows()]
        return json.dumps(data, sort_keys=True)

    @mcp.resource("albumentationsx://workflows/task-profiles")
    def task_profiles_resource() -> str:
        """Return task-specific workflow profiles as compact JSON."""
        data = [profile.model_dump(mode="json") for profile in list_task_profiles()]
        return json.dumps(data, sort_keys=True)

    @mcp.resource("albumentationsx://workflows/preview-tuning")
    def preview_tuning_workflow() -> str:
        """Return the preview-driven augmentation tuning workflow guide."""
        return get_agent_workflow("preview-tuning").model_dump_json()

    @mcp.resource("albumentationsx://workflows/annotation-preview")
    def annotation_preview_workflow() -> str:
        """Return the annotation-aware preview workflow guide."""
        return get_agent_workflow("annotation-preview").model_dump_json()

    @mcp.resource("albumentationsx://examples/client-smoke")
    def client_smoke_example() -> str:
        """Return the MCP host smoke-check example."""
        return get_host_example(
            "client-smoke",
            preview_tools_available=diagnostics_service.preview_tools_available,
        ).model_dump_json()

    @mcp.resource("albumentationsx://examples/first-preview")
    def first_preview_example() -> str:
        """Return the MCP first local preview host example."""
        return get_host_example("first-preview").model_dump_json()

    @mcp.resource("albumentationsx://examples/distortion-review")
    def distortion_review_example() -> str:
        """Return the MCP distorted robustness review example."""
        return get_host_example("distortion-review").model_dump_json()

    @mcp.resource("albumentationsx://examples/dataset-onboarding")
    def dataset_onboarding_example() -> str:
        """Return the MCP dataset onboarding host example."""
        return get_host_example("dataset-onboarding").model_dump_json()

    @mcp.resource("albumentationsx://examples/diagnostics")
    def diagnostics_example() -> str:
        """Return the MCP host diagnostics example."""
        return get_host_example("diagnostics").model_dump_json()

    @mcp.resource("albumentationsx://examples/review-loop")
    def review_loop_example() -> str:
        """Return the concrete preview feedback host example."""
        return get_host_example("review-loop").model_dump_json()

    @mcp.resource("albumentationsx://examples/report-handoff")
    def report_handoff_example() -> str:
        """Return the visual report handoff host example."""
        return get_host_example("report-handoff").model_dump_json()

    @mcp.tool(name="diagnose_environment")
    def diagnose_environment_tool(include_write_probe: bool = True) -> dict[str, Any]:  # noqa: FBT001, FBT002
        """Diagnose local MCP setup, root access, artifact writes, and public surface discovery."""
        return diagnostics_service.diagnose(include_write_probe=include_write_probe).model_dump(mode="json")

    @mcp.tool(name="run_host_smoke_check")
    def run_host_smoke_check_tool(
        include_write_probe: bool = True,  # noqa: FBT001, FBT002
        task: str = "classification",
        intensity: Intensity = "low",
        targets: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a read-only host preflight; reading the client-smoke resource is optional."""
        diagnostics = diagnostics_service.diagnose(include_write_probe=include_write_probe)
        recipe = recommend_recipe(
            task=task,
            intensity=intensity,
            targets=targets,
            available_tools=diagnostics_service.public_surface.tools,
        )
        validation = pipeline_service.validate_pipeline(recipe.pipeline, TargetSpec(targets=recipe.targets))
        return build_host_smoke_report(
            diagnostics=diagnostics,
            recipe=recipe,
            validation=validation,
            preview_tools_available=diagnostics_service.preview_tools_available,
        ).model_dump(mode="json")

    @mcp.tool(name="get_workflow_example")
    def get_workflow_example_tool(example_id: HostExampleId) -> dict[str, Any]:
        """Return an active-profile workflow example when the MCP host cannot read resources."""
        resource_uri = f"albumentationsx://examples/{example_id}"
        profile = diagnostics_service.public_surface.capability_profile
        if resource_uri not in diagnostics_service.public_surface.workflow_resources:
            msg = (
                f"workflow example {example_id!r} is unavailable in capability profile {profile.value!r}; "
                f"switch to a profile that exposes {resource_uri}"
            )
            raise ValueError(msg)
        return get_host_example(
            example_id,
            preview_tools_available=diagnostics_service.preview_tools_available,
        ).model_dump(mode="json")
