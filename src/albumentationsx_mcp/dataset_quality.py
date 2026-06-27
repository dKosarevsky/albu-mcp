"""Read-only dataset quality inspection before preview rendering."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image
from pydantic import Field

from albumentationsx_mcp.dataset_intelligence import DatasetAnnotationSummary, inspect_annotation_consistency
from albumentationsx_mcp.diagnostics import DiagnosticSeverity, DiagnosticStatus
from albumentationsx_mcp.models import ImageQualityAggregate, ImageQualityMetrics, StrictModel
from albumentationsx_mcp.preview import PathPolicy
from albumentationsx_mcp.quality import collect_image_quality_metrics

_IMAGE_EXTENSIONS = frozenset({".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"})
_DEFAULT_MAX_IMAGES = 8
_MAX_IMAGES_LIMIT = 32
_HIGH_CLIPPING_THRESHOLD = 0.2
_LOW_CONTRAST_THRESHOLD = 5.0
_LOW_ENTROPY_THRESHOLD = 2.0
_LOW_BRIGHTNESS_THRESHOLD = 25.0
_HIGH_BRIGHTNESS_THRESHOLD = 230.0
_KNOWN_SPLITS = {
    "train": "train",
    "training": "train",
    "val": "val",
    "valid": "val",
    "validation": "val",
    "test": "test",
}
_MAX_METADATA_IMAGES = 512
_MAX_DUPLICATE_GROUPS = 8
_CLASS_IMBALANCE_RATIO = 0.5
_SPLIT_IMBALANCE_RATIO = 0.2
_ASPECT_RATIO_SPREAD = 3.0
_MIN_CLASS_PATH_PARTS = 2
_SPLIT_WITH_CLASS_PATH_PARTS = 3
_MIN_IMBALANCE_BUCKETS = 2


class DatasetQualityFinding(StrictModel):
    """One machine-readable dataset quality finding."""

    code: str
    severity: DiagnosticSeverity
    summary: str
    sample_paths: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class DatasetImageSizeSummary(StrictModel):
    """Lightweight image size and aspect-ratio summary for dataset health checks."""

    image_count: int
    min_width: int
    max_width: int
    min_height: int
    max_height: int
    aspect_ratio_min: float
    aspect_ratio_max: float


class DatasetDuplicateGroup(StrictModel):
    """One exact duplicate image group detected by content hash."""

    sha256: str
    image_count: int
    sample_paths: list[str] = Field(default_factory=list)


class DatasetStructureHealth(StrictModel):
    """Structural dataset health signals that do not require rendering previews."""

    split_distribution: dict[str, int] = Field(default_factory=dict)
    class_distribution: dict[str, int] = Field(default_factory=dict)
    image_size_summary: DatasetImageSizeSummary | None = None
    duplicate_groups: list[DatasetDuplicateGroup] = Field(default_factory=list)
    annotation_summary: DatasetAnnotationSummary | None = None


class DatasetQualityReport(StrictModel):
    """Read-only quality report for a sampled local dataset folder."""

    status: DiagnosticStatus
    dataset_path: str
    allowed_roots: list[str]
    image_count: int = 0
    sampled_image_count: int = 0
    ignored_file_count: int = 0
    unreadable_image_count: int = 0
    duplicate_image_count: int = 0
    sample_paths: list[str] = Field(default_factory=list)
    unreadable_paths: list[str] = Field(default_factory=list)
    split_distribution: dict[str, int] = Field(default_factory=dict)
    class_distribution: dict[str, int] = Field(default_factory=dict)
    image_size_summary: DatasetImageSizeSummary | None = None
    duplicate_groups: list[DatasetDuplicateGroup] = Field(default_factory=list)
    annotation_summary: DatasetAnnotationSummary | None = None
    aggregate: ImageQualityAggregate
    sample_metrics: list[ImageQualityMetrics] = Field(default_factory=list)
    findings: list[DatasetQualityFinding] = Field(default_factory=list)
    preview_ready: bool = True
    preview_guard: str = "ready"
    preview_blockers: list[DatasetQualityFinding] = Field(default_factory=list)
    preview_guard_actions: list[str] = Field(default_factory=list)
    recommended_next_tools: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    remediation_actions: list[dict[str, Any]] = Field(default_factory=list)


def inspect_dataset_quality(
    *,
    dataset_path: Path,
    path_policy: PathPolicy,
    max_images: int = _DEFAULT_MAX_IMAGES,
) -> DatasetQualityReport:
    """Inspect a bounded sample of local dataset images without rendering previews."""
    resolved = dataset_path.expanduser().resolve()
    path_error = _path_error(resolved, path_policy)
    if path_error is not None:
        return DatasetQualityReport(
            status="error",
            dataset_path=str(resolved),
            allowed_roots=[str(root) for root in path_policy.allowed_roots],
            aggregate=ImageQualityAggregate(image_count=0),
            findings=[path_error],
            preview_ready=False,
            preview_guard="blocked_by_path_policy",
            preview_blockers=[path_error],
            preview_guard_actions=["Fix the dataset path before rendering previews."],
            recommended_next_tools=["fix_dataset_path"],
            next_actions=["Move the dataset under an allowed root or restart the MCP server with --allowed-root."],
            remediation_actions=[
                {
                    "code": "move_dataset_under_allowed_root",
                    "severity": "high",
                    "summary": "Move the dataset path under an allowed root before inspecting quality.",
                    "command_hint": "--allowed-root /absolute/path/to/dataset-parent",
                }
            ],
        )

    image_paths, ignored_file_count = _scan_images(resolved)
    sampled_paths = image_paths[: _bounded_max_images(max_images)]
    metrics, unreadable_paths = _collect_sample_metrics(sampled_paths)
    aggregate = _aggregate_metrics(metrics)
    structure = _structure_health(dataset_path=resolved, image_paths=image_paths)
    findings = _findings(
        aggregate=aggregate,
        unreadable_paths=unreadable_paths,
        structure=structure,
    )
    preview_blockers = _preview_blockers(findings)
    status = _status(image_paths=image_paths, metrics=metrics, findings=findings)
    return DatasetQualityReport(
        status=status,
        dataset_path=str(resolved),
        allowed_roots=[str(root) for root in path_policy.allowed_roots],
        image_count=len(image_paths),
        sampled_image_count=len(sampled_paths),
        ignored_file_count=ignored_file_count,
        unreadable_image_count=len(unreadable_paths),
        duplicate_image_count=sum(group.image_count for group in structure.duplicate_groups),
        sample_paths=[str(path) for path in sampled_paths],
        unreadable_paths=[str(path) for path in unreadable_paths],
        split_distribution=structure.split_distribution,
        class_distribution=structure.class_distribution,
        image_size_summary=structure.image_size_summary,
        duplicate_groups=structure.duplicate_groups,
        annotation_summary=structure.annotation_summary,
        aggregate=aggregate,
        sample_metrics=metrics,
        findings=findings,
        preview_ready=not preview_blockers,
        preview_guard=_preview_guard(preview_blockers),
        preview_blockers=preview_blockers,
        preview_guard_actions=_preview_guard_actions(preview_blockers),
        recommended_next_tools=_recommended_next_tools(status=status, findings=findings),
        next_actions=_next_actions(status=status, findings=findings),
        remediation_actions=_remediation_actions(findings),
    )


def _path_error(path: Path, path_policy: PathPolicy) -> DatasetQualityFinding | None:
    if not _is_allowed(path, path_policy):
        return DatasetQualityFinding(
            code="dataset_path_outside_allowed_root",
            severity="high",
            summary=f"Dataset path is outside allowed roots: {path}",
            details={"allowed_roots": [str(root) for root in path_policy.allowed_roots]},
        )
    if not path.exists():
        return DatasetQualityFinding(
            code="dataset_path_missing",
            severity="high",
            summary=f"Dataset path does not exist: {path}",
        )
    if not path.is_dir():
        return DatasetQualityFinding(
            code="dataset_path_not_directory",
            severity="high",
            summary=f"Dataset path is not a directory: {path}",
        )
    return None


def _scan_images(dataset_path: Path) -> tuple[list[Path], int]:
    files = sorted(path.resolve() for path in dataset_path.rglob("*") if path.is_file())
    image_paths = [path for path in files if path.suffix.lower() in _IMAGE_EXTENSIONS]
    return image_paths, len(files) - len(image_paths)


def _collect_sample_metrics(paths: list[Path]) -> tuple[list[ImageQualityMetrics], list[Path]]:
    metrics: list[ImageQualityMetrics] = []
    unreadable_paths: list[Path] = []
    for path in paths:
        metric = _safe_collect_metric(path)
        if metric is None:
            unreadable_paths.append(path)
        else:
            metrics.append(metric)
    return metrics, unreadable_paths


def _safe_collect_metric(path: Path) -> ImageQualityMetrics | None:
    try:
        return collect_image_quality_metrics(path)
    except (OSError, ValueError):
        return None


def _aggregate_metrics(metrics: list[ImageQualityMetrics]) -> ImageQualityAggregate:
    if not metrics:
        return ImageQualityAggregate(image_count=0)
    return ImageQualityAggregate(
        image_count=len(metrics),
        brightness_mean=_mean([metric.brightness_mean for metric in metrics]),
        contrast_std=_mean([metric.contrast_std for metric in metrics]),
        sharpness_score=_mean([metric.sharpness_score for metric in metrics]),
        saturation_mean=_mean([metric.saturation_mean for metric in metrics]),
        colorfulness_score=_mean([metric.colorfulness_score for metric in metrics]),
        entropy_bits=_mean([metric.entropy_bits for metric in metrics]),
        clipping_fraction=_mean([metric.clipping_fraction for metric in metrics]),
    )


def _findings(
    *,
    aggregate: ImageQualityAggregate,
    unreadable_paths: list[Path],
    structure: DatasetStructureHealth,
) -> list[DatasetQualityFinding]:
    findings: list[DatasetQualityFinding] = []
    if unreadable_paths:
        findings.append(
            DatasetQualityFinding(
                code="sample_unreadable_images",
                severity="high",
                summary=f"{len(unreadable_paths)} sampled image file(s) could not be opened.",
                sample_paths=[str(path) for path in unreadable_paths[:3]],
            )
        )
    if structure.duplicate_groups:
        findings.append(
            DatasetQualityFinding(
                code="dataset_exact_duplicate_images",
                severity="medium",
                summary="Dataset sample contains exact duplicate image files.",
                sample_paths=structure.duplicate_groups[0].sample_paths,
                details={
                    "duplicate_group_count": len(structure.duplicate_groups),
                    "duplicate_image_count": sum(group.image_count for group in structure.duplicate_groups),
                },
            )
        )
    if _is_imbalanced(structure.class_distribution, min_ratio=_CLASS_IMBALANCE_RATIO):
        findings.append(
            DatasetQualityFinding(
                code="dataset_class_imbalance",
                severity="medium",
                summary="Detected class distribution is imbalanced.",
                details={"class_distribution": structure.class_distribution},
            )
        )
    if _is_imbalanced(structure.split_distribution, min_ratio=_SPLIT_IMBALANCE_RATIO):
        findings.append(
            DatasetQualityFinding(
                code="dataset_split_imbalance",
                severity="medium",
                summary="Detected split distribution is imbalanced.",
                details={"split_distribution": structure.split_distribution},
            )
        )
    if structure.image_size_summary is not None and _has_large_aspect_ratio_spread(structure.image_size_summary):
        findings.append(
            DatasetQualityFinding(
                code="dataset_aspect_ratio_spread",
                severity="info",
                summary="Sampled image dimensions have a wide aspect-ratio spread.",
                details={
                    "aspect_ratio_min": structure.image_size_summary.aspect_ratio_min,
                    "aspect_ratio_max": structure.image_size_summary.aspect_ratio_max,
                },
            )
        )
    if structure.annotation_summary is not None:
        findings.extend(_annotation_findings(structure.annotation_summary))
    if aggregate.image_count == 0:
        return findings
    if aggregate.clipping_fraction is not None and aggregate.clipping_fraction >= _HIGH_CLIPPING_THRESHOLD:
        findings.append(
            DatasetQualityFinding(
                code="dataset_high_clipping",
                severity="medium",
                summary="Sampled images contain a high fraction of clipped dark or bright pixels.",
                details={"clipping_fraction": aggregate.clipping_fraction},
            )
        )
    if aggregate.contrast_std is not None and aggregate.contrast_std < _LOW_CONTRAST_THRESHOLD:
        findings.append(
            DatasetQualityFinding(
                code="dataset_low_contrast",
                severity="medium",
                summary="Sampled images have very low contrast.",
                details={"contrast_std": aggregate.contrast_std},
            )
        )
    if aggregate.entropy_bits is not None and aggregate.entropy_bits < _LOW_ENTROPY_THRESHOLD:
        findings.append(
            DatasetQualityFinding(
                code="dataset_low_entropy",
                severity="medium",
                summary="Sampled images have low entropy and may be visually uniform.",
                details={"entropy_bits": aggregate.entropy_bits},
            )
        )
    if _has_extreme_brightness(aggregate):
        findings.append(
            DatasetQualityFinding(
                code="dataset_extreme_brightness",
                severity="medium",
                summary="Sampled images are very dark or very bright on average.",
                details={"brightness_mean": aggregate.brightness_mean},
            )
        )
    return findings


def _status(
    *,
    image_paths: list[Path],
    metrics: list[ImageQualityMetrics],
    findings: list[DatasetQualityFinding],
) -> DiagnosticStatus:
    if not image_paths:
        return "warning"
    if not metrics:
        return "warning"
    if findings:
        return "warning"
    return "ok"


def _recommended_next_tools(
    *,
    status: DiagnosticStatus,
    findings: list[DatasetQualityFinding],
) -> list[str]:
    if status == "error":
        return ["fix_dataset_path"]
    if any(finding.code == "sample_unreadable_images" for finding in findings):
        return ["fix_dataset_images", "inspect_dataset_quality"]
    return ["build_review_packet", "render_preview_batch", "compare_preview_runs"]


def _next_actions(
    *,
    status: DiagnosticStatus,
    findings: list[DatasetQualityFinding],
) -> list[str]:
    if status == "error":
        return ["Fix the dataset path before running dataset onboarding or previews."]
    if not findings:
        return ["Continue with build_review_packet, then validate and render the preview request."]
    return [
        "Review quality findings before accepting augmentation intensity.",
        "Start with low intensity and inspect the contact sheet before increasing variants.",
    ]


def _remediation_actions(findings: list[DatasetQualityFinding]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if any(finding.code == "sample_unreadable_images" for finding in findings):
        actions.append(
            {
                "code": "fix_unreadable_images",
                "severity": "high",
                "summary": "Remove, repair, or convert unreadable image files before preview rendering.",
            }
        )
    if any(finding.code == "dataset_exact_duplicate_images" for finding in findings):
        actions.append(
            {
                "code": "review_duplicate_images",
                "severity": "medium",
                "summary": "Review exact duplicate groups before splitting or sampling the dataset.",
            }
        )
    if any(finding.code == "dataset_class_imbalance" for finding in findings):
        actions.append(
            {
                "code": "review_class_balance",
                "severity": "medium",
                "summary": "Check whether minority classes need more source data or lighter augmentation.",
            }
        )
    if any(finding.code.startswith("dataset_") and "annotation" in finding.code for finding in findings):
        actions.append(
            {
                "code": "review_annotation_consistency",
                "severity": "medium",
                "summary": "Review missing, orphan, or invalid annotations before rendering annotated previews.",
            }
        )
    return actions


def _preview_blockers(findings: list[DatasetQualityFinding]) -> list[DatasetQualityFinding]:
    return [
        finding for finding in findings if finding.code == "sample_unreadable_images" or _is_annotation_blocker(finding)
    ]


def _preview_guard(preview_blockers: list[DatasetQualityFinding]) -> str:
    return "blocked_by_preview_blockers" if preview_blockers else "ready"


def _preview_guard_actions(preview_blockers: list[DatasetQualityFinding]) -> list[str]:
    actions: list[str] = []
    if any(finding.code == "sample_unreadable_images" for finding in preview_blockers):
        actions.append("Repair unreadable images before rendering previews.")
    if any(_is_annotation_blocker(finding) for finding in preview_blockers):
        actions.append("Fix high-severity annotation blockers before rendering annotated previews.")
    return actions


def _is_annotation_blocker(finding: DatasetQualityFinding) -> bool:
    return finding.severity == "high" and finding.code.startswith("dataset_") and "annotation" in finding.code


def _bounded_max_images(max_images: int) -> int:
    return max(1, min(max_images, _MAX_IMAGES_LIMIT))


def _is_allowed(path: Path, path_policy: PathPolicy) -> bool:
    return any(path == root or root in path.parents for root in path_policy.allowed_roots)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6)


def _has_extreme_brightness(aggregate: ImageQualityAggregate) -> bool:
    brightness = aggregate.brightness_mean
    return brightness is not None and (
        brightness <= _LOW_BRIGHTNESS_THRESHOLD or brightness >= _HIGH_BRIGHTNESS_THRESHOLD
    )


def _structure_health(*, dataset_path: Path, image_paths: list[Path]) -> DatasetStructureHealth:
    split_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    for path in image_paths:
        relative_parts = path.relative_to(dataset_path).parts
        split, class_name = _split_and_class(relative_parts)
        if split is not None:
            split_counts[split] += 1
        if class_name is not None:
            class_counts[class_name] += 1
    metadata_paths = image_paths[:_MAX_METADATA_IMAGES]
    return DatasetStructureHealth(
        split_distribution=dict(sorted(split_counts.items())),
        class_distribution=dict(sorted(class_counts.items())),
        image_size_summary=_image_size_summary(metadata_paths),
        duplicate_groups=_duplicate_groups(metadata_paths),
        annotation_summary=inspect_annotation_consistency(dataset_path=dataset_path, image_paths=metadata_paths),
    )


def _split_and_class(relative_parts: tuple[str, ...]) -> tuple[str | None, str | None]:
    if len(relative_parts) < _MIN_CLASS_PATH_PARTS:
        return None, None
    first = relative_parts[0].lower()
    if first in _KNOWN_SPLITS:
        class_name = relative_parts[1] if len(relative_parts) >= _SPLIT_WITH_CLASS_PATH_PARTS else None
        return _KNOWN_SPLITS[first], class_name
    return None, relative_parts[0]


def _image_size_summary(paths: list[Path]) -> DatasetImageSizeSummary | None:
    sizes: list[tuple[int, int]] = []
    for path in paths:
        size = _safe_image_size(path)
        if size is not None:
            sizes.append(size)
    if not sizes:
        return None
    widths = [width for width, _height in sizes]
    heights = [height for _width, height in sizes]
    ratios = [width / height for width, height in sizes if height > 0]
    return DatasetImageSizeSummary(
        image_count=len(sizes),
        min_width=min(widths),
        max_width=max(widths),
        min_height=min(heights),
        max_height=max(heights),
        aspect_ratio_min=round(min(ratios), 6),
        aspect_ratio_max=round(max(ratios), 6),
    )


def _safe_image_size(path: Path) -> tuple[int, int] | None:
    try:
        with Image.open(path) as image:
            return image.size
    except (OSError, ValueError):
        return None


def _duplicate_groups(paths: list[Path]) -> list[DatasetDuplicateGroup]:
    paths_by_hash: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        digest = _safe_sha256(path)
        if digest is not None:
            paths_by_hash[digest].append(path)
    groups = [
        DatasetDuplicateGroup(
            sha256=digest,
            image_count=len(group_paths),
            sample_paths=[str(path) for path in group_paths[:3]],
        )
        for digest, group_paths in sorted(paths_by_hash.items())
        if len(group_paths) > 1
    ]
    return groups[:_MAX_DUPLICATE_GROUPS]


def _safe_sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _is_imbalanced(distribution: dict[str, int], *, min_ratio: float) -> bool:
    if len(distribution) < _MIN_IMBALANCE_BUCKETS:
        return False
    counts = [count for count in distribution.values() if count > 0]
    return bool(counts) and min(counts) / max(counts) <= min_ratio


def _has_large_aspect_ratio_spread(summary: DatasetImageSizeSummary | None) -> bool:
    if summary is None or summary.aspect_ratio_min <= 0:
        return False
    return summary.aspect_ratio_max / summary.aspect_ratio_min >= _ASPECT_RATIO_SPREAD


def _annotation_findings(summary: DatasetAnnotationSummary) -> list[DatasetQualityFinding]:
    findings: list[DatasetQualityFinding] = []
    if summary.missing_annotation_count:
        findings.append(
            DatasetQualityFinding(
                code="dataset_missing_annotations",
                severity="medium",
                summary="Some dataset images do not have matching annotations.",
                sample_paths=summary.sample_missing_paths,
                details={
                    "source_format": summary.source_format,
                    "missing_annotation_count": summary.missing_annotation_count,
                },
            )
        )
    if summary.orphan_annotation_count:
        findings.append(
            DatasetQualityFinding(
                code="dataset_orphan_annotations",
                severity="medium",
                summary="Some annotations reference images that were not found in the dataset sample.",
                sample_paths=summary.sample_orphan_references,
                details={
                    "source_format": summary.source_format,
                    "orphan_annotation_count": summary.orphan_annotation_count,
                },
            )
        )
    if summary.invalid_annotation_count:
        findings.append(
            DatasetQualityFinding(
                code="dataset_invalid_annotations",
                severity="high",
                summary="Some annotation records are malformed.",
                sample_paths=summary.sample_invalid_references,
                details={
                    "source_format": summary.source_format,
                    "invalid_annotation_count": summary.invalid_annotation_count,
                },
            )
        )
    if summary.out_of_bounds_annotation_count:
        findings.append(
            DatasetQualityFinding(
                code="dataset_out_of_bounds_annotations",
                severity="high",
                summary="Some annotation boxes fall outside image bounds.",
                sample_paths=summary.sample_out_of_bounds_references,
                details={
                    "source_format": summary.source_format,
                    "out_of_bounds_annotation_count": summary.out_of_bounds_annotation_count,
                },
            )
        )
    if summary.unknown_category_annotation_count:
        findings.append(
            DatasetQualityFinding(
                code="dataset_unknown_category_annotations",
                severity="high",
                summary="Some annotations reference category ids missing from the category catalog.",
                sample_paths=summary.sample_unknown_category_references,
                details={
                    "source_format": summary.source_format,
                    "unknown_category_annotation_count": summary.unknown_category_annotation_count,
                },
            )
        )
    return findings
