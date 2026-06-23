"""Read-only dataset quality inspection before preview rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field

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


class DatasetQualityFinding(StrictModel):
    """One machine-readable dataset quality finding."""

    code: str
    severity: DiagnosticSeverity
    summary: str
    sample_paths: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class DatasetQualityReport(StrictModel):
    """Read-only quality report for a sampled local dataset folder."""

    status: DiagnosticStatus
    dataset_path: str
    allowed_roots: list[str]
    image_count: int = 0
    sampled_image_count: int = 0
    ignored_file_count: int = 0
    unreadable_image_count: int = 0
    sample_paths: list[str] = Field(default_factory=list)
    unreadable_paths: list[str] = Field(default_factory=list)
    aggregate: ImageQualityAggregate
    sample_metrics: list[ImageQualityMetrics] = Field(default_factory=list)
    findings: list[DatasetQualityFinding] = Field(default_factory=list)
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
    findings = _findings(aggregate=aggregate, unreadable_paths=unreadable_paths)
    status = _status(image_paths=image_paths, metrics=metrics, findings=findings)
    return DatasetQualityReport(
        status=status,
        dataset_path=str(resolved),
        allowed_roots=[str(root) for root in path_policy.allowed_roots],
        image_count=len(image_paths),
        sampled_image_count=len(sampled_paths),
        ignored_file_count=ignored_file_count,
        unreadable_image_count=len(unreadable_paths),
        sample_paths=[str(path) for path in sampled_paths],
        unreadable_paths=[str(path) for path in unreadable_paths],
        aggregate=aggregate,
        sample_metrics=metrics,
        findings=findings,
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
    return actions


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
