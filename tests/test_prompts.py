from albumentationsx_mcp.prompts import run_first_preview_review


def test_first_preview_prompt_uses_workflow_fallback_when_resources_are_not_exposed() -> None:
    prompt = run_first_preview_review()

    assert "when the host exposes resource reads" in prompt
    assert "if resource reads are unavailable, call get_workflow_example" in prompt
    assert 'example_id="client-smoke"' in prompt
    assert "otherwise call run_host_smoke_check directly" not in prompt
    assert "Continue only when preview_ready is true" in prompt
