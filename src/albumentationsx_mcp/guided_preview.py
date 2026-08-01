"""Application service for a safe guided first preview."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import Field, ValidationError

from albumentationsx_mcp.models import ArtifactRef, PreviewRequest, PreviewResult, StrictModel, TargetSpec
from albumentationsx_mcp.onboarding import DatasetOnboardingReport, RecipeBuilder, build_dataset_onboarding_report
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.presets import Intensity
from albumentationsx_mcp.preview import PathPolicy
from albumentationsx_mcp.preview_trace import PreviewVariantTraceResult
from albumentationsx_mcp.preview_validation import PreviewRequestValidationReport

_MALFORMED_NORMALIZED_REQUEST = "Validated preview request is malformed"
_INVALID_CONTACT_SHEET_COUNT = "Rendered preview must contain exactly one contact_sheet artifact"
_UNAVAILABLE_FIRST_TRACE = "Rendered preview first variant trace is unavailable or inconsistent"
_SUCCESS_NEXT_ACTIONS = (
    "Inspect the rendered contact sheet.",
    "Call `trace_preview_variant` for image_index=0 and variant_index=0.",
    "Use `adjust_pipeline` only after reviewing the contact sheet and first-variant trace evidence.",
)


class _PreviewValidator(Protocol):
    def validate(
        self,
        request: dict[str, Any],
        *,
        target: TargetSpec | None = None,
    ) -> PreviewRequestValidationReport: ...


class _PreviewRenderer(Protocol):
    def render_preview(self, request: PreviewRequest) -> PreviewResult: ...


class OnboardingBuilder(Protocol):
    """Build one read-only dataset onboarding report."""

    def __call__(  # noqa: PLR0913
        self,
        *,
        dataset_path: Path,
        task: str,
        intensity: Intensity,
        targets: list[str] | None,
        path_policy: PathPolicy,
        pipeline_service: PipelineService,
        recipe_builder: RecipeBuilder,
        max_images: int = 8,
    ) -> DatasetOnboardingReport: ...


class TraceLookup(Protocol):
    """Look up one trace from a rendered preview run."""

    def __call__(
        self,
        run_id: str,
        *,
        image_index: int,
        variant_index: int,
    ) -> PreviewVariantTraceResult: ...


class GuidedPreviewRequest(StrictModel):
    """Inputs for one bounded guided first-preview attempt."""

    dataset_path: Path
    task: str = "classification"
    intensity: Intensity = "low"
    targets: list[str] | None = None
    max_images: int = Field(default=8, ge=1, le=8)


class GuidedPreviewResult(StrictModel):
    """Rendered preview or a structured report explaining why it was blocked."""

    status: Literal["rendered", "blocked"]
    onboarding: DatasetOnboardingReport
    validation: PreviewRequestValidationReport | None = None
    normalized_request: dict[str, Any] | None = None
    preview: PreviewResult | None = None
    contact_sheet: ArtifactRef | None = None
    trace_available: bool = False
    next_actions: list[str] = Field(default_factory=list)


class GuidedPreviewService:
    """Coordinate onboarding, validation, and one bounded preview render."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        path_policy: PathPolicy,
        pipeline_service: PipelineService,
        recipe_builder: RecipeBuilder,
        preview_validator: _PreviewValidator,
        preview_service: _PreviewRenderer,
        trace_lookup: TraceLookup,
        onboarding_builder: OnboardingBuilder = build_dataset_onboarding_report,
    ) -> None:
        self.path_policy = path_policy
        self.pipeline_service = pipeline_service
        self.recipe_builder = recipe_builder
        self.preview_validator = preview_validator
        self.preview_service = preview_service
        self.trace_lookup = trace_lookup
        self.onboarding_builder = onboarding_builder

    def run(self, request: GuidedPreviewRequest) -> GuidedPreviewResult:
        """Render the onboarding template only after every read-only gate passes."""
        onboarding = self.onboarding_builder(
            dataset_path=request.dataset_path,
            task=request.task,
            intensity=request.intensity,
            targets=request.targets,
            max_images=request.max_images,
            path_policy=self.path_policy,
            pipeline_service=self.pipeline_service,
            recipe_builder=self.recipe_builder,
        )
        template = onboarding.preview_request_template
        if not onboarding.preview_ready or template is None:
            return GuidedPreviewResult(
                status="blocked",
                onboarding=onboarding,
                next_actions=onboarding.next_actions,
            )

        validation = self.preview_validator.validate(
            template.request,
            target=TargetSpec(targets=onboarding.recipe.targets),
        )
        normalized_request = validation.normalized_request
        if not validation.valid or normalized_request is None:
            return GuidedPreviewResult(
                status="blocked",
                onboarding=onboarding,
                validation=validation,
                next_actions=validation.next_actions,
            )

        try:
            preview_request = PreviewRequest.model_validate(normalized_request)
        except ValidationError:
            raise ValueError(_MALFORMED_NORMALIZED_REQUEST) from None

        preview = self.preview_service.render_preview(preview_request)
        contact_sheets = [artifact for artifact in preview.artifacts if artifact.kind == "contact_sheet"]
        if len(contact_sheets) != 1:
            raise RuntimeError(_INVALID_CONTACT_SHEET_COUNT)

        trace_result = self.trace_lookup(preview.run_id, image_index=0, variant_index=0)
        trace_available = _is_first_variant_trace_available(trace_result, run_id=preview.run_id)
        if not trace_available:
            raise RuntimeError(_UNAVAILABLE_FIRST_TRACE)

        return GuidedPreviewResult(
            status="rendered",
            onboarding=onboarding,
            validation=validation,
            normalized_request=normalized_request,
            preview=preview,
            contact_sheet=contact_sheets[0],
            trace_available=trace_available,
            next_actions=list(_SUCCESS_NEXT_ACTIONS),
        )


def _is_first_variant_trace_available(result: PreviewVariantTraceResult, *, run_id: str) -> bool:
    trace = result.trace
    return (
        result.available
        and trace is not None
        and result.run_id == run_id
        and result.image_index == 0
        and result.variant_index == 0
        and trace.image_index == 0
        and trace.variant_index == 0
    )
