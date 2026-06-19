import pytest

from albumentationsx_mcp.workflows import (
    get_agent_workflow,
    get_host_example,
    get_task_profile,
    list_agent_workflows,
    list_host_examples,
    list_task_profiles,
)


def test_agent_workflow_catalog_contains_preview_tuning_contract() -> None:
    workflows = list_agent_workflows()
    preview_tuning = get_agent_workflow("preview-tuning")

    assert any(workflow.name == "preview-tuning" for workflow in workflows)
    assert preview_tuning.goal.startswith("Tune")
    assert preview_tuning.recommended_tools[:4] == [
        "recommend_pipeline",
        "validate_pipeline",
        "explain_pipeline",
        "render_preview",
    ]
    assert "start_tuning_session" in preview_tuning.recommended_tools
    assert "record_tuning_session_step" in preview_tuning.recommended_tools
    assert "export_tuning_session" in preview_tuning.recommended_tools
    assert "ask the user for structured feedback" in " ".join(step.instruction for step in preview_tuning.steps)
    assert "export_pipeline" in preview_tuning.completion_criteria[-1]


def test_unknown_agent_workflow_is_rejected() -> None:
    with pytest.raises(KeyError, match="Unknown agent workflow"):
        get_agent_workflow("missing")


def test_task_profiles_cover_common_computer_vision_workflows() -> None:
    profiles = list_task_profiles()
    profile_names = {profile.name for profile in profiles}
    detection = get_task_profile("detection-annotation-review")

    assert {
        "classification-robustness",
        "detection-annotation-review",
        "segmentation-mask-review",
        "ocr-document-robustness",
    }.issubset(profile_names)
    assert detection.workflow == "annotation-preview"
    assert "bboxes" in detection.targets
    assert "too_distorted" in detection.feedback_tags


def test_host_examples_cover_review_loop_and_report_handoff() -> None:
    examples = list_host_examples()
    client_smoke = get_host_example("client-smoke")
    first_preview = get_host_example("first-preview")
    distortion_review = get_host_example("distortion-review")
    review_loop = get_host_example("review-loop")
    report_handoff = get_host_example("report-handoff")

    assert {example.name for example in examples} >= {
        "client-smoke",
        "first-preview",
        "distortion-review",
        "review-loop",
        "report-handoff",
    }
    assert client_smoke.trigger_phrase == "is AlbumentationsX MCP connected?"
    assert [step.tool for step in client_smoke.steps] == [
        "albumentationsx://capabilities",
        "albumentationsx://recipes/catalog",
        "recommend_recipe",
        "validate_pipeline",
        "run_host_smoke_check",
    ]
    assert first_preview.trigger_phrase == "run the first AlbumentationsX preview"
    assert [step.tool for step in first_preview.steps] == [
        "albumentationsx://examples/client-smoke",
        "run_host_smoke_check",
        "validate_preview_request",
        "render_preview_batch",
    ]
    assert distortion_review.trigger_phrase == "make distorted versions, but example 8 is too noisy"
    assert [step.tool for step in distortion_review.steps] == [
        "albumentationsx://examples/first-preview",
        "render_preview_batch",
        "record_preview_feedback",
        "adjust_pipeline",
        "compare_preview_runs",
        "export_pipeline",
    ]
    assert review_loop.trigger_phrase == "example 8 is too noisy"
    assert [step.tool for step in review_loop.steps[:3]] == [
        "record_preview_feedback",
        "list_preview_feedback",
        "adjust_pipeline",
    ]
    assert "export_preview_report" in [step.tool for step in report_handoff.steps]
