import json
from pathlib import Path
from typing import Any, cast

import pytest

from albumentationsx_mcp import server as server_module
from albumentationsx_mcp.adapters.mcp.registration import PUBLIC_WORKFLOW_RESOURCES, surface_for_profile
from albumentationsx_mcp.capabilities import CapabilityProfile
from albumentationsx_mcp.models import TuningSessionSummary
from albumentationsx_mcp.server import ServerSettings, create_mcp_server, settings_from_environment
from albumentationsx_mcp.sessions import InteractiveTuningSessionStore


def test_create_mcp_server_registers_fastmcp_instance() -> None:
    server = create_mcp_server()

    assert server.name == "AlbumentationsX MCP"


def test_server_settings_default_to_full_profile() -> None:
    assert ServerSettings().capability_profile is CapabilityProfile.FULL


def test_server_settings_read_capability_profile_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALBU_MCP_CAPABILITY_PROFILE", "review")

    assert settings_from_environment().capability_profile is CapabilityProfile.REVIEW


def test_unknown_environment_capability_profile_lists_accepted_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALBU_MCP_CAPABILITY_PROFILE", "unknown")

    with pytest.raises(ValueError, match="unknown capability profile") as error:
        settings_from_environment()

    message = str(error.value)
    assert "unknown capability profile" in message
    for profile in CapabilityProfile:
        assert profile.value in message


