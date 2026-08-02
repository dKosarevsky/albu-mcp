"""Ordered, atomic composition of the public MCP adapter surface."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, cast

from mcp.server import MCPServer

from albumentationsx_mcp.adapters.mcp.apps import SURFACE as PREVIEW_APP_SURFACE
from albumentationsx_mcp.adapters.mcp.apps import register_preview_app_fallback
from albumentationsx_mcp.adapters.mcp.catalog import SURFACE as CATALOG_SURFACE
from albumentationsx_mcp.adapters.mcp.catalog import register_catalog_adapter
from albumentationsx_mcp.adapters.mcp.contracts import (
    AdapterSurface,
    CombinedSurface,
    adapter_surface_for_profile,
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
from albumentationsx_mcp.adapters.mcp.registrar import CollectedMcpRegistrar, McpRegistrar, ProfiledMcpRegistrar
from albumentationsx_mcp.adapters.mcp.sessions import SURFACE as SESSION_SURFACE
from albumentationsx_mcp.adapters.mcp.sessions import register_session_adapter
from albumentationsx_mcp.capabilities import CapabilityProfile
from albumentationsx_mcp.diagnostics import PublicSurface

if TYPE_CHECKING:
    from albumentationsx_mcp.adapters.mcp.dependencies import McpDependencies

ADAPTER_SURFACES = (
    CATALOG_SURFACE,
    POLICY_SURFACE,
    DATASET_SURFACE,
    PREVIEW_APP_SURFACE,
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
    "trace_preview_variant",
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
    "run_first_preview",
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
    "albumentationsx://examples/torch-cpu-compose",
)


def register_mcp_adapters(
    mcp: MCPServer,
    dependencies: McpDependencies,
    *,
    profile: CapabilityProfile = CapabilityProfile.FULL,
    external_surfaces: tuple[AdapterSurface, ...] = (),
) -> None:
    """Register one canonical profile on a fresh or collision-free MCP server."""
    validate_profiled_adapter_surfaces(ADAPTER_SURFACES)
    declared_surface = surface_for_profile(profile)
    expected_public_surface = public_surface_for_profile(profile)
    actual_public_surface = dependencies.diagnostics_service.public_surface
    if actual_public_surface != expected_public_surface:
        msg = (
            f"MCP dependency surface does not match capability profile {profile.value!r}: "
            f"expected {expected_public_surface!r}, got {actual_public_surface!r}"
        )
        raise ValueError(msg)
    external_adapter_names = _validate_external_surfaces(external_surfaces)
    external_surface = (
        combine_adapter_surfaces_for_profile(external_surfaces, profile) if external_surfaces else _empty_surface()
    )
    registered_surface = _subtract_surface(declared_surface, external_surface)

    collected = CollectedMcpRegistrar()
    _register_adapters(
        collected,
        dependencies,
        profile=profile,
        external_adapter_names=external_adapter_names,
    )

    staged = MCPServer("AlbumentationsX MCP registration validation")
    collected.apply_to(staged)
    staged_surface = _registered_surface(staged)
    if staged_surface != registered_surface:
        msg = (
            f"collected MCP surface does not match declaration: "
            f"expected {registered_surface!r}, got {staged_surface!r}"
        )
        raise RuntimeError(msg)

    initial_surface = _registered_surface(mcp)
    _verify_external_surface(initial_surface, external_surface)
    _raise_on_collisions(initial_surface, registered_surface)
    collected.apply_to(mcp)
    _verify_registered_surface(mcp, initial_surface, registered_surface)


def surface_for_profile(profile: CapabilityProfile) -> CombinedSurface:
    """Return the validated canonical surface for one capability profile."""
    if not isinstance(profile, CapabilityProfile):
        msg = f"unknown capability profile: {profile}"
        raise TypeError(msg)
    return PROFILE_SURFACES[profile]


def public_surface_for_profile(profile: CapabilityProfile) -> PublicSurface:
    """Return diagnostics metadata derived from the canonical profile declaration."""
    selected = surface_for_profile(profile)
    selected_tools = set(selected.tools)
    selected_prompts = set(selected.prompts)
    selected_resources = set(selected.resources)
    return PublicSurface(
        capability_profile=profile,
        tools=[name for name in PUBLIC_TOOLS if name in selected_tools],
        prompts=[name for name in PUBLIC_PROMPTS if name in selected_prompts],
        workflow_resources=[uri for uri in PUBLIC_WORKFLOW_RESOURCES if uri in selected_resources],
    )


def _register_adapters(
    mcp: McpRegistrar,
    dependencies: McpDependencies,
    *,
    profile: CapabilityProfile,
    external_adapter_names: set[str],
) -> None:
    available_tools = set(dependencies.diagnostics_service.public_surface.tools)
    catalog_registrar = _profiled_registrar(mcp, CATALOG_SURFACE, profile)
    register_catalog_adapter(catalog_registrar, catalog=dependencies.catalog, available_tools=available_tools)
    catalog_registrar.verify_complete()

    policy_registrar = _profiled_registrar(mcp, POLICY_SURFACE, profile)
    register_policy_adapter(
        policy_registrar,
        catalog=dependencies.catalog,
        pipeline_service=dependencies.pipeline_service,
    )
    policy_registrar.verify_complete()

    dataset_registrar = _profiled_registrar(mcp, DATASET_SURFACE, profile)
    register_dataset_adapter(
        dataset_registrar,
        path_policy=dependencies.path_policy,
        pipeline_service=dependencies.pipeline_service,
        preview_service=dependencies.preview_service,
        guided_preview_service=dependencies.guided_preview_service,
        available_tools=available_tools,
    )
    dataset_registrar.verify_complete()

    if PREVIEW_APP_SURFACE.adapter not in external_adapter_names:
        app_registrar = _profiled_registrar(mcp, PREVIEW_APP_SURFACE, profile)
        register_preview_app_fallback(app_registrar, preview_service=dependencies.preview_service)
        app_registrar.verify_complete()

    preview_registrar = _profiled_registrar(mcp, PREVIEW_SURFACE, profile)
    register_preview_adapter(
        preview_registrar,
        artifact_store=dependencies.artifact_store,
        preview_service=dependencies.preview_service,
        preview_validator=dependencies.preview_validator,
        tuning_store=dependencies.tuning_store,
        session_store=dependencies.session_store,
        feedback_store=dependencies.feedback_store,
        report_service=dependencies.report_service,
    )
    preview_registrar.verify_complete()

    session_registrar = _profiled_registrar(mcp, SESSION_SURFACE, profile)
    register_session_adapter(
        session_registrar,
        preview_service=dependencies.preview_service,
        tuning_store=dependencies.tuning_store,
        session_store=dependencies.session_store,
        feedback_store=dependencies.feedback_store,
    )
    session_registrar.verify_complete()

    diagnostics_registrar = _profiled_registrar(mcp, DIAGNOSTICS_SURFACE, profile)
    register_diagnostics_adapter(
        diagnostics_registrar,
        diagnostics_service=dependencies.diagnostics_service,
        pipeline_service=dependencies.pipeline_service,
    )
    diagnostics_registrar.verify_complete()

    prompt_registrar = _profiled_registrar(mcp, PROMPT_SURFACE, profile)
    register_prompt_adapter(prompt_registrar, available_tools=available_tools)
    prompt_registrar.verify_complete()


def _validate_external_surfaces(external_surfaces: tuple[AdapterSurface, ...]) -> set[str]:
    canonical = {surface.adapter: surface for surface in ADAPTER_SURFACES}
    names: set[str] = set()
    for surface in external_surfaces:
        if surface.adapter in names:
            msg = f"duplicate external MCP adapter surface: {surface.adapter!r}"
            raise ValueError(msg)
        if canonical.get(surface.adapter) != surface:
            msg = f"unknown or mismatched external MCP adapter surface: {surface.adapter!r}"
            raise ValueError(msg)
        names.add(surface.adapter)
    return names


def _empty_surface() -> CombinedSurface:
    return CombinedSurface(tools=(), resources=(), resource_templates=(), prompts=())


def _subtract_surface(surface: CombinedSurface, excluded: CombinedSurface) -> CombinedSurface:
    return CombinedSurface(
        tools=tuple(item for item in surface.tools if item not in set(excluded.tools)),
        resources=tuple(item for item in surface.resources if item not in set(excluded.resources)),
        resource_templates=tuple(
            item for item in surface.resource_templates if item not in set(excluded.resource_templates)
        ),
        prompts=tuple(item for item in surface.prompts if item not in set(excluded.prompts)),
    )


def _verify_external_surface(actual: CombinedSurface, expected: CombinedSurface) -> None:
    for kind in ("tools", "resources", "resource_templates", "prompts"):
        missing = set(getattr(expected, kind)) - set(getattr(actual, kind))
        if missing:
            identifier = next(item for item in getattr(expected, kind) if item in missing)
            msg = f"external MCP {kind} identifier {identifier!r} is not registered"
            raise RuntimeError(msg)


def _profiled_registrar(
    mcp: McpRegistrar,
    declared: AdapterSurface,
    profile: CapabilityProfile,
) -> ProfiledMcpRegistrar:
    return ProfiledMcpRegistrar(
        mcp,
        declared=declared,
        selected=adapter_surface_for_profile(declared, profile),
    )


def _registered_surface(mcp: MCPServer) -> CombinedSurface:
    async def list_surface() -> CombinedSurface:
        tools, resources, resource_templates, prompts = await asyncio.gather(
            mcp.list_tools(),
            mcp.list_resources(),
            mcp.list_resource_templates(),
            mcp.list_prompts(),
        )
        return CombinedSurface(
            tools=tuple(tool.name for tool in tools),
            resources=tuple(str(resource.uri) for resource in resources),
            resource_templates=tuple(template.uri_template for template in resource_templates),
            prompts=tuple(prompt.name for prompt in prompts),
        )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(list_surface())
    with ThreadPoolExecutor(max_workers=1) as executor:
        return cast("CombinedSurface", executor.submit(asyncio.run, list_surface()).result())


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


def _verify_registered_surface(
    mcp: MCPServer,
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
