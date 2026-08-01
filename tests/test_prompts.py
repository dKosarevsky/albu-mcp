import ast
import re
from pathlib import Path

import pytest

from albumentationsx_mcp.guided_preview import GuidedPreviewRequest
from albumentationsx_mcp.prompts import run_first_preview_review

_COMMON_REVIEW_TOOLS = {
    "adjust_pipeline",
    "compare_preview_runs",
    "export_pipeline",
    "render_preview_batch",
    "run_host_smoke_check",
    "trace_preview_variant",
    "validate_preview_request",
}


def test_first_preview_prompt_defaults_to_guided_workflow_when_tool_is_available() -> None:
    prompt = run_first_preview_review()

    assert "when the host exposes resource reads" in prompt
    assert "if resource reads are unavailable, call get_workflow_example" in prompt
    assert 'example_id="client-smoke"' in prompt
    assert "otherwise call run_host_smoke_check directly" not in prompt
    assert "Continue only when preview_ready is true" in prompt
    assert "run_first_preview" in prompt
    assert "validate_preview_request" not in prompt
    assert "render_preview_batch" not in prompt
    assert prompt.index("run_host_smoke_check") < prompt.index("run_first_preview")
    assert prompt.index("run_first_preview") < prompt.index("contact sheet")
    assert prompt.index("contact sheet") < prompt.index("trace_preview_variant")
    assert prompt.index("trace_preview_variant") < prompt.index("adjust_pipeline")
    assert prompt.index("adjust_pipeline") < prompt.index("compare_preview_runs")
    assert prompt.index("compare_preview_runs") < prompt.index("export_pipeline")


@pytest.mark.parametrize(
    ("targets", "expected"),
    [
        (None, ["image"]),
        (" image, bboxes ", ["image", "bboxes"]),
        (" , ", None),
    ],
    ids=["default", "comma-separated", "empty"],
)
def test_first_preview_prompt_emits_schema_valid_guided_targets(
    targets: str | None,
    expected: list[str] | None,
) -> None:
    prompt = run_first_preview_review() if targets is None else run_first_preview_review(targets=targets)
    guided_call = prompt.split("Call run_first_preview", maxsplit=1)[1].split("Show the returned", maxsplit=1)[0]
    match = re.search(r"\btargets=(\[[^]]*\])", guided_call)
    payload: dict[str, object] = {"dataset_path": Path("/absolute/path/to/images")}
    if expected is None:
        assert "targets=" not in guided_call
    else:
        assert match is not None
        payload["targets"] = ast.literal_eval(match.group(1))

    request = GuidedPreviewRequest.model_validate(payload)

    assert request.targets == expected


def test_first_preview_prompt_uses_manual_review_fallback_without_guided_tool() -> None:
    prompt = run_first_preview_review(available_tools=_COMMON_REVIEW_TOOLS)

    assert "run_first_preview" not in prompt
    assert prompt.index("run_host_smoke_check") < prompt.index("preview_request_template")
    assert prompt.index("preview_request_template") < prompt.index("validate_preview_request")
    assert prompt.index("validate_preview_request") < prompt.index("render_preview_batch")
    assert prompt.index("render_preview_batch") < prompt.index("contact sheet")
    assert prompt.index("contact sheet") < prompt.index("trace_preview_variant")
    assert prompt.index("trace_preview_variant") < prompt.index("adjust_pipeline")


def test_first_preview_prompt_omits_trace_when_trace_tool_is_unavailable() -> None:
    prompt = run_first_preview_review(available_tools=_COMMON_REVIEW_TOOLS - {"trace_preview_variant"})

    assert "trace_preview_variant" not in prompt
