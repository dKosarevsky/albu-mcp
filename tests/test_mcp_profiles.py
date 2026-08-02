from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, cast

import pytest
from mcp import Client
from mcp.types import TextResourceContents
from mcp.types.version import LATEST_MODERN_VERSION

from albumentationsx_mcp.adapters.mcp.contracts import (
    AdapterSurface,
    ProfileSurface,
    combine_adapter_surfaces_for_profile,
    validate_profiled_adapter_surfaces,
)
from albumentationsx_mcp.adapters.mcp.registration import ADAPTER_SURFACES, COMBINED_SURFACE
from albumentationsx_mcp.capabilities import CapabilityProfile
from albumentationsx_mcp.server import ServerSettings, create_mcp_server

_EXPECTED_COUNTS = {
    CapabilityProfile.CORE: (16, 10, 1, 0),
    CapabilityProfile.REVIEW: (43, 20, 2, 5),
    CapabilityProfile.DATASET: (27, 12, 2, 0),
    CapabilityProfile.FULL: (47, 21, 2, 5),
}

_SINGLE_TOOL_REFERENCE_KEYS = {"primary_tool", "recommended_next_tool", "tool", "v2_tool"}
_TOOL_SEQUENCE_KEYS = {"follow_up_tools", "recommended_tools", "tool_sequence"}
_SINGLE_RESOURCE_REFERENCE_KEYS = {"resource", "resource_uri"}

