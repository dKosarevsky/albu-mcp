"""Ordered, atomic composition of the public FastMCP adapter surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from albumentationsx_mcp.adapters.mcp.catalog import SURFACE as CATALOG_SURFACE
from albumentationsx_mcp.adapters.mcp.catalog import register_catalog_adapter
from albumentationsx_mcp.adapters.mcp.contracts import (
    CombinedSurface,
    combine_adapter_surfaces_for_profile,
    validate_profiled_adapter_surfaces,
)
from albumentationsx_mcp.adapters.mcp.dataset import SURFACE as DATASET_SURFACE
from albumentationsx_mcp.adapters.mcp.dataset import register_dataset_adapter
from albumentationsx_mcp.adapters.mcp.diagnostics import SURFACE as DIAGNOSTICS_SURFACE
from albumentationsx_mcp.adapters.mcp.diagnostics import register_diagnostics_adapter
from albumentationsx_mcp.adapters.mcp.policy import SURFACE as POLICY_SURFACE
from albumentationsx_mcp.adapters.mcp.policy import register_policy_adapter
from albumentationsx_mcp.adapters.mcp.preview import SURFACE as PREVIEW_SURFACE
from albumentationsx_mcp.adapters.mcp.preview import register_preview_adapter
from albumentationsx_mcp.adapters.mcp.prompts import SURFACE as PROMPT_SURFACE
from albumentationsx_mcp.adapters.mcp.prompts import register_prompt_adapter
from albumentationsx_mcp.adapters.mcp.sessions import SURFACE as SESSION_SURFACE
from albumentationsx_mcp.adapters.mcp.sessions import register_session_adapter
from albumentationsx_mcp.capabilities import CapabilityProfile

if TYPE_CHECKING:
    from albumentationsx_mcp.adapters.mcp.dependencies import McpDependencies

ADAPTER_SURFACES = (
    CATALOG_SURFACE,
    POLICY_SURFACE,
    DATASET_SURFACE,
    PREVIEW_SURFACE,
    SESSION_SURFACE,
    DIAGNOSTICS_SURFACE,
    PROMPT_SURFACE,
)
PROFILE_SURFACES = {
    profile: combine_adapter_surfaces_for_profile(ADAPTER_SURFACES, profile) for profile in CapabilityProfile
}
COMBINED_SURFACE = PROFILE_SURFACES[CapabilityProfile.FULL]

PUBLIC_TOOLS = (
    "search_transforms",
    "get_transform_schema",
    "validate_pipeline",
    "recommend_pipeline",
    "adjust_pipeline",
    "explain_pipeline",
    "list_feedback_tags",
    "render_preview",
    "render_preview_batch",
    "compare_preview_runs",
    "interpret_preview_feedback",
    "plan_preview_review",
    "summarize_tuning_session",
    "start_tuning_session",
    "record_tuning_session_step",
    "list_tuning_sessions",
    "export_tuning_session",
    "close_tuning_session",
    "archive_tuning_session",
    "cleanup_tuning_sessions",
    "rank_preview_candidates",
    "score_dataset_preview_candidates",
    "list_quality_profiles",
    "recommend_recipe",
    "plan_augmentation_policy",
    "plan_augmentation_policy_candidates",
    "plan_policy_iteration",
    "record_preview_feedback",
    "list_preview_feedback",
    "record_tuning_decision",
    "list_tuning_decisions",
    "export_tuning_report",
    "export_preview_report",
    "list_preview_runs",
    "get_preview_manifest",
    "delete_preview_run",
    "cleanup_preview_runs",
    "export_pipeline",
    "diagnose_environment",
    "run_host_smoke_check",
    "get_workflow_example",
    "validate_preview_request",
    "plan_dataset_onboarding",
    "build_review_packet",
    "inspect_dataset_quality",
)
PUBLIC_PROMPTS = (
    "build_robustness_augmentation_session",
    "run_first_preview_review",
    "compare_preview_runs_for_feedback",
    "tune_pipeline_from_preview_feedback",
    "export_reproducible_pipeline",
)
PUBLIC_WORKFLOW_RESOURCES = (
    "albumentationsx://workflows/catalog",
    "albumentationsx://workflows/preview-tuning",
    "albumentationsx://workflows/annotation-preview",
    "albumentationsx://workflows/task-profiles",
    "albumentationsx://recipes/catalog",
    "albumentationsx://policy-assistant/contract",
    "albumentationsx://diagnostics/guide",
    "albumentationsx://examples/client-smoke",
    "albumentationsx://examples/first-preview",
    "albumentationsx://examples/distortion-review",
    "albumentationsx://examples/dataset-onboarding",
    "albumentationsx://examples/diagnostics",
    "albumentationsx://examples/review-loop",
    "albumentationsx://examples/report-handoff",
)


@dataclass(frozen=True, slots=True)
class _ManagerState:
    tools: dict[Any, Any]
    resources: dict[Any, Any]
    resource_templates: dict[Any, Any]
    prompts: dict[Any, Any]


def register_mcp_adapters(
    mcp: FastMCP,
    dependencies: McpDependencies,
    *,
    profile: CapabilityProfile = CapabilityProfile.FULL,
) -> None:
    """Register one canonical profile without leaving a partial target surface."""
    validate_profiled_adapter_surfaces(ADAPTER_SURFACES)
    declared_surface = surface_for_profile(profile)
    before = _capture_manager_state(mcp)
    initial_surface = _surface_from_state(before)
    _raise_on_collisions(initial_surface, declared_surface)

    try:
        staged = FastMCP("AlbumentationsX MCP registration staging")
        _register_adapters(staged, dependencies)
        _verify_staged_surface(staged)
        selected = _select_manager_state(_capture_manager_state(staged), declared_surface)
        _append_manager_state(mcp, selected)
        _verify_registered_surface(mcp, initial_surface, declared_surface)
    except Exception:
        _restore_manager_state(mcp, before)
        raise


def surface_for_profile(profile: CapabilityProfile) -> CombinedSurface:
    """Return the validated canonical surface for one capability profile."""
    if not isinstance(profile, CapabilityProfile):
        msg = f"unknown capability profile: {profile}"
        raise TypeError(msg)
    return PROFILE_SURFACES[profile]


def _register_adapters(mcp: FastMCP, dependencies: McpDependencies) -> None:
    register_catalog_adapter(mcp, catalog=dependencies.catalog)
    register_policy_adapter(
        mcp,
        catalog=dependencies.catalog,
        pipeline_service=dependencies.pipeline_service,
    )
    register_dataset_adapter(
        mcp,
        path_policy=dependencies.path_policy,
        pipeline_service=dependencies.pipeline_service,
        preview_service=dependencies.preview_service,
    )
    register_preview_adapter(
        mcp,
        artifact_store=dependencies.artifact_store,
        preview_service=dependencies.preview_service,
        preview_validator=dependencies.preview_validator,
        tuning_store=dependencies.tuning_store,
        session_store=dependencies.session_store,
        feedback_store=dependencies.feedback_store,
        report_service=dependencies.report_service,
    )
    register_session_adapter(
        mcp,
        preview_service=dependencies.preview_service,
        tuning_store=dependencies.tuning_store,
        session_store=dependencies.session_store,
        feedback_store=dependencies.feedback_store,
    )
    register_diagnostics_adapter(
        mcp,
        diagnostics_service=dependencies.diagnostics_service,
        pipeline_service=dependencies.pipeline_service,
    )
    register_prompt_adapter(mcp)


def _capture_manager_state(mcp: FastMCP) -> _ManagerState:
    return _ManagerState(
        tools=dict(mcp._tool_manager._tools),  # noqa: SLF001
        resources=dict(mcp._resource_manager._resources),  # noqa: SLF001
        resource_templates=dict(mcp._resource_manager._templates),  # noqa: SLF001
        prompts=dict(mcp._prompt_manager._prompts),  # noqa: SLF001
    )


def _surface_from_state(state: _ManagerState) -> CombinedSurface:
    return CombinedSurface(
        tools=tuple(state.tools),
        resources=tuple(str(uri) for uri in state.resources),
        resource_templates=tuple(state.resource_templates),
        prompts=tuple(state.prompts),
    )


def _registered_surface(mcp: FastMCP) -> CombinedSurface:
    return CombinedSurface(
        tools=tuple(mcp._tool_manager._tools),  # noqa: SLF001
        resources=tuple(str(uri) for uri in mcp._resource_manager._resources),  # noqa: SLF001
        resource_templates=tuple(mcp._resource_manager._templates),  # noqa: SLF001
        prompts=tuple(mcp._prompt_manager._prompts),  # noqa: SLF001
    )


def _raise_on_collisions(existing: CombinedSurface, declared: CombinedSurface) -> None:
    for kind in ("tools", "resources", "resource_templates", "prompts"):
        existing_identifiers = set(getattr(existing, kind))
        collision = next(
            (identifier for identifier in getattr(declared, kind) if identifier in existing_identifiers),
            None,
        )
        if collision is not None:
            msg = f"MCP {kind} collision: {collision!r} is already registered"
            raise ValueError(msg)


def _verify_staged_surface(mcp: FastMCP) -> None:
    actual = _registered_surface(mcp)
    if actual != COMBINED_SURFACE:
        msg = f"staged MCP surface does not match full declaration: expected {COMBINED_SURFACE!r}, got {actual!r}"
        raise RuntimeError(msg)


def _verify_registered_surface(
    mcp: FastMCP,
    initial: CombinedSurface,
    declared: CombinedSurface,
) -> None:
    expected = CombinedSurface(
        tools=initial.tools + declared.tools,
        resources=initial.resources + declared.resources,
        resource_templates=initial.resource_templates + declared.resource_templates,
        prompts=initial.prompts + declared.prompts,
    )
    actual = _registered_surface(mcp)
    if actual != expected:
        msg = f"registered MCP surface does not match declarations: expected {expected!r}, got {actual!r}"
        raise RuntimeError(msg)


def _select_manager_state(state: _ManagerState, surface: CombinedSurface) -> _ManagerState:
    tools = set(surface.tools)
    resources = set(surface.resources)
    resource_templates = set(surface.resource_templates)
    prompts = set(surface.prompts)
    return _ManagerState(
        tools={name: item for name, item in state.tools.items() if name in tools},
        resources={uri: item for uri, item in state.resources.items() if str(uri) in resources},
        resource_templates={
            uri: item for uri, item in state.resource_templates.items() if str(uri) in resource_templates
        },
        prompts={name: item for name, item in state.prompts.items() if name in prompts},
    )


def _append_manager_state(mcp: FastMCP, state: _ManagerState) -> None:
    managers = (
        (mcp._tool_manager._tools, state.tools),  # noqa: SLF001
        (mcp._resource_manager._resources, state.resources),  # noqa: SLF001
        (mcp._resource_manager._templates, state.resource_templates),  # noqa: SLF001
        (mcp._prompt_manager._prompts, state.prompts),  # noqa: SLF001
    )
    for registered, selected in managers:
        registered.update(selected)


def _restore_manager_state(mcp: FastMCP, state: _ManagerState) -> None:
    managers = (
        (mcp._tool_manager._tools, state.tools),  # noqa: SLF001
        (mcp._resource_manager._resources, state.resources),  # noqa: SLF001
        (mcp._resource_manager._templates, state.resource_templates),  # noqa: SLF001
        (mcp._prompt_manager._prompts, state.prompts),  # noqa: SLF001
    )
    for registered, original in managers:
        registered.clear()
        registered.update(original)
