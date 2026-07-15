from __future__ import annotations

from typing import Any, cast

import pytest

from albumentationsx_mcp.adapters.mcp.contracts import (
    AdapterSurface,
    ProfileSurface,
    combine_adapter_surfaces_for_profile,
    validate_profiled_adapter_surfaces,
)
from albumentationsx_mcp.adapters.mcp.registration import ADAPTER_SURFACES, COMBINED_SURFACE
from albumentationsx_mcp.capabilities import CapabilityProfile

_EXPECTED_COUNTS = {
    CapabilityProfile.CORE: (16, 9, 1, 0),
    CapabilityProfile.REVIEW: (41, 19, 2, 5),
    CapabilityProfile.DATASET: (20, 9, 1, 0),
    CapabilityProfile.FULL: (45, 20, 2, 5),
}

_PROMPT_TOOL_DEPENDENCIES = {
    "build_robustness_augmentation_session": {
        "recommend_pipeline",
        "validate_pipeline",
        "render_preview_batch",
        "adjust_pipeline",
    },
    "compare_preview_runs_for_feedback": {"compare_preview_runs", "interpret_preview_feedback"},
    "run_first_preview_review": {"validate_preview_request", "render_preview_batch"},
    "tune_pipeline_from_preview_feedback": {"adjust_pipeline", "record_preview_feedback"},
    "export_reproducible_pipeline": {"export_pipeline", "get_preview_manifest"},
}

_WORKFLOW_RESOURCE_TOOL_DEPENDENCIES = {
    "albumentationsx://policy-assistant/contract": {
        "render_preview_batch",
        "compare_preview_runs",
        "interpret_preview_feedback",
        "adjust_pipeline",
        "record_preview_feedback",
    },
    "albumentationsx://workflows/catalog": {
        "recommend_pipeline",
        "render_preview",
        "record_tuning_session_step",
        "get_preview_manifest",
    },
    "albumentationsx://workflows/task-profiles": {"recommend_pipeline", "render_preview"},
    "albumentationsx://workflows/preview-tuning": {
        "recommend_pipeline",
        "render_preview",
        "record_tuning_session_step",
    },
    "albumentationsx://workflows/annotation-preview": {
        "validate_pipeline",
        "render_preview",
        "get_preview_manifest",
    },
    "albumentationsx://examples/client-smoke": {
        "recommend_recipe",
        "validate_pipeline",
        "run_host_smoke_check",
    },
    "albumentationsx://examples/first-preview": {
        "run_host_smoke_check",
        "validate_preview_request",
        "render_preview_batch",
    },
    "albumentationsx://examples/distortion-review": {
        "render_preview_batch",
        "record_preview_feedback",
        "adjust_pipeline",
        "compare_preview_runs",
        "export_pipeline",
    },
    "albumentationsx://examples/dataset-onboarding": {
        "plan_dataset_onboarding",
        "validate_preview_request",
        "render_preview_batch",
    },
    "albumentationsx://examples/diagnostics": {"diagnose_environment", "run_host_smoke_check"},
    "albumentationsx://examples/review-loop": {
        "record_preview_feedback",
        "list_preview_feedback",
        "adjust_pipeline",
    },
    "albumentationsx://examples/report-handoff": {
        "export_preview_report",
        "export_pipeline",
    },
}


@pytest.mark.parametrize(("profile", "counts"), _EXPECTED_COUNTS.items())
def test_profile_surface_has_expected_counts(
    profile: CapabilityProfile,
    counts: tuple[int, int, int, int],
) -> None:
    surface = combine_adapter_surfaces_for_profile(ADAPTER_SURFACES, profile)

    assert (
        len(surface.tools),
        len(surface.resources),
        len(surface.resource_templates),
        len(surface.prompts),
    ) == counts


def test_full_profile_preserves_canonical_registration_order() -> None:
    assert combine_adapter_surfaces_for_profile(ADAPTER_SURFACES, CapabilityProfile.FULL) == COMBINED_SURFACE


@pytest.mark.parametrize(
    ("profile", "included_tools", "excluded_tools"),
    [
        (
            CapabilityProfile.CORE,
            {"search_transforms", "adjust_pipeline", "diagnose_environment", "get_workflow_example"},
            {"render_preview", "plan_dataset_onboarding", "start_tuning_session"},
        ),
        (
            CapabilityProfile.REVIEW,
            {"render_preview", "compare_preview_runs", "start_tuning_session", "export_preview_report"},
            {"plan_dataset_onboarding", "inspect_dataset_quality"},
        ),
        (
            CapabilityProfile.DATASET,
            {"plan_dataset_onboarding", "build_review_packet", "inspect_dataset_quality"},
            {"render_preview", "start_tuning_session"},
        ),
    ],
)
def test_focused_profile_tool_membership(
    profile: CapabilityProfile,
    included_tools: set[str],
    excluded_tools: set[str],
) -> None:
    tools = set(combine_adapter_surfaces_for_profile(ADAPTER_SURFACES, profile).tools)

    assert included_tools <= tools
    assert excluded_tools.isdisjoint(tools)


def test_production_profile_declarations_are_complete() -> None:
    validate_profiled_adapter_surfaces(ADAPTER_SURFACES)


@pytest.mark.parametrize(
    ("surface", "message"),
    [
        (AdapterSurface(adapter="missing", tools=("one",)), "missing profile declaration"),
        (
            AdapterSurface(
                adapter="outside",
                tools=("one",),
                profile_surfaces=(ProfileSurface(profiles=(CapabilityProfile.FULL,), tools=("other",)),),
            ),
            "outside declared surface",
        ),
        (
            AdapterSurface(
                adapter="duplicate",
                tools=("one",),
                profile_surfaces=(
                    ProfileSurface(profiles=(CapabilityProfile.CORE, CapabilityProfile.FULL), tools=("one",)),
                    ProfileSurface(profiles=(CapabilityProfile.REVIEW, CapabilityProfile.FULL), tools=("one",)),
                ),
            ),
            "duplicate profile declaration",
        ),
        (
            AdapterSurface(
                adapter="not-full",
                tools=("one",),
                profile_surfaces=(ProfileSurface(profiles=(CapabilityProfile.CORE,), tools=("one",)),),
            ),
            "must include full profile",
        ),
    ],
)
def test_invalid_profile_declaration_is_rejected(surface: AdapterSurface, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_profiled_adapter_surfaces((surface,))


def test_unknown_profile_value_is_rejected() -> None:
    invalid_profile = cast("Any", "unknown")

    with pytest.raises(TypeError, match="unknown capability profile"):
        ProfileSurface(profiles=(invalid_profile,), tools=("one",))


@pytest.mark.parametrize("profile", CapabilityProfile)
def test_profile_prompts_and_workflow_resources_are_dependency_closed(profile: CapabilityProfile) -> None:
    surface = combine_adapter_surfaces_for_profile(ADAPTER_SURFACES, profile)
    tools = set(surface.tools)

    for prompt in surface.prompts:
        assert _PROMPT_TOOL_DEPENDENCIES[prompt] <= tools
    for resource in surface.resources:
        dependencies = _WORKFLOW_RESOURCE_TOOL_DEPENDENCIES.get(resource, set())
        assert dependencies <= tools
