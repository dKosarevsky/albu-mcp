"""Read-only dataset onboarding for first preview planning."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from albumentationsx_mcp.dataset_annotations import SampleAnnotationSet, build_sample_annotations
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
    annotation_summary: dict[str, Any] | None = None


class DatasetOnboardingReport(StrictModel):
    """Agent-legible first-preview plan for a local image or image directory."""

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
    review_brief: list[str] = Field(default_factory=list)
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
    """Build a safe first-preview plan for a local image source without rendering."""
    resolved = dataset_path.expanduser().resolve()
    recipe = recipe_builder(task=task, intensity=intensity, targets=targets)
    validation = pipeline_service.validate_pipeline(recipe.pipeline, TargetSpec(targets=recipe.targets))
    checks = _dataset_path_checks(resolved, path_policy)
    image_paths: list[Path] = []
    ignored_file_count = 0
    dataset_structure: DatasetStructureProfile | None = None
    if all(check.status == "ok" for check in checks):
        image_paths, ignored_file_count = _scan_images(resolved)
        dataset_structure = build_dataset_structure_profile(_dataset_context_root(resolved), image_paths)
        checks.append(_image_inventory_check(image_paths, ignored_file_count))
    checks.append(_validation_check(validation))

    sample_image_paths = image_paths[: _bounded_max_images(max_images)]
    sample_paths = [str(path) for path in sample_image_paths]
    status = _aggregate_status(checks)
    preview_ready = status == "ok" and bool(sample_paths) and validation.valid
    template = (
        _preview_request_template(
            dataset_path=_dataset_context_root(resolved),
            sample_paths=sample_image_paths,
            recipe=recipe,
        )
        if preview_ready
        else None
    )
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
        review_brief=_review_brief(
            preview_ready=preview_ready,
            image_counts=(len(image_paths), len(sample_paths)),
            recipe=recipe,
            dataset_structure=dataset_structure,
            template=template,
        ),
        next_actions=_next_actions(preview_ready=preview_ready, checks=checks),
        remediation_actions=_remediation_actions(checks),
        dataset_structure=dataset_structure,
        preview_request_template=template,
    )


def _dataset_path_checks(path: Path, path_policy: PathPolicy) -> list[DatasetOnboardingCheck]:
    details = {
        "path": str(path),
        "allowed_roots": [str(root) for root in path_policy.allowed_roots],
        "path_kind": _path_kind(path),
    }
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
    if path.is_file() and path.suffix.lower() not in _IMAGE_EXTENSIONS:
        return [
            DatasetOnboardingCheck(
                code="dataset_path_unsupported_file",
                status="error",
                severity="high",
                summary=f"Image source is not a supported image file: {path}",
                details={**details, "supported_extensions": sorted(_IMAGE_EXTENSIONS)},
            )
        ]
    if not path.is_dir() and not path.is_file():
        return [
            DatasetOnboardingCheck(
                code="dataset_path_unsupported_type",
                status="error",
                severity="high",
                summary=f"Image source is neither a regular file nor a directory: {path}",
                details=details,
            )
        ]
    return [
        DatasetOnboardingCheck(
            code="dataset_path_accessible",
            status="ok",
            summary=f"Image source is accessible: {path}",
            details=details,
        )
    ]


def _scan_images(dataset_path: Path) -> tuple[list[Path], int]:
    if dataset_path.is_file():
        return [dataset_path.resolve()], 0
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


def _preview_request_template(
    *,
    dataset_path: Path,
    sample_paths: list[Path],
    recipe: RecipeRecommendation,
) -> DatasetPreviewRequestTemplate:
    annotation_set = _annotation_set_for_template(dataset_path, sample_paths, recipe)
    request = {
        "input_paths": [str(path) for path in sample_paths],
        "pipeline": recipe.pipeline.model_dump(mode="json", exclude_none=True),
        "variants_per_image": 1,
        "seed": 0,
        "max_side": 512,
    }
    instructions = [
        "Call `validate_preview_request` with this request before rendering.",
        "Call `render_preview_batch` only after validation returns `valid=true`.",
        "Inspect the contact sheet before increasing variants_per_image, max_side, or intensity.",
        "Record concrete feedback tags before adjusting the pipeline.",
    ]
    if annotation_set is not None:
        annotation_summary = _annotation_summary(annotation_set)
        request["annotations"] = _annotation_payload(
            annotation_set,
            include_bboxes=_include_bboxes(recipe),
            include_masks=_include_masks(recipe),
        )
        instructions.extend(
            [
                f"Annotation-aware template uses {annotation_set.source_format} annotations for overlay previews.",
                "Inspect `overlay_contact_sheet` before accepting geometric transforms.",
            ]
        )
        if _include_masks(recipe):
            instructions.append("Mask-aware template preserves segmentation masks for coverage-aware overlay previews.")
            instructions.append(_mask_summary_instruction(annotation_summary))
        instructions.extend(annotation_set.warnings)
    else:
        annotation_summary = None
    return DatasetPreviewRequestTemplate(
        request=request,
        instructions=instructions,
        annotation_summary=annotation_summary,
    )


def _annotation_set_for_template(
    dataset_path: Path,
    sample_paths: list[Path],
    recipe: RecipeRecommendation,
) -> SampleAnnotationSet | None:
    if not _include_bboxes(recipe) and not _include_masks(recipe):
        return None
    return build_sample_annotations(dataset_path, sample_paths)


def _annotation_payload(
    annotation_set: SampleAnnotationSet,
    *,
    include_bboxes: bool,
    include_masks: bool,
) -> list[dict[str, Any] | None]:
    payload: list[dict[str, Any] | None] = []
    for annotation in annotation_set.annotations:
        if annotation is None:
            payload.append(None)
            continue
        item: dict[str, Any] = {}
        if include_bboxes and annotation.bboxes:
            item["bboxes"] = annotation.bboxes
        if include_bboxes and annotation.bbox_labels:
            item["bbox_labels"] = annotation.bbox_labels
        if annotation.keypoints:
            item["keypoints"] = annotation.keypoints
        if include_masks and annotation.mask_path is not None:
            item["mask_path"] = str(annotation.mask_path)
        if include_masks and annotation.mask_polygons:
            item["mask_polygons"] = annotation.mask_polygons
        if include_masks and annotation.mask_rles:
            item["mask_rles"] = [mask_rle.model_dump(mode="json") for mask_rle in annotation.mask_rles]
        payload.append(item or None)
    return payload


def _annotation_summary(annotation_set: SampleAnnotationSet) -> dict[str, Any]:
    annotations = [annotation for annotation in annotation_set.annotations if annotation is not None]
    mask_path_count = sum(annotation.mask_path is not None for annotation in annotations)
    mask_polygon_count = sum(len(annotation.mask_polygons) for annotation in annotations)
    compressed_rle_count = sum(
        1 for annotation in annotations for mask_rle in annotation.mask_rles if isinstance(mask_rle.counts, str)
    )
    uncompressed_rle_count = sum(
        1 for annotation in annotations for mask_rle in annotation.mask_rles if not isinstance(mask_rle.counts, str)
    )
    mask_formats = _mask_formats(
        mask_path_count=mask_path_count,
        mask_polygon_count=mask_polygon_count,
        compressed_rle_count=compressed_rle_count,
        uncompressed_rle_count=uncompressed_rle_count,
    )
    return {
        "source_format": annotation_set.source_format,
        "sample_count": len(annotation_set.annotations),
        "matched_count": annotation_set.matched_count,
        "missing_count": len(annotation_set.annotations) - annotation_set.matched_count,
        "bbox_count": sum(len(annotation.bboxes) for annotation in annotations),
        "keypoint_count": sum(len(annotation.keypoints) for annotation in annotations),
        "mask_path_count": mask_path_count,
        "mask_polygon_count": mask_polygon_count,
        "mask_rle_count": compressed_rle_count + uncompressed_rle_count,
        "compressed_rle_count": compressed_rle_count,
        "uncompressed_rle_count": uncompressed_rle_count,
        "mask_formats": mask_formats,
        "warnings": list(annotation_set.warnings),
    }


def _mask_formats(
    *,
    mask_path_count: int,
    mask_polygon_count: int,
    compressed_rle_count: int,
    uncompressed_rle_count: int,
) -> list[str]:
    formats: list[str] = []
    if mask_path_count:
        formats.append("mask_path")
    if mask_polygon_count:
        formats.append("polygons")
    if uncompressed_rle_count:
        formats.append("uncompressed_rle")
    if compressed_rle_count:
        formats.append("compressed_rle")
    return formats


def _mask_summary_instruction(annotation_summary: dict[str, Any]) -> str:
    return (
        "Segmentation annotation summary: "
        f"matched={annotation_summary['matched_count']}/{annotation_summary['sample_count']}, "
        f"mask_polygons={annotation_summary['mask_polygon_count']}, "
        f"mask_rles={annotation_summary['mask_rle_count']}, "
        f"formats={','.join(annotation_summary['mask_formats']) or 'none'}."
    )


def _include_bboxes(recipe: RecipeRecommendation) -> bool:
    return "bboxes" in recipe.targets or recipe.pipeline.bbox_params is not None


def _include_masks(recipe: RecipeRecommendation) -> bool:
    return "mask" in recipe.targets or "masks" in recipe.targets


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


def _review_brief(
    *,
    preview_ready: bool,
    image_counts: tuple[int, int],
    recipe: RecipeRecommendation,
    dataset_structure: DatasetStructureProfile | None,
    template: DatasetPreviewRequestTemplate | None,
) -> list[str]:
    """Build a concise host-facing summary for first-preview review."""
    image_count, sampled_image_count = image_counts
    status = "Preview-ready dataset" if preview_ready else "Dataset is not preview-ready"
    image_word = "image" if image_count == 1 else "images"
    sampled_word = "image" if sampled_image_count == 1 else "images"
    brief = [f"{status}: {sampled_image_count} sampled {sampled_word} out of {image_count} supported {image_word}."]
    if dataset_structure is not None:
        if dataset_structure.detected_layouts:
            brief.append(f"Detected layouts: {', '.join(sorted(dataset_structure.detected_layouts))}.")
        annotation_formats = sorted({item.format for item in dataset_structure.annotation_formats})
        if annotation_formats:
            brief.append(f"Annotation formats: {', '.join(annotation_formats)}.")
        brief.extend(dataset_structure.balance_warnings)
    if "bboxes" in recipe.targets:
        brief.append("Bounding boxes require bbox_params-compatible transforms and overlay review before export.")
    if "mask" in recipe.targets or "masks" in recipe.targets:
        brief.append("Masks require mask-aware review and coverage checks before accepting geometric transforms.")
    if template is not None and template.annotation_summary:
        summary = template.annotation_summary
        brief.append(
            "Annotation coverage: "
            f"{summary['matched_count']}/{summary['sample_count']} samples matched, "
            f"bbox_count={summary['bbox_count']}, "
            f"mask_formats={','.join(summary['mask_formats']) or 'none'}."
        )
    if preview_ready:
        brief.append("Validate preview_request_template.request before rendering.")
    else:
        brief.append("Resolve remediation_actions before rendering local previews.")
    return brief


def _remediation_actions(checks: list[DatasetOnboardingCheck]) -> list[DatasetOnboardingRemediationAction]:
    codes = {check.code for check in checks if check.status != "ok"}
    actions: list[DatasetOnboardingRemediationAction] = []
    if "dataset_path_outside_allowed_root" in codes:
        actions.append(
            DatasetOnboardingRemediationAction(
                code="move_dataset_under_allowed_root",
                severity="high",
                check_codes=["dataset_path_outside_allowed_root"],
                summary="Move the image source under an allowed root or restart the server with a correct root.",
                command_hint="--allowed-root /absolute/path/to/images",
                docs_uri="albumentationsx://diagnostics/guide",
            )
        )
    invalid_source = [
        code
        for code in ("dataset_path_missing", "dataset_path_unsupported_file", "dataset_path_unsupported_type")
        if code in codes
    ]
    if invalid_source:
        actions.append(
            DatasetOnboardingRemediationAction(
                code="fix_dataset_path",
                severity="high",
                check_codes=invalid_source,
                summary="Use an existing supported image or a directory containing supported images as dataset_path.",
            )
        )
    if "dataset_images_missing" in codes:
        actions.append(
            DatasetOnboardingRemediationAction(
                code="add_dataset_images",
                severity="medium",
                check_codes=["dataset_images_missing"],
                summary="Add supported image files or point dataset_path at a supported image.",
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


def _dataset_context_root(path: Path) -> Path:
    return path if path.is_dir() else path.parent


def _path_kind(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "other"


def _bounded_max_images(max_images: int) -> int:
    return max(1, min(max_images, 32))