_PROMPT_TOOL_DEPENDENCIES = {
    "build_robustness_augmentation_session": {
        "recommend_pipeline",
        "validate_pipeline",
        "render_preview_batch",
        "adjust_pipeline",
    },
    "compare_preview_runs_for_feedback": {"compare_preview_runs", "interpret_preview_feedback"},
    "run_first_preview_review": {
        "adjust_pipeline",
        "compare_preview_runs",
        "export_pipeline",
        "render_preview_batch",
        "run_host_smoke_check",
        "trace_preview_variant",
        "validate_preview_request",
    },
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
        "adjust_pipeline",
        "compare_preview_runs",
        "export_pipeline",
        "run_host_smoke_check",
        "trace_preview_variant",
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
    "albumentationsx://examples/torch-cpu-compose": {
        "validate_pipeline",
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
    adapter_order = combine_adapter_surfaces_for_profile(ADAPTER_SURFACES, CapabilityProfile.FULL)

    assert set(adapter_order.tools) == set(COMBINED_SURFACE.tools)
    assert adapter_order.resources == COMBINED_SURFACE.resources
    assert adapter_order.resource_templates == COMBINED_SURFACE.resource_templates
    assert adapter_order.prompts == COMBINED_SURFACE.prompts
    preview_start = COMBINED_SURFACE.tools.index("validate_preview_request")
    assert COMBINED_SURFACE.tools[preview_start : preview_start + 4] == (
        "validate_preview_request",
        "render_preview",
        "render_preview_batch",
        "trace_preview_variant",
    )


@pytest.mark.parametrize(
    ("profile", "included_tools", "excluded_tools"),
    [
        (
            CapabilityProfile.CORE,
            {"search_transforms", "adjust_pipeline", "diagnose_environment", "get_workflow_example"},
            {
                "render_preview",
                "plan_dataset_onboarding",
                "run_first_preview",
                "start_tuning_session",
                "trace_preview_variant",
            },
        ),
        (
            CapabilityProfile.REVIEW,
            {
                "render_preview",
                "compare_preview_runs",
                "start_tuning_session",
                "export_preview_report",
                "trace_preview_variant",
            },
            {"plan_dataset_onboarding", "inspect_dataset_quality", "run_first_preview"},
        ),
        (
            CapabilityProfile.DATASET,
            {
                "build_review_packet",
                "compare_preview_runs",
                "export_preview_report",
                "inspect_dataset_quality",
                "plan_dataset_onboarding",
                "record_preview_feedback",
                "render_preview_batch",
                "run_first_preview",
                "trace_preview_variant",
                "validate_preview_request",
            },
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


@pytest.mark.parametrize(
    ("tool_name", "expected_profiles"),
    [
        ("run_first_preview", {CapabilityProfile.DATASET, CapabilityProfile.FULL}),
        (
            "trace_preview_variant",
            {CapabilityProfile.REVIEW, CapabilityProfile.DATASET, CapabilityProfile.FULL},
        ),
    ],
)
def test_guided_preview_tool_profile_membership_is_exact(
    tool_name: str,
    expected_profiles: set[CapabilityProfile],
) -> None:
    actual_profiles = {
        profile
        for profile in CapabilityProfile
        if tool_name in combine_adapter_surfaces_for_profile(ADAPTER_SURFACES, profile).tools
    }

    assert actual_profiles == expected_profiles


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


@pytest.mark.parametrize("profile", CapabilityProfile)
def test_registered_json_resources_reference_only_active_profile_surface(
    tmp_path: Path,
    profile: CapabilityProfile,
) -> None:
    server = create_mcp_server(
        ServerSettings(
            allowed_roots=[tmp_path],
            artifact_root=tmp_path / "artifacts",
            capability_profile=profile,
        )
    )
    async def read_public_surface() -> tuple[set[str], set[str], dict[str, str]]:
        async with Client(server, mode=LATEST_MODERN_VERSION) as client:
            tools_result = await client.list_tools()
            resources_result = await client.list_resources()
            text_resources: dict[str, str] = {}
            for resource in resources_result.resources:
                result = await client.read_resource(str(resource.uri))
                if len(result.contents) == 1 and isinstance(result.contents[0], TextResourceContents):
                    text_resources[str(resource.uri)] = result.contents[0].text
            return (
                {tool.name for tool in tools_result.tools},
                {str(resource.uri) for resource in resources_result.resources},
                text_resources,
            )

    tools, resources, text_resources = asyncio.run(read_public_surface())
    unresolved: list[str] = []

    for uri, payload in text_resources.items():
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        for reference_kind, reference in _iter_capability_references(data):
            available = resources if reference_kind == "resource" else tools
            if reference not in available:
                unresolved.append(f"{uri}: {reference_kind} {reference}")

    assert unresolved == []


def test_core_client_smoke_resource_and_fallback_describe_non_preview_profile(tmp_path: Path) -> None:
    server = create_mcp_server(
        ServerSettings(
            allowed_roots=[tmp_path],
            artifact_root=tmp_path / "artifacts",
            capability_profile=CapabilityProfile.CORE,
        )
    )
    resource = server._resource_manager._resources["albumentationsx://examples/client-smoke"]
    resource_payload = json.loads(cast("Any", resource).fn())
    fallback_payload = cast("Any", server._tool_manager._tools["get_workflow_example"]).fn(example_id="client-smoke")

    assert resource_payload == fallback_payload
    serialized = json.dumps(resource_payload)
    assert "preview_ready=true" not in serialized
    assert "preview_ready=false" in serialized
    assert "--capability-profile review" in serialized


@pytest.mark.parametrize(
    ("profile", "expected_steps"),
    [
        (
            CapabilityProfile.REVIEW,
            [
                "albumentationsx://examples/client-smoke",
                "run_host_smoke_check",
                "validate_preview_request",
                "render_preview_batch",
                "trace_preview_variant",
                "adjust_pipeline",
                "render_preview_batch",
                "compare_preview_runs",
                "export_pipeline",
            ],
        ),
        (
            CapabilityProfile.FULL,
            [
                "albumentationsx://examples/client-smoke",
                "run_host_smoke_check",
                "run_first_preview",
                "trace_preview_variant",
                "adjust_pipeline",
                "render_preview_batch",
                "compare_preview_runs",
                "export_pipeline",
            ],
        ),
    ],
)
def test_first_preview_resource_fallback_tool_and_prompt_match_active_profile(
    tmp_path: Path,
    profile: CapabilityProfile,
    expected_steps: list[str],
) -> None:
    server = create_mcp_server(
        ServerSettings(
            allowed_roots=[tmp_path],
            artifact_root=tmp_path / "artifacts",
            capability_profile=profile,
        )
    )
    tools = set(server._tool_manager._tools)
    resource = server._resource_manager._resources["albumentationsx://examples/first-preview"]
    resource_payload = json.loads(cast("Any", resource).fn())
    fallback_payload = cast("Any", server._tool_manager._tools["get_workflow_example"]).fn(example_id="first-preview")
    prompt = cast("Any", server._prompt_manager._prompts["run_first_preview_review"]).fn()

    assert resource_payload == fallback_payload
    assert [step["tool"] for step in resource_payload["steps"]] == expected_steps
    assert {reference for kind, reference in _iter_capability_references(resource_payload) if kind == "tool"} <= tools
    if profile is CapabilityProfile.FULL:
        assert "run_first_preview" in prompt
        assert prompt.index("run_first_preview") < prompt.index("trace_preview_variant")
    else:
        assert "run_first_preview" not in prompt
        assert prompt.index("validate_preview_request") < prompt.index("render_preview_batch")
        assert prompt.index("render_preview_batch") < prompt.index("trace_preview_variant")


@pytest.mark.parametrize("profile", CapabilityProfile)
def test_recipe_recommendation_lists_only_active_profile_tools(tmp_path: Path, profile: CapabilityProfile) -> None:
    server = create_mcp_server(
        ServerSettings(
            allowed_roots=[tmp_path],
            artifact_root=tmp_path / "artifacts",
            capability_profile=profile,
        )
    )
    tools = set(server._tool_manager._tools)

    recommendation = cast("Any", server._tool_manager._tools["recommend_recipe"]).fn(task="classification")

    assert set(recommendation["recommended_tools"]) <= tools


def _iter_capability_references(value: Any) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _SINGLE_TOOL_REFERENCE_KEYS and isinstance(item, str):
                kind = "resource" if item.startswith("albumentationsx://") else "tool"
                references.append((kind, item))
            elif key in _TOOL_SEQUENCE_KEYS and isinstance(item, list):
                references.extend(("tool", entry) for entry in item if isinstance(entry, str))
            elif key in _SINGLE_RESOURCE_REFERENCE_KEYS and isinstance(item, str):
                references.append(("resource", item))
            references.extend(_iter_capability_references(item))
    elif isinstance(value, list):
        for item in value:
            references.extend(_iter_capability_references(item))
    return references
