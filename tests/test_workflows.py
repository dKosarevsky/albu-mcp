import pytest

from albumentationsx_mcp.workflows import get_agent_workflow, list_agent_workflows


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
    assert "ask the user for structured feedback" in " ".join(step.instruction for step in preview_tuning.steps)
    assert "export_pipeline" in preview_tuning.completion_criteria[-1]


def test_unknown_agent_workflow_is_rejected() -> None:
    with pytest.raises(KeyError, match="Unknown agent workflow"):
        get_agent_workflow("missing")
