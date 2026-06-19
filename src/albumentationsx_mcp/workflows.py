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
            "start_tuning_session",
            "adjust_pipeline",
            "record_tuning_session_step",
            "export_tuning_session",
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
                tool="start_tuning_session",
                instruction="Start an interactive tuning session linked to the baseline preview run.",
                expected_result=(
                    "A persistent session id with task, targets, baseline run id, quality profile, and next actions."
                ),
            ),
            WorkflowStep(
                order=7,
                tool="adjust_pipeline",
                instruction=(
                    "Apply structured feedback tags, revalidate, and re-render until the user accepts the preview set."
                ),
                expected_result="An adjusted pipeline that reduces the observed preview issue.",
            ),
            WorkflowStep(
                order=8,
                tool="record_tuning_session_step",
                instruction="Record each candidate comparison, feedback tags, reviewer notes, and acceptance state.",
                expected_result=(
                    "The tuning session contains an ordered step and points to the accepted candidate when accepted."
                ),
            ),
            WorkflowStep(
                order=9,
                tool="export_tuning_session",
                instruction="Export the interactive session as Markdown for handoff or JSON for automation.",
                expected_result=(
                    "A compact session record with baseline, candidates, feedback, score, risk, and final status."
                ),
            ),
            WorkflowStep(
                order=10,
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
            HostExampleStep(
                order=5,
                tool="run_host_smoke_check",
                instruction="Call run_host_smoke_check to confirm preview readiness and get a safe request template.",
                expected_result="A report with preview_ready=true and a render_preview_batch request template.",
            ),
        ],
        success_criteria=[
            "The host can read static resources without filesystem access errors.",
            "recommend_recipe returns a typed pipeline and explanation list.",
            "validate_pipeline accepts the recommended pipeline before preview rendering begins.",
            "run_host_smoke_check returns preview_ready=true and a small render_preview_batch template.",
        ],
    ),
    "first-preview": HostExample(
        name="first-preview",
        goal="Run the first local preview only after host smoke and preview request validation pass.",
        trigger_phrase="run the first AlbumentationsX preview",
        steps=[
            HostExampleStep(
                order=1,
                tool="albumentationsx://examples/client-smoke",
                instruction="Read the client smoke playbook so the host follows the supported setup flow.",
                expected_result="A playbook that starts with capability checks and ends with run_host_smoke_check.",
            ),
            HostExampleStep(
                order=2,
                tool="run_host_smoke_check",
                instruction=(
                    "Call run_host_smoke_check for the user's task and continue only when preview_ready is true."
                ),
                expected_result="A report with preview_ready=true and a preview_request_template.",
            ),
            HostExampleStep(
                order=3,
                tool="validate_preview_request",
                instruction=(
                    "Copy preview_request_template.request, replace the placeholder input path with one small image "
                    "under an allowed root, and validate the filled request."
                ),
                expected_result="A valid request with normalized_request and no remediation_actions.",
            ),
            HostExampleStep(
                order=4,
                tool="render_preview_batch",
                instruction="Render the validated request and show the contact sheet before increasing scope.",
                expected_result="A preview run with contact sheet artifacts and a readable manifest.",
            ),
        ],
        success_criteria=[
            "The host does not render until run_host_smoke_check returns preview_ready=true.",
            "validate_preview_request returns valid=true for the filled local image path.",
            "render_preview_batch uses the validated request and writes artifacts under the artifact root.",
            "The user reviews the first contact sheet before changing intensity, batch size, or variants.",
        ],
    ),
    "distortion-review": HostExample(
        name="distortion-review",
        goal=(
            "Create distorted robustness previews, capture concrete user rejection such as one noisy example, "
            "then render a safer candidate and export only after acceptance."
        ),
        trigger_phrase="make distorted versions, but example 8 is too noisy",
        steps=[
            HostExampleStep(
                order=1,
                tool="albumentationsx://examples/first-preview",
                instruction="Start with the first-preview playbook so local paths are validated before rendering.",
                expected_result="Host smoke and validate_preview_request pass before preview rendering starts.",
            ),
            HostExampleStep(
                order=2,
                tool="render_preview_batch",
                instruction=("Render a small deterministic set of variants for the user's requested robustness task."),
                expected_result="A contact sheet and manifest the user can inspect before increasing scope.",
            ),
            HostExampleStep(
                order=3,
                tool="record_preview_feedback",
                instruction=(
                    "When the user says an example is too noisy or unrecognizable, record the exact image index, "
                    "variant index, feedback tags, and note."
                ),
                expected_result="A concrete feedback record such as too_noisy:high for example 8.",
            ),
            HostExampleStep(
                order=4,
                tool="adjust_pipeline",
                instruction="Use recorded feedback tags to reduce destructive noise, distortion, or color shift.",
                expected_result="A safer candidate pipeline that preserves the task and targets.",
            ),
            HostExampleStep(
                order=5,
                tool="compare_preview_runs",
                instruction="Compare baseline and candidate runs before asking the user to accept the next set.",
                expected_result="Quality summary, deltas, and suggested feedback tags for the candidate.",
            ),
            HostExampleStep(
                order=6,
                tool="export_pipeline",
                instruction="Export only the accepted candidate pipeline in the requested format.",
                expected_result="A reproducible AlbumentationsX pipeline tied to the accepted preview run.",
            ),
        ],
        success_criteria=[
            "The host never renders paths that fail validate_preview_request.",
            "Concrete user feedback is recorded against the exact reviewed preview example.",
            "The adjusted candidate is compared against the same local inputs before export.",
            "The exported pipeline corresponds to a user-accepted preview run.",
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
    "diagnostics": HostExample(
        name="diagnostics",
        goal="Diagnose AlbumentationsX MCP setup before rendering local previews.",
        trigger_phrase="why does AlbumentationsX MCP preview not work?",
        steps=[
            HostExampleStep(
                order=1,
                tool="albumentationsx://diagnostics/guide",
                instruction="Read the diagnostics guide before interpreting setup checks.",
                expected_result="A machine-readable playbook with checks, success criteria, and failure actions.",
            ),
            HostExampleStep(
                order=2,
                tool="diagnose_environment",
                instruction="Call diagnose_environment with include_write_probe=true.",
                expected_result="A structured status report with checks, warnings, environment, and next actions.",
            ),
            HostExampleStep(
                order=3,
                tool="albumentationsx://capabilities",
                instruction="Confirm local roots, preview limits, tools, prompts, and workflow resources.",
                expected_result="The configured roots and public MCP surface match the expected setup.",
            ),
        ],
        success_criteria=[
            "diagnose_environment returns status ok before preview rendering begins.",
            "Every warning or error is mapped to a concrete next action.",
            "The host confirms allowed_roots and artifact_root match the user's intended review folder.",
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