@pytest.mark.parametrize("profile", CapabilityProfile)
def test_create_mcp_server_exposes_exact_profile_and_capabilities(
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
    expected = surface_for_profile(profile)

    assert tuple(server._tool_manager._tools) == expected.tools
    assert tuple(str(uri) for uri in server._resource_manager._resources) == expected.resources
    assert tuple(server._resource_manager._templates) == expected.resource_templates
    assert tuple(server._prompt_manager._prompts) == expected.prompts

    capabilities = json.loads(cast("Any", server._resource_manager._resources["albumentationsx://capabilities"]).fn())
    diagnostics = cast("Any", server._tool_manager._tools["diagnose_environment"]).fn(include_write_probe=False)
    assert capabilities["capability_profile"] == profile.value
    assert set(capabilities["tools"]) == set(expected.tools)
    assert set(capabilities["prompts"]) == set(expected.prompts)
    assert capabilities["workflow_resources"] == [
        uri for uri in PUBLIC_WORKFLOW_RESOURCES if uri in set(expected.resources)
    ]
    assert diagnostics["capability_profile"] == profile.value
    assert diagnostics["status"] == "ok"


@pytest.mark.parametrize(
    ("profile", "expected_state"),
    [
        (CapabilityProfile.CORE, "blocked"),
        (CapabilityProfile.REVIEW, "ready"),
        (CapabilityProfile.DATASET, "ready"),
        (CapabilityProfile.FULL, "ready"),
    ],
)
def test_host_smoke_preview_readiness_matches_active_profile(
    tmp_path: Path,
    profile: CapabilityProfile,
    expected_state: str,
) -> None:
    server = create_mcp_server(
        ServerSettings(
            allowed_roots=[tmp_path],
            artifact_root=tmp_path / "artifacts",
            capability_profile=profile,
        )
    )

    report = cast("Any", server._tool_manager._tools["run_host_smoke_check"]).fn(include_write_probe=False)
    preview_ready = expected_state == "ready"

    assert report["capability_profile"] == profile.value
    assert report["preview_ready"] is preview_ready
    assert (report["preview_request_template"] is not None) is preview_ready
    if preview_ready:
        assert any("render_preview_batch" in action for action in report["next_actions"])
    else:
        assert report["status"] == "warning"
        assert any("--capability-profile review" in action for action in report["next_actions"])
        assert any(action["code"] == "select_preview_capability_profile" for action in report["remediation_actions"])
        assert all("render_preview_batch" not in action for action in report["diagnostics"]["next_actions"])


def test_server_module_is_a_thin_composition_facade() -> None:
    source = Path(server_module.__file__).read_text(encoding="utf-8")

    assert "@mcp." not in source
    assert len(source.splitlines()) <= 220


def test_server_exposes_documented_tool_names() -> None:
    server = create_mcp_server()

    tool_names = set(server._tool_manager._tools)

    assert {
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
        "validate_preview_request",
        "plan_dataset_onboarding",
        "build_review_packet",
        "inspect_dataset_quality",
    }.issubset(tool_names)


def test_host_smoke_tool_allows_direct_call_without_resource_read() -> None:
    server = create_mcp_server()

    description = server._tool_manager._tools["run_host_smoke_check"].description

    assert description is not None
    assert "resource" in description.lower()
    assert "optional" in description.lower()


def test_server_exposes_agent_workflow_prompts() -> None:
    server = create_mcp_server()

    prompt_names = set(server._prompt_manager._prompts)

    assert {
        "build_robustness_augmentation_session",
        "run_first_preview_review",
        "compare_preview_runs_for_feedback",
        "tune_pipeline_from_preview_feedback",
        "export_reproducible_pipeline",
    }.issubset(prompt_names)


def test_server_exposes_agent_workflow_resources() -> None:
    server = create_mcp_server()

    resources = server._resource_manager._resources
    workflow_catalog = cast("Any", resources["albumentationsx://workflows/catalog"]).fn()
    preview_tuning = cast("Any", resources["albumentationsx://workflows/preview-tuning"]).fn()
    task_profiles = cast("Any", resources["albumentationsx://workflows/task-profiles"]).fn()
    quality_profiles = cast("Any", resources["albumentationsx://quality-profiles"]).fn()
    recipes_catalog = cast("Any", resources["albumentationsx://recipes/catalog"]).fn()
    diagnostics_guide = cast("Any", resources["albumentationsx://diagnostics/guide"]).fn()
    client_smoke_example = cast("Any", resources["albumentationsx://examples/client-smoke"]).fn()
    first_preview_example = cast("Any", resources["albumentationsx://examples/first-preview"]).fn()
    distortion_review_example = cast("Any", resources["albumentationsx://examples/distortion-review"]).fn()
    dataset_onboarding_example = cast("Any", resources["albumentationsx://examples/dataset-onboarding"]).fn()
    diagnostics_example = cast("Any", resources["albumentationsx://examples/diagnostics"]).fn()
    review_loop_example = cast("Any", resources["albumentationsx://examples/review-loop"]).fn()
    report_handoff_example = cast("Any", resources["albumentationsx://examples/report-handoff"]).fn()
    capabilities = cast("Any", resources["albumentationsx://capabilities"]).fn()

    assert "preview-tuning" in workflow_catalog
    assert "recommend_pipeline" in preview_tuning
    assert "classification-robustness" in task_profiles
    assert "segmentation" in quality_profiles
    assert "object_detection" in recipes_catalog
    assert "diagnose_environment" in diagnostics_guide
    assert "is AlbumentationsX MCP connected?" in client_smoke_example
    assert "run the first AlbumentationsX preview" in first_preview_example
    assert "make distorted versions, but example 8 is too noisy" in distortion_review_example
    assert "plan the first AlbumentationsX dataset preview" in dataset_onboarding_example
    assert "why does AlbumentationsX MCP preview not work?" in diagnostics_example
    assert "record_preview_feedback" in review_loop_example
    assert "export_preview_report" in report_handoff_example
    assert "adjust_pipeline" in preview_tuning
    expected_capability_terms = {
        "workflow_resources",
        "compare_preview_runs_for_feedback",
        "interpret_preview_feedback",
        "plan_preview_review",
        "run_first_preview_review",
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
        "record_preview_feedback",
        "list_preview_feedback",
        "record_tuning_decision",
        "export_tuning_report",
        "export_preview_report",
        "diagnose_environment",
        "run_host_smoke_check",
        "validate_preview_request",
        "plan_dataset_onboarding",
        "build_review_packet",
        "inspect_dataset_quality",
        "albumentationsx://diagnostics/guide",
        "albumentationsx://recipes/catalog",
        "albumentationsx://examples/client-smoke",
        "albumentationsx://examples/first-preview",
        "albumentationsx://examples/distortion-review",
        "albumentationsx://examples/dataset-onboarding",
        "albumentationsx://examples/diagnostics",
        "albumentationsx://examples/review-loop",
        "albumentationsx://examples/report-handoff",
        "albumentationsx://workflows/task-profiles",
    }
    for term in expected_capability_terms:
        assert term in capabilities


def test_server_exports_matching_tuning_session_artifacts(tmp_path: Path) -> None:
    store = InteractiveTuningSessionStore(tmp_path)
    session = store.start_session(task="classification", targets=["image"], baseline_run_id="baseline-a")
    store.record_step(
        session.session_id,
        summary=TuningSessionSummary(
            baseline_run_id="baseline-a",
            candidate_run_id="candidate-a",
            feedback_tags=["too_noisy:low"],
            accepted=True,
            export_ready=True,
            recommended_next_tool="export_pipeline",
            rationale="accepted",
            quality_score=96.0,
            quality_risk="low",
        ),
        reviewer_notes=["candidate keeps object readable"],
    )

    artifacts = server_module._export_matching_tuning_session_artifacts(
        store,
        baseline_run_id="baseline-a",
        candidate_run_ids={"candidate-a"},
    )

    assert len(artifacts) == 1
    assert artifacts[0].uri.startswith("artifact://tuning-sessions/")
    assert artifacts[0].mime_type == "text/markdown"
