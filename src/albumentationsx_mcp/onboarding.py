"""Read-only dataset onboarding for first preview planning."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from albumentationsx_mcp.dataset_profile import DatasetStructureProfile, build_dataset_structure_profile
from albumentationsx_mcp.diagnostics import DiagnosticSeverity, DiagnosticStatus
from albumentationsx_mcp.models import PipelineValidationReport, RecipeRecommendation, StrictModel, TargetSpec
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.presets import Intensity
from albumentationsx_mcp.preview import PathPolicy

_IMAGE_EXTENSIONS = frozenset({".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"})
_DEFAULT_MAX_IMAGES = 8


class DatasetOnboardingCheck(StrictModel):
    """One machine-readable dataset onboarding check."""

    code: str
    status: DiagnosticStatus
    severity: DiagnosticSeverity = "info"
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class DatasetOnboardingRemediationAction(StrictModel):
    """One structured remediation action for dataset onboarding."""

    code: str
    severity: DiagnosticSeverity
    check_codes: list[str] = Field(default_factory=list)
    summary: str
    command_hint: str | None = None
    docs_uri: str | None = None


class DatasetPreviewRequestTemplate(StrictModel):
    """Safe render_preview_batch request template for the sampled dataset."""

    tool: Literal["render_preview_batch"] = "render_preview_batch"
    request: dict[str, Any]
    instructions: list[str] = Field(default_factory=list)


class DatasetOnboardingReport(StrictModel):
    """Agent-legible first-preview plan for a local image dataset folder."""

    status: DiagnosticStatus
    preview_ready: bool
    dataset_path: str
    allowed_roots: list[str]
    image_count: int = 0
    sampled_image_count: int = 0
    ignored_file_count: int = 0
    sample_paths: list[str] = Field(default_factory=list)
    checks: list[DatasetOnboardingCheck]
    recipe: RecipeRecommendation
    validation: PipelineValidationReport
    next_actions: list[str]
    remediation_actions: list[DatasetOnboardingRemediationAction]
    dataset_structure: DatasetStructureProfile | None = None
    preview_request_template: DatasetPreviewRequestTemplate | None = None


RecipeBuilder = Callable[..., RecipeRecommendation]


def build_dataset_onboarding_report(  # noqa: PLR0913
    *,
    dataset_path: Path,
    task: str,
    intensity: Intensity,
    targets: list[str] | None,
    path_policy: PathPolicy,
    pipeline_service: PipelineService,
    recipe_builder: RecipeBuilder,
    max_images: int = _DEFAULT_MAX_IMAGES,
) -> DatasetOnboardingReport:
    """Build a safe first-preview plan for a local dataset folder without rendering."""
    resolved = dataset_path.expanduser().resolve()
    recipe = recipe_builder(task=task, intensity=intensity, targets=targets)
    validation = pipeline_service.validate_pipeline(recipe.pipeline, TargetSpec(targets=recipe.targets))
    checks = _dataset_path_checks(resolved, path_policy)
    image_paths: list[Path] = []
    ignored_file_count = 0
    dataset_structure: DatasetStructureProfile | None = None
    if all(check.status == "ok" for check in checks):
        image_paths, ignored_file_count = _scan_images(resolved)
        dataset_structure = build_dataset_structure_profile(resolved, image_paths)
        checks.append(_image_inventory_check(image_paths, ignored_file_count))
    checks.append(_validation_check(validation))

    sample_paths = [str(path) for path in image_paths[: _bounded_max_images(max_images)]]
    status = _aggregate_status(checks)
    preview_ready = status == "ok" and bool(sample_paths) and validation.valid
    template = _preview_request_template(sample_paths, recipe) if preview_ready else None
    return DatasetOnboardingReport(
        status=status,
        preview_ready=preview_ready,
        dataset_path=str(resolved),
        allowed_roots=[str(root) for root in path_policy.allowed_roots],
        image_count=len(image_paths),
        sampled_image_count=len(sample_paths),
        ignored_file_count=ignored_file_count,
        sample_paths=sample_paths,
        checks=checks,
        recipe=recipe,
        validation=validation,
        next_actions=_next_actions(preview_ready=preview_ready, checks=checks),
        remediation_actions=_remediation_actions(checks),
        dataset_structure=dataset_structure,
        preview_request_template=template,
    )


def _dataset_path_checks(path: Path, path_policy: PathPolicy) -> list[DatasetOnboardingCheck]:
    details = {"path": str(path), "allowed_roots": [str(root) for root in path_policy.allowed_roots]}
    if not _is_allowed(path, path_policy):
        return [
            DatasetOnboardingCheck(
                code="dataset_path_outside_allowed_root",
                status="error",
                severity="high",
                summary=f"Dataset path is outside allowed roots: {path}",
                details=details,
            )
        ]
    if not path.exists():
        return [
            DatasetOnboardingCheck(
                code="dataset_path_missing",
                status="error",
                severity="high",
                summary=f"Dataset path does not exist: {path}",
                details=details,
            )
        ]
    if not path.is_dir():
        return [
            DatasetOnboardingCheck(
                code="dataset_path_not_directory",
                status="error",
                severity="high",
                summary=f"Dataset path is not a directory: {path}",
                details=details,
            )
        ]
    return [
        DatasetOnboardingCheck(
            code="dataset_path_accessible",
            status="ok",
            summary=f"Dataset path is accessible: {path}",
            details=details,
        )
    ]


def _scan_images(dataset_path: Path) -> tuple[list[Path], int]:
    files = sorted(path.resolve() for path in dataset_path.rglob("*") if path.is_file())
    image_paths = [path for path in files if path.suffix.lower() in _IMAGE_EXTENSIONS]
    return image_paths, len(files) - len(image_paths)


def _image_inventory_check(image_paths: list[Path], ignored_file_count: int) -> DatasetOnboardingCheck:
    if not image_paths:
        return DatasetOnboardingCheck(
            code="dataset_images_missing",
            status="warning",
            severity="medium",
            summary="Dataset folder contains no supported image files.",
            details={
                "supported_extensions": sorted(_IMAGE_EXTENSIONS),
                "ignored_file_count": ignored_file_count,
            },
        )
    return DatasetOnboardingCheck(
        code="dataset_images_found",
        status="ok",
        summary=f"Found {len(image_paths)} supported image file(s).",
        details={
            "image_count": len(image_paths),
            "ignored_file_count": ignored_file_count,
            "supported_extensions": sorted(_IMAGE_EXTENSIONS),
        },
    )


def _validation_check(validation: PipelineValidationReport) -> DatasetOnboardingCheck:
    if validation.valid:
        return DatasetOnboardingCheck(
            code="recommended_pipeline_valid",
            status="ok",
            summary="Recommended pipeline validates for the selected targets.",
            details={"warning_count": len(validation.warnings)},
        )
    return DatasetOnboardingCheck(
        code="recommended_pipeline_invalid",
        status="error",
        severity="high",
        summary="Recommended pipeline failed validation for the selected targets.",
        details={
            "errors": [error.model_dump(mode="json") for error in validation.errors],
            "warnings": [warning.model_dump(mode="json") for warning in validation.warnings],
        },
    )


def _preview_request_template(sample_paths: list[str], recipe: RecipeRecommendation) -> DatasetPreviewRequestTemplate:
    return DatasetPreviewRequestTemplate(
        request={
            "input_paths": sample_paths,
            "pipeline": recipe.pipeline.model_dump(mode="json", exclude_none=True),
            "variants_per_image": 1,
            "seed": 0,
            "max_side": 512,
        },
        instructions=[
            "Call `validate_preview_request` with this request before rendering.",
            "Call `render_preview_batch` only after validation returns `valid=true`.",
            "Inspect the contact sheet before increasing variants_per_image, max_side, or intensity.",
            "Record concrete feedback tags before adjusting the pipeline.",
        ],
    )


def _next_actions(*, preview_ready: bool, checks: list[DatasetOnboardingCheck]) -> list[str]:
    if preview_ready:
        return [
            "Call `validate_preview_request` with `preview_request_template.request`.",
            "Call `render_preview_batch` with the validated request.",
            "Inspect the contact sheet and collect concrete feedback tags.",
            "Use `adjust_pipeline` or `start_tuning_session` after feedback.",
        ]
    actions = [check.summary for check in checks if check.status != "ok"]
    if not actions:
        actions.append("Resolve dataset onboarding warnings before rendering previews.")
    return actions


def _remediation_actions(checks: list[DatasetOnboardingCheck]) -> list[DatasetOnboardingRemediationAction]:
    codes = {check.code for check in checks if check.status != "ok"}
    actions: list[DatasetOnboardingRemediationAction] = []
    if "dataset_path_outside_allowed_root" in codes:
        actions.append(
            DatasetOnboardingRemediationAction(
                code="move_dataset_under_allowed_root",
                severity="high",
                check_codes=["dataset_path_outside_allowed_root"],
                summary="Move the dataset folder under an allowed root or restart the server with a correct root.",
                command_hint="--allowed-root /absolute/path/to/images",
                docs_uri="albumentationsx://diagnostics/guide",
            )
        )
    missing_or_not_dir = [code for code in ("dataset_path_missing", "dataset_path_not_directory") if code in codes]
    if missing_or_not_dir:
        actions.append(
            DatasetOnboardingRemediationAction(
                code="fix_dataset_path",
                severity="high",
                check_codes=missing_or_not_dir,
                summary="Use an existing local image directory as dataset_path.",
            )
        )
    if "dataset_images_missing" in codes:
        actions.append(
            DatasetOnboardingRemediationAction(
                code="add_dataset_images",
                severity="medium",
                check_codes=["dataset_images_missing"],
                summary="Add supported image files or point dataset_path at a folder containing images.",
            )
        )
    if "recommended_pipeline_invalid" in codes:
        actions.append(
            DatasetOnboardingRemediationAction(
                code="fix_recommended_pipeline",
                severity="high",
                check_codes=["recommended_pipeline_invalid"],
                summary="Use `recommend_recipe` with compatible targets or call `validate_pipeline` for details.",
            )
        )
    return actions


def _aggregate_status(checks: list[DatasetOnboardingCheck]) -> DiagnosticStatus:
    statuses = {check.status for check in checks}
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "ok"


def _is_allowed(path: Path, path_policy: PathPolicy) -> bool:
    return any(path == root or root in path.parents for root in path_policy.allowed_roots)


def _bounded_max_images(max_images: int) -> int:
    return max(1, min(max_images, 32))
