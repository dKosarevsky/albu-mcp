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


class TaskWorkflowProfile(StrictModel):
    """Task-specific workflow defaults for MCP hosts."""

    name: str
    task: str
    workflow: str
    targets: list[str]
    recommended_intensity: str
    feedback_tags: list[str]
    notes: list[str]


class HostExampleStep(StrictModel):
    """One tool step in a canonical MCP host example."""

    order: int
    tool: str
    instruction: str
    expected_result: str


class HostExample(StrictModel):
    """Machine-readable host playbook for common user interactions."""

    name: str
    goal: str
    trigger_phrase: str
    steps: list[HostExampleStep]
    success_criteria: list[str]


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

_HOST_EXAMPLES = {
    "client-smoke": HostExample(
        name="client-smoke",
        goal="Verify that an MCP host can see AlbumentationsX MCP resources and call a safe typed tool.",
        trigger_phrase="is AlbumentationsX MCP connected?",
        steps=[
            HostExampleStep(
                order=1,
                tool="albumentationsx://capabilities",
                instruction=(
                    "Read server capabilities and confirm the expected tools and workflow resources are present."
                ),
                expected_result=(
                    "A compact JSON object with tools, workflow_resources, preview limits, and local roots."
                ),
            ),
            HostExampleStep(
                order=2,
                tool="albumentationsx://recipes/catalog",
                instruction="Read the recipe catalog before choosing a starter workflow.",
                expected_result=(
                    "Task-aware recipes including classification, detection, segmentation, OCR, and balanced."
                ),
            ),
            HostExampleStep(
                order=3,
                tool="recommend_recipe",
                instruction="Call recommend_recipe with task classification and intensity low.",
                expected_result="A conservative classification pipeline with explanations and recommended next tools.",
            ),
            HostExampleStep(
                order=4,
                tool="validate_pipeline",
                instruction="Validate the recommended pipeline before rendering any local images.",
                expected_result="A valid normalized pipeline or machine-readable validation errors.",
            ),
        ],
        success_criteria=[
            "The host can read static resources without filesystem access errors.",
            "recommend_recipe returns a typed pipeline and explanation list.",
            "validate_pipeline accepts the recommended pipeline before preview rendering begins.",
        ],
    ),
    "review-loop": HostExample(
        name="review-loop",
        goal="Turn concrete user feedback about one preview example into structured tags and a safer next render.",
        trigger_phrase="example 8 is too noisy",
        steps=[
            HostExampleStep(
                order=1,
                tool="record_preview_feedback",
                instruction=(
                    "Persist the user note against the reviewed candidate run, zero-based image index, "
                    "zero-based variant index, and selected structured feedback tags."
                ),
                expected_result="A feedback record with review_target and recommended_next_tool.",
            ),
            HostExampleStep(
                order=2,
                tool="list_preview_feedback",
                instruction=(
                    "List feedback for the same run and reuse aggregated_feedback_tags as the adjustment input."
                ),
                expected_result="Newest-first feedback records and deduplicated feedback tags.",
            ),
            HostExampleStep(
                order=3,
                tool="adjust_pipeline",
                instruction=(
                    "Apply the recorded tags to the current candidate pipeline before rendering a lighter version."
                ),
                expected_result="An adjusted pipeline that responds to the concrete reviewed example.",
            ),
            HostExampleStep(
                order=4,
                tool="render_preview_batch",
                instruction="Re-render with the same input images, variants, and deterministic seed family.",
                expected_result="A comparable preview run with a new contact sheet.",
            ),
        ],
        success_criteria=[
            "The feedback record points to the same preview run the user reviewed.",
            "The host uses structured tags from the feedback journal instead of free-form text.",
            "The next candidate is rendered against the same inputs before comparison.",
        ],
    ),
    "report-handoff": HostExample(
        name="report-handoff",
        goal="Create a visual handoff after ranking candidates and recording decisions.",
        trigger_phrase="send me the final preview report",
        steps=[
            HostExampleStep(
                order=1,
                tool="score_dataset_preview_candidates",
                instruction="Score the candidate set with the task-appropriate quality profile.",
                expected_result="A dataset-level score with ranking, metric stats, and finding counts.",
            ),
            HostExampleStep(
                order=2,
                tool="record_tuning_decision",
                instruction="Persist the accepted or rejected outcome with reviewer notes.",
                expected_result="A local tuning decision linked to baseline and candidate run ids.",
            ),
            HostExampleStep(
                order=3,
                tool="export_preview_report",
                instruction="Export HTML for visual review or Markdown for text-first handoff.",
                expected_result="A report artifact with contact sheet thumbnails or image refs.",
            ),
        ],
        success_criteria=[
            "The report includes baseline and candidate contact sheets.",
            "The report includes ranking, metric ranges, finding counts, and matching decisions.",
            "The host exports the pipeline only after the user accepts the candidate.",
        ],
    ),
}

_TASK_PROFILES = {
    "classification-robustness": TaskWorkflowProfile(
        name="classification-robustness",
        task="classification",
        workflow="preview-tuning",
        targets=["image"],
        recommended_intensity="medium",
        feedback_tags=["too_noisy", "too_blurry", "object_unrecognizable"],
        notes=[
            "Start with a small class-balanced image set.",
            "Prefer severity suffixes only after the user points to concrete preview examples.",
        ],
    ),
    "detection-annotation-review": TaskWorkflowProfile(
        name="detection-annotation-review",
        task="object_detection",
        workflow="annotation-preview",
        targets=["image", "bboxes"],
        recommended_intensity="low",
        feedback_tags=["too_distorted", "object_unrecognizable"],
        notes=[
            "Render overlays before accepting geometric transforms.",
            "Keep bbox label fields aligned with bbox_params.",
        ],
    ),
    "segmentation-mask-review": TaskWorkflowProfile(
        name="segmentation-mask-review",
        task="segmentation",
        workflow="annotation-preview",
        targets=["image", "mask"],
        recommended_intensity="low",
        feedback_tags=["too_distorted", "too_blurry", "object_unrecognizable"],
        notes=[
            "Use mask overlays to confirm boundaries stay aligned.",
            "Avoid high geometric severity until annotation overlays look stable.",
        ],
    ),
    "ocr-document-robustness": TaskWorkflowProfile(
        name="ocr-document-robustness",
        task="ocr",
        workflow="preview-tuning",
        targets=["image"],
        recommended_intensity="low",
        feedback_tags=["too_blurry", "too_distorted", "object_unrecognizable"],
        notes=[
            "Review text legibility before increasing perspective or compression.",
            "Use high severity feedback when characters become unreadable.",
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


def list_task_profiles() -> list[TaskWorkflowProfile]:
    """Return task-specific workflow profiles."""
    return sorted(_TASK_PROFILES.values(), key=lambda profile: profile.name)


def get_task_profile(name: str) -> TaskWorkflowProfile:
    """Return one task workflow profile by stable name."""
    try:
        return _TASK_PROFILES[name]
    except KeyError as exc:
        msg = f"Unknown task workflow profile: {name}"
        raise KeyError(msg) from exc


def list_host_examples() -> list[HostExample]:
    """Return canonical host interaction examples."""
    return sorted(_HOST_EXAMPLES.values(), key=lambda example: example.name)


def get_host_example(name: str) -> HostExample:
    """Return one host interaction example by stable name."""
    try:
        return _HOST_EXAMPLES[name]
    except KeyError as exc:
        msg = f"Unknown host example: {name}"
        raise KeyError(msg) from exc
