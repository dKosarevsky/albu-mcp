"""Typed contracts used by the AlbumentationsX MCP server."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

ArtifactKind = Literal["image", "manifest", "contact_sheet", "overlay", "overlay_contact_sheet", "report"]
RiskLevel = Literal["low", "medium", "high"]
QualityProfileName = Literal["balanced", "classification", "detection", "segmentation", "ocr"]


class StrictModel(BaseModel):
    """Base model that rejects unknown fields in MCP-facing contracts."""

    model_config = ConfigDict(extra="forbid")


class ConstraintInfo(StrictModel):
    """Numeric and collection constraints extracted from transform metadata."""

    ge: float | None = None
    le: float | None = None
    gt: float | None = None
    lt: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    multiple_of: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    pattern: str | None = None
    validators: list[str] = Field(default_factory=list)
    validator_info: dict[str, Any] = Field(default_factory=dict)


class ParameterInfo(StrictModel):
    """Serializable parameter description for one transform argument."""

    name: str
    type_hint: str | list[Any]
    default: Any = None
    description: str | None = None
    constraints: ConstraintInfo | None = None


class TransformMetadata(StrictModel):
    """Compact transform metadata exposed through MCP resources and tools."""

    name: str
    module: str
    transform_type: Literal["image_only", "dual", "transforms_3d", "unknown"]
    targets: list[str]
    parameters: dict[str, ParameterInfo] = Field(default_factory=dict)
    docstring_short: str | None = None
    supported_bbox_types: list[str] | None = None


class TransformSpec(StrictModel):
    """One transform invocation in an augmentation pipeline."""

    name: str
    params: dict[str, Any] = Field(default_factory=dict)
    p: float | None = Field(default=None, ge=0.0, le=1.0)


class ComposeSpec(StrictModel):
    """Serializable AlbumentationsX Compose pipeline specification."""

    transforms: list[TransformSpec] = Field(min_length=1)
    bbox_params: dict[str, Any] | None = None
    keypoint_params: dict[str, Any] | None = None
    additional_targets: dict[str, str] = Field(default_factory=dict)
    seed: int | None = None
    is_check_shapes: bool = True
    strict: bool = True


class TargetSpec(StrictModel):
    """Requested data targets for a pipeline validation or recommendation."""

    targets: list[str] = Field(default_factory=lambda: ["image"], min_length=1)
    bbox_format: str | None = None
    keypoint_format: str | None = None
    bbox_type: Literal["hbb", "obb"] | None = None


class ValidationIssue(StrictModel):
    """Machine-readable validation problem."""

    code: str
    path: str
    message: str


class PipelineValidationReport(StrictModel):
    """Validation result returned by MCP tools."""

    valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    normalized_pipeline: dict[str, Any] | None = None


class ExportResult(StrictModel):
    """Exported pipeline representation."""

    format: Literal["python", "json", "yaml"]
    content: str


class MaskRLE(StrictModel):
    """Serializable COCO-style mask RLE."""

    counts: list[int] | str
    size: list[int] = Field(min_length=2, max_length=2)


class ImageAnnotations(StrictModel):
    """Optional annotations supplied for one preview input image."""

    bboxes: list[list[float]] = Field(default_factory=list)
    bbox_labels: list[str | int] = Field(default_factory=list)
    keypoints: list[list[float]] = Field(default_factory=list)
    mask_path: Path | None = None
    mask_polygons: list[list[list[float]]] = Field(default_factory=list)
    mask_rles: list[MaskRLE] = Field(default_factory=list)


class PreviewRequest(StrictModel):
    """Preview rendering request with bounded work size."""

    input_paths: list[Path] = Field(min_length=1, max_length=32)
    annotations: list[ImageAnnotations | None] | None = None
    pipeline: ComposeSpec
    variants_per_image: int = Field(default=4, ge=1, le=16)
    seed: int | None = None
    max_side: int = Field(default=1024, ge=64, le=4096)


class ArtifactRef(StrictModel):
    """Reference to an artifact written by the preview renderer."""

    kind: ArtifactKind
    uri: str
    path: str
    mime_type: str
    sha256: str
    size_bytes: int


class PreviewResult(StrictModel):
    """Preview rendering output."""

    run_id: str
    artifacts: list[ArtifactRef]
    manifest: ArtifactRef
    pipeline: dict[str, Any]


class PreviewRunSummary(StrictModel):
    """Queryable summary for one rendered preview run."""

    run_id: str
    created_at: str
    manifest_path: str
    artifact_count: int
    input_count: int
    contact_sheet_path: str | None = None


class PreviewManifestSummary(StrictModel):
    """Agent-legible summary embedded in and derived from preview manifests."""

    run_id: str
    created_at: str
    input_count: int
    variants_per_image: int | None = None
    seed: int | None = None
    effective_seeds: list[int] = Field(default_factory=list)
    max_side: int | None = None
    transform_count: int
    transform_names: list[str]
    artifact_counts: dict[str, int] = Field(default_factory=dict)
    contact_sheet_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    annotation_observation_count: int = 0


class ImageQualityMetrics(StrictModel):
    """Simple local image quality metrics for one preview artifact."""

    path: str
    brightness_mean: float
    contrast_std: float
    sharpness_score: float
    saturation_mean: float
    colorfulness_score: float
    entropy_bits: float
    clipping_fraction: float


class ImageQualityAggregate(StrictModel):
    """Aggregate quality metrics for a preview run."""

    image_count: int
    brightness_mean: float | None = None
    contrast_std: float | None = None
    sharpness_score: float | None = None
    saturation_mean: float | None = None
    colorfulness_score: float | None = None
    entropy_bits: float | None = None
    clipping_fraction: float | None = None


class QualityFinding(StrictModel):
    """Machine-readable local preview quality finding."""

    code: str
    severity: RiskLevel
    message: str
    metric: str
    value: float
    baseline_value: float | None = None


class QualityProfileInfo(StrictModel):
    """Named local quality profile for task-aware preview review."""

    name: QualityProfileName
    description: str
    task_hints: list[str] = Field(default_factory=list)
    thresholds: dict[str, float] = Field(default_factory=dict)


class RecipeInfo(StrictModel):
    """Agent-legible task recipe metadata."""

    name: str
    description: str
    task_aliases: list[str] = Field(default_factory=list)
    quality_profile: QualityProfileName
    default_targets: list[str] = Field(default_factory=list)
    feedback_tags: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)


class RecipeExplanation(StrictModel):
    """Structured explanation for one recipe recommendation choice."""

    kind: Literal["quality_profile", "targets", "feedback_tags", "workflow"]
    selected: str | list[str]
    rationale: str


class RecipeRecommendation(StrictModel):
    """Task-aware starter recipe and workflow guidance."""

    task: str
    recipe_name: str
    intensity: Literal["low", "medium", "high"]
    targets: list[str] = Field(default_factory=list)
    quality_profile: QualityProfileName
    pipeline: ComposeSpec
    recommended_tools: list[str] = Field(default_factory=list)
    feedback_tags: list[str] = Field(default_factory=list)
    preview_guidance: list[str] = Field(default_factory=list)
    explanations: list[RecipeExplanation] = Field(default_factory=list)
    rationale: str


class AnnotationObservation(StrictModel):
    """Per-variant annotation retention observation recorded in preview manifests."""

    image_index: int
    variant_index: int
    input_bbox_count: int = 0
    output_bbox_count: int = 0
    input_keypoint_count: int = 0
    output_keypoint_count: int = 0
    input_mask_coverage: float | None = None
    output_mask_coverage: float | None = None


class AnnotationQualityAggregate(StrictModel):
    """Aggregate annotation retention metrics for a preview run."""

    observation_count: int
    input_bbox_count: int = 0
    output_bbox_count: int = 0
    bbox_retention_ratio: float | None = None
    input_keypoint_count: int = 0
    output_keypoint_count: int = 0
    keypoint_retention_ratio: float | None = None
    input_mask_coverage_mean: float | None = None
    output_mask_coverage_mean: float | None = None
    mask_coverage_ratio: float | None = None


class PreviewAnnotationQualitySummary(StrictModel):
    """Annotation retention comparison between two preview runs."""

    baseline: AnnotationQualityAggregate
    candidate: AnnotationQualityAggregate
    deltas: dict[str, float] = Field(default_factory=dict)


class PreviewQualitySummary(StrictModel):
    """Quality comparison between baseline and candidate preview runs."""

    quality_profile: QualityProfileName = "balanced"
    baseline: ImageQualityAggregate
    candidate: ImageQualityAggregate
    deltas: dict[str, float] = Field(default_factory=dict)
    findings: list[QualityFinding] = Field(default_factory=list)
    annotation_summary: PreviewAnnotationQualitySummary | None = None


class PreviewReviewGuidance(StrictModel):
    """Actionable review guidance for one suggested feedback tag."""

    feedback_tag: str
    review_focus: str
    rationale: str
    suggested_action: str


class PreviewRunComparison(StrictModel):
    """Comparison of two preview run manifests for feedback-driven tuning."""

    baseline: PreviewManifestSummary
    candidate: PreviewManifestSummary
    pipeline_changed: bool
    inputs_changed: bool
    seed_changed: bool
    artifact_count_delta: int
    review_notes: list[str] = Field(default_factory=list)
    suggested_feedback_tags: list[str] = Field(default_factory=list)
    review_guidance: list[PreviewReviewGuidance] = Field(default_factory=list)
    quality_summary: PreviewQualitySummary | None = None
    quality_warnings: list[str] = Field(default_factory=list)


class TuningSessionSummary(StrictModel):
    """Agent-facing summary for one baseline-to-candidate tuning step."""

    baseline_run_id: str
    candidate_run_id: str
    feedback_tags: list[str] = Field(default_factory=list)
    accepted: bool = False
    export_ready: bool
    recommended_next_tool: Literal[
        "list_feedback_tags",
        "adjust_pipeline",
        "render_preview_batch",
        "export_pipeline",
    ]
    rationale: str
    suggested_feedback_tags: list[str] = Field(default_factory=list)
    quality_deltas: dict[str, float] = Field(default_factory=dict)
    quality_score: float = Field(default=100.0, ge=0.0, le=100.0)
    quality_risk: RiskLevel = "low"
    quality_findings: list[QualityFinding] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)


class ReviewAgentPlan(StrictModel):
    """Host-facing review workflow plan for one baseline-to-candidate preview comparison."""

    baseline_run_id: str
    candidate_run_id: str
    decision: Literal["collect_feedback", "revise_candidate", "rerender_candidate", "accept_candidate"]
    accepted: bool = False
    feedback_tags: list[str] = Field(default_factory=list)
    recommended_next_tool: Literal[
        "list_feedback_tags",
        "adjust_pipeline",
        "render_preview_batch",
        "record_tuning_decision",
    ]
    rationale: str
    review_checklist: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    suggested_feedback_tags: list[str] = Field(default_factory=list)
    quality_deltas: dict[str, float] = Field(default_factory=dict)
    quality_score: float = Field(default=100.0, ge=0.0, le=100.0)
    quality_risk: RiskLevel = "low"
    tuning_summary: TuningSessionSummary


class TuningDecisionRecord(StrictModel):
    """Persisted local tuning decision for one baseline-to-candidate comparison."""

    decision_id: str
    created_at: str
    baseline_run_id: str
    candidate_run_id: str
    feedback_tags: list[str] = Field(default_factory=list)
    accepted: bool = False
    export_ready: bool
    recommended_next_tool: Literal[
        "list_feedback_tags",
        "adjust_pipeline",
        "render_preview_batch",
        "export_pipeline",
    ]
    quality_score: float = Field(ge=0.0, le=100.0)
    quality_risk: RiskLevel
    reviewer_notes: list[str] = Field(default_factory=list)
    summary: TuningSessionSummary


class TuningDecisionList(StrictModel):
    """List response for persisted local tuning decisions."""

    decisions: list[TuningDecisionRecord] = Field(default_factory=list)
    total_count: int
    accepted_count: int
    ranked: bool = False


class TuningDecisionReport(StrictModel):
    """Exported tuning decision report."""

    format: Literal["markdown", "json"]
    content: str
    decision_count: int
    accepted_count: int
    best_candidate_run_id: str | None = None


TuningSessionStatus = Literal["active", "accepted", "rejected", "archived"]


class InteractiveTuningStep(StrictModel):
    """One persisted step in an interactive preview tuning session."""

    step_id: str
    created_at: str
    baseline_run_id: str
    candidate_run_id: str
    feedback_tags: list[str] = Field(default_factory=list)
    accepted: bool = False
    reviewer_notes: list[str] = Field(default_factory=list)
    recommended_next_tool: Literal[
        "list_feedback_tags",
        "adjust_pipeline",
        "render_preview_batch",
        "export_pipeline",
    ]
    quality_score: float = Field(ge=0.0, le=100.0)
    quality_risk: RiskLevel
    summary: TuningSessionSummary


class InteractiveTuningSession(StrictModel):
    """Persisted multi-step interactive preview tuning session."""

    session_id: str
    created_at: str
    updated_at: str
    task: str
    targets: list[str] = Field(default_factory=list)
    quality_profile: QualityProfileName = "balanced"
    status: TuningSessionStatus = "active"
    closed_at: str | None = None
    archived_at: str | None = None
    status_note: str | None = None
    baseline_run_id: str | None = None
    accepted_candidate_run_id: str | None = None
    steps: list[InteractiveTuningStep] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def step_count(self) -> int:
        """Return number of recorded session steps."""
        return len(self.steps)


class InteractiveTuningSessionList(StrictModel):
    """List response for persisted interactive tuning sessions."""

    sessions: list[InteractiveTuningSession] = Field(default_factory=list)
    total_count: int
    active_count: int
    accepted_count: int
    rejected_count: int = 0
    archived_count: int = 0


class InteractiveTuningSessionCleanup(StrictModel):
    """Cleanup response for persisted interactive tuning sessions."""

    deleted_sessions: list[InteractiveTuningSession] = Field(default_factory=list)
    deleted_count: int
    kept_count: int
    protected_active_count: int = 0


class InteractiveTuningSessionExport(StrictModel):
    """Exported interactive tuning session handoff."""

    format: Literal["markdown", "json"]
    content: str
    artifact: ArtifactRef
    session_id: str
    status: TuningSessionStatus
    step_count: int
    accepted_candidate_run_id: str | None = None


class PreviewReportExport(StrictModel):
    """Exported visual preview report artifact."""

    format: Literal["markdown", "html"]
    content: str
    artifact: ArtifactRef
    tuning_session_artifacts: list[ArtifactRef] = Field(default_factory=list)
    baseline_run_id: str
    candidate_count: int
    best_candidate_run_id: str | None = None


class PreviewFeedbackInput(StrictModel):
    """User feedback for one concrete preview example."""

    run_id: str
    image_index: int = Field(ge=0)
    variant_index: int = Field(ge=0)
    feedback_tags: list[str] = Field(default_factory=list)
    note: str = Field(default="", max_length=500)
    accepted: bool = False


class PreviewFeedbackRecord(StrictModel):
    """Persisted user feedback for one preview image variant."""

    feedback_id: str
    created_at: str
    run_id: str
    image_index: int = Field(ge=0)
    variant_index: int = Field(ge=0)
    feedback_tags: list[str] = Field(default_factory=list)
    note: str = ""
    accepted: bool = False
    review_target: str
    recommended_next_tool: Literal["adjust_pipeline", "record_tuning_decision"]


class PreviewFeedbackList(StrictModel):
    """List response for concrete preview feedback records."""

    feedback: list[PreviewFeedbackRecord] = Field(default_factory=list)
    total_count: int
    accepted_count: int
    run_id: str | None = None
    accepted_only: bool = False
    aggregated_feedback_tags: list[str] = Field(default_factory=list)


class RankedPreviewCandidate(StrictModel):
    """One candidate in a ranked preview tuning comparison."""

    rank: int
    candidate_run_id: str
    quality_score: float = Field(ge=0.0, le=100.0)
    quality_risk: RiskLevel
    export_ready: bool
    recommended_next_tool: Literal[
        "list_feedback_tags",
        "adjust_pipeline",
        "render_preview_batch",
        "export_pipeline",
    ]
    feedback_tags: list[str] = Field(default_factory=list)
    top_findings: list[QualityFinding] = Field(default_factory=list)
    summary: TuningSessionSummary


class PreviewCandidateRanking(StrictModel):
    """Ranked candidate list for one baseline preview run."""

    baseline_run_id: str
    quality_profile: QualityProfileName = "balanced"
    candidate_count: int
    best_candidate_run_id: str | None = None
    ranked_candidates: list[RankedPreviewCandidate] = Field(default_factory=list)
    decision_guidance: list[str] = Field(default_factory=list)


class DatasetMetricStats(StrictModel):
    """Cross-candidate dataset-level stats for one quality metric."""

    metric: str
    candidate_count: int
    min_value: float
    max_value: float
    mean_value: float


class DatasetFindingCount(StrictModel):
    """Cross-candidate count for one quality finding type."""

    code: str
    severity: RiskLevel
    count: int


class DatasetPreviewScore(StrictModel):
    """Dataset-level score for several preview candidates against one baseline."""

    baseline_run_id: str
    quality_profile: QualityProfileName = "balanced"
    candidate_count: int
    best_candidate_run_id: str | None = None
    ranking: PreviewCandidateRanking
    metric_stats: list[DatasetMetricStats] = Field(default_factory=list)
    finding_counts: list[DatasetFindingCount] = Field(default_factory=list)
    decision_guidance: list[str] = Field(default_factory=list)


class TransformSearchResult(StrictModel):
    """Search result for transform discovery."""

    name: str
    transform_type: str
    targets: list[str]
    score: float
    summary: str | None = None
    supported_bbox_types: list[str] | None = None


class FeedbackTagInfo(StrictModel):
    """Structured feedback tag accepted by pipeline adjustment tools."""

    name: str
    description: str
    applies_to: list[str]
    mitigation: str


class TransformExplanation(StrictModel):
    """Human and machine-readable explanation of one transform's likely effect."""

    name: str
    category: str
    probability: float
    impact: str
    transform_type: str | None = None
    targets: list[str] = Field(default_factory=list)
    metadata_summary: str | None = None
    notable_params: dict[str, Any] = Field(default_factory=dict)


class PipelineExplanation(StrictModel):
    """Pipeline explanation for preview-driven augmentation tuning."""

    risk_level: RiskLevel
    summary: str
    transforms: list[TransformExplanation]
    warnings: list[ValidationIssue] = Field(default_factory=list)
    suggested_feedback_tags: list[str] = Field(default_factory=list)
