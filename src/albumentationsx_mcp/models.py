"""Typed contracts used by the AlbumentationsX MCP server."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ArtifactKind = Literal["image", "manifest", "contact_sheet", "overlay", "overlay_contact_sheet"]
RiskLevel = Literal["low", "medium", "high"]


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


class ImageAnnotations(StrictModel):
    """Optional annotations supplied for one preview input image."""

    bboxes: list[list[float]] = Field(default_factory=list)
    bbox_labels: list[str | int] = Field(default_factory=list)
    keypoints: list[list[float]] = Field(default_factory=list)
    mask_path: Path | None = None


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


class PreviewRunComparison(StrictModel):
    """Comparison of two preview run manifests for feedback-driven tuning."""

    baseline: PreviewManifestSummary
    candidate: PreviewManifestSummary
    pipeline_changed: bool
    inputs_changed: bool
    seed_changed: bool
    artifact_count_delta: int
    review_notes: list[str] = Field(default_factory=list)


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
