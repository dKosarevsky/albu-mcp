"""Agent-legible workflow contracts exposed through MCP resources."""

from __future__ import annotations

from albumentationsx_mcp.models import StrictModel


class WorkflowStep(StrictModel):
    """One ordered step in an MCP workflow an assistant can follow."""

    order: int
    instruction: str
    tool: str | None = None
    expected_result: str


class AgentWorkflow(StrictModel):
    """A compact, machine-readable MCP workflow guide."""

    name: str
    goal: str
    recommended_tools: list[str]
    steps: list[WorkflowStep]
    safety_notes: list[str]
    completion_criteria: list[str]


_WORKFLOWS = {
    "preview-tuning": AgentWorkflow(
        name="preview-tuning",
        goal="Tune an AlbumentationsX augmentation pipeline from deterministic previews and structured user feedback.",
        recommended_tools=[
            "recommend_pipeline",
            "validate_pipeline",
            "explain_pipeline",
            "render_preview",
            "list_feedback_tags",
            "adjust_pipeline",
            "export_pipeline",
        ],
        steps=[
            WorkflowStep(
                order=1,
                tool="recommend_pipeline",
                instruction=(
                    "Create a conservative starter pipeline for the task, target types, and requested intensity."
                ),
                expected_result="A typed pipeline spec with transform names, parameters, and probabilities.",
            ),
            WorkflowStep(
                order=2,
                tool="validate_pipeline",
                instruction="Validate the pipeline before previewing it and stop on validation errors.",
                expected_result="A valid normalized pipeline or machine-readable validation errors.",
            ),
            WorkflowStep(
                order=3,
                tool="explain_pipeline",
                instruction="Explain likely visual effects and risks before asking the user to review previews.",
                expected_result="Risk level, transform effects, warnings, and suggested feedback tags.",
            ),
            WorkflowStep(
                order=4,
                tool="render_preview",
                instruction="Render a small deterministic preview batch inside the configured artifact root.",
                expected_result="Preview images, contact sheet, manifest, and artifact hashes.",
            ),
            WorkflowStep(
                order=5,
                tool="list_feedback_tags",
                instruction="Show the relevant feedback tag vocabulary and ask the user for structured feedback.",
                expected_result="Tags such as too_noisy, too_blurry, too_distorted, or acceptable.",
            ),
            WorkflowStep(
                order=6,
                tool="adjust_pipeline",
                instruction=(
                    "Apply structured feedback tags, revalidate, and re-render until the user accepts the preview set."
                ),
                expected_result="An adjusted pipeline that reduces the observed preview issue.",
            ),
            WorkflowStep(
                order=7,
                tool="export_pipeline",
                instruction="Export the accepted pipeline in the requested format with the preview manifest run id.",
                expected_result="Reproducible Python, JSON, or YAML pipeline content.",
            ),
        ],
        safety_notes=[
            "Only read local input files allowed by ALBU_MCP_ALLOWED_ROOTS or --allowed-root.",
            "Do not overwrite datasets; preview artifacts are written only under the artifact root.",
            "Use deterministic seeds when comparing variants or discussing individual examples.",
        ],
        completion_criteria=[
            "The user has accepted a preview set or supplied a final feedback tag.",
            "validate_pipeline reports no errors for the final pipeline.",
            "export_pipeline has produced the requested reproducible representation.",
        ],
    ),
    "annotation-preview": AgentWorkflow(
        name="annotation-preview",
        goal="Check whether image, bbox, keypoint, or mask augmentations remain visually coherent after transforms.",
        recommended_tools=[
            "validate_pipeline",
            "render_preview",
            "get_preview_manifest",
            "explain_pipeline",
        ],
        steps=[
            WorkflowStep(
                order=1,
                tool="validate_pipeline",
                instruction="Validate target-specific pipeline settings before rendering annotation overlays.",
                expected_result="A valid pipeline with bbox_params, keypoint_params, or mask-compatible transforms.",
            ),
            WorkflowStep(
                order=2,
                tool="render_preview",
                instruction="Render previews with annotations and inspect overlay_contact_sheet when available.",
                expected_result="Image previews, overlay previews, contact sheets, and a manifest.",
            ),
            WorkflowStep(
                order=3,
                tool="explain_pipeline",
                instruction="Explain geometric risks if annotations look clipped, shifted, or too distorted.",
                expected_result="Target-aware warnings and useful feedback tags.",
            ),
        ],
        safety_notes=[
            "Resolve mask paths through the same allowlist as input images.",
            "Keep label fields aligned with bbox_params before previewing.",
        ],
        completion_criteria=[
            "Overlay artifacts show objects, masks, and keypoints remain interpretable.",
            "The final pipeline validates for the requested target spec.",
        ],
    ),
}


def list_agent_workflows() -> list[AgentWorkflow]:
    """Return all built-in agent workflow guides."""
    return sorted(_WORKFLOWS.values(), key=lambda workflow: workflow.name)


def get_agent_workflow(name: str) -> AgentWorkflow:
    """Return one agent workflow guide by stable name."""
    try:
        return _WORKFLOWS[name]
    except KeyError as exc:
        msg = f"Unknown agent workflow: {name}"
        raise KeyError(msg) from exc
