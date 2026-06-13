"""Local preview artifact quality metrics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from albumentationsx_mcp.models import (
    AnnotationObservation,
    AnnotationQualityAggregate,
    ImageQualityAggregate,
    ImageQualityMetrics,
    PreviewAnnotationQualitySummary,
    PreviewQualitySummary,
    QualityFinding,
)

_METRIC_FIELDS = (
    "brightness_mean",
    "contrast_std",
    "sharpness_score",
    "saturation_mean",
    "colorfulness_score",
    "entropy_bits",
    "clipping_fraction",
)
_MIN_SHARPNESS_SIDE = 2
_LOW_BRIGHTNESS_HIGH = 35.0
_LOW_BRIGHTNESS_MEDIUM = 55.0
_HIGH_BRIGHTNESS_HIGH = 220.0
_HIGH_BRIGHTNESS_MEDIUM = 200.0
_HIGH_CLIPPING_HIGH = 0.5
_HIGH_CLIPPING_MEDIUM = 0.1
_LOW_ENTROPY_MEDIUM = 0.4
_CLIPPING_LOW_VALUE = 2.0
_CLIPPING_HIGH_VALUE = 253.0
_SHARPNESS_DROP_MEDIUM = -20.0
_MASK_COVERAGE_DROP_MEDIUM = 0.75
_MASK_COVERAGE_DROP_HIGH = 0.25


def collect_image_quality_metrics(path: Path) -> ImageQualityMetrics:
    """Collect lightweight quality metrics for one local image artifact."""
    image = Image.open(path).convert("RGB")
    rgb = np.asarray(image, dtype=np.float32)
    gray = np.asarray(image.convert("L"), dtype=np.float32)
    hsv = np.asarray(image.convert("HSV"), dtype=np.float32)
    return ImageQualityMetrics(
        path=str(path),
        brightness_mean=round(float(gray.mean()), 4),
        contrast_std=round(float(gray.std()), 4),
        sharpness_score=round(_sharpness_score(gray), 4),
        saturation_mean=round(float(hsv[:, :, 1].mean()), 4),
        colorfulness_score=round(_colorfulness_score(rgb), 4),
        entropy_bits=round(_entropy_bits(gray), 4),
        clipping_fraction=round(_clipping_fraction(rgb), 4),
    )


def compare_manifest_quality(
    baseline_manifest: dict[str, Any],
    candidate_manifest: dict[str, Any],
) -> tuple[PreviewQualitySummary | None, list[str]]:
    """Compare image quality metrics for preview image artifacts in two manifests."""
    warnings: list[str] = []
    baseline = _collect_manifest_metrics(baseline_manifest, label="baseline", warnings=warnings)
    candidate = _collect_manifest_metrics(candidate_manifest, label="candidate", warnings=warnings)
    annotation_summary = _compare_annotation_quality(baseline_manifest, candidate_manifest, warnings=warnings)
    if not baseline and not candidate and annotation_summary is None:
        return None, warnings

    baseline_aggregate = _aggregate_quality_metrics(baseline)
    candidate_aggregate = _aggregate_quality_metrics(candidate)
    return (
        PreviewQualitySummary(
            baseline=baseline_aggregate,
            candidate=candidate_aggregate,
            deltas=_quality_deltas(baseline_aggregate, candidate_aggregate),
            findings=_quality_findings(baseline_aggregate, candidate_aggregate, annotation_summary),
            annotation_summary=annotation_summary,
        ),
        warnings,
    )


def _sharpness_score(pixels: np.ndarray) -> float:
    if pixels.shape[0] < _MIN_SHARPNESS_SIDE or pixels.shape[1] < _MIN_SHARPNESS_SIDE:
        return 0.0
    horizontal = np.abs(np.diff(pixels, axis=1)).mean()
    vertical = np.abs(np.diff(pixels, axis=0)).mean()
    return float((horizontal + vertical) / 2)


def _colorfulness_score(rgb: np.ndarray) -> float:
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    red_green = red - green
    yellow_blue = 0.5 * (red + green) - blue
    std_root = np.sqrt(red_green.std() ** 2 + yellow_blue.std() ** 2)
    mean_root = np.sqrt(red_green.mean() ** 2 + yellow_blue.mean() ** 2)
    return float(std_root + (0.3 * mean_root))


def _entropy_bits(gray: np.ndarray) -> float:
    histogram = np.bincount(gray.astype(np.uint8).ravel(), minlength=256)
    probabilities = histogram[histogram > 0] / gray.size
    return float(-(probabilities * np.log2(probabilities)).sum())


def _clipping_fraction(rgb: np.ndarray) -> float:
    clipped = (rgb <= _CLIPPING_LOW_VALUE) | (rgb >= _CLIPPING_HIGH_VALUE)
    return float(clipped.mean())


def _collect_manifest_metrics(
    manifest: dict[str, Any],
    *,
    label: str,
    warnings: list[str],
) -> list[ImageQualityMetrics]:
    metrics: list[ImageQualityMetrics] = []
    for path in _image_artifact_paths(manifest):
        metric, warning = _safe_collect_image_quality_metric(path, label=label)
        if metric is not None:
            metrics.append(metric)
        if warning is not None:
            warnings.append(warning)
    return metrics


def _safe_collect_image_quality_metric(path: Path, *, label: str) -> tuple[ImageQualityMetrics | None, str | None]:
    try:
        return collect_image_quality_metrics(path), None
    except OSError as exc:
        return None, f"{label} quality skipped for {path}: {exc}"


def _image_artifact_paths(manifest: dict[str, Any]) -> list[Path]:
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        return []
    return [
        Path(str(artifact["path"]))
        for artifact in artifacts
        if isinstance(artifact, dict) and artifact.get("kind") == "image" and "path" in artifact
    ]


def _aggregate_quality_metrics(metrics: list[ImageQualityMetrics]) -> ImageQualityAggregate:
    if not metrics:
        return ImageQualityAggregate(image_count=0)
    return ImageQualityAggregate(
        image_count=len(metrics),
        brightness_mean=_average(metrics, "brightness_mean"),
        contrast_std=_average(metrics, "contrast_std"),
        sharpness_score=_average(metrics, "sharpness_score"),
        saturation_mean=_average(metrics, "saturation_mean"),
        colorfulness_score=_average(metrics, "colorfulness_score"),
        entropy_bits=_average(metrics, "entropy_bits"),
        clipping_fraction=_average(metrics, "clipping_fraction"),
    )


def _average(metrics: list[ImageQualityMetrics], field_name: str) -> float:
    return round(sum(float(getattr(metric, field_name)) for metric in metrics) / len(metrics), 4)


def _quality_deltas(baseline: ImageQualityAggregate, candidate: ImageQualityAggregate) -> dict[str, float]:
    deltas: dict[str, float] = {}
    for field_name in _METRIC_FIELDS:
        baseline_value = getattr(baseline, field_name)
        candidate_value = getattr(candidate, field_name)
        if baseline_value is not None and candidate_value is not None:
            deltas[field_name] = round(float(candidate_value) - float(baseline_value), 4)
    return deltas


def _quality_findings(
    baseline: ImageQualityAggregate,
    candidate: ImageQualityAggregate,
    annotation_summary: PreviewAnnotationQualitySummary | None,
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    if candidate.brightness_mean is not None:
        findings.extend(_brightness_findings(candidate.brightness_mean, baseline.brightness_mean))
    if candidate.clipping_fraction is not None:
        findings.extend(_clipping_findings(candidate.clipping_fraction, baseline.clipping_fraction))
    if candidate.entropy_bits is not None and candidate.entropy_bits < _LOW_ENTROPY_MEDIUM:
        findings.append(
            QualityFinding(
                code="candidate_low_entropy",
                severity="medium",
                message="Candidate preview has very low tonal entropy and may hide useful variation.",
                metric="entropy_bits",
                value=candidate.entropy_bits,
                baseline_value=baseline.entropy_bits,
            ),
        )
    if baseline.sharpness_score is not None and candidate.sharpness_score is not None:
        sharpness_delta = candidate.sharpness_score - baseline.sharpness_score
        if sharpness_delta <= _SHARPNESS_DROP_MEDIUM:
            findings.append(
                QualityFinding(
                    code="candidate_sharpness_drop",
                    severity="medium",
                    message="Candidate preview is substantially less sharp than the baseline.",
                    metric="sharpness_score",
                    value=candidate.sharpness_score,
                    baseline_value=baseline.sharpness_score,
                ),
            )
    if annotation_summary is not None:
        findings.extend(_annotation_quality_findings(annotation_summary))
    return findings


def _brightness_findings(value: float, baseline_value: float | None) -> list[QualityFinding]:
    if value < _LOW_BRIGHTNESS_HIGH:
        return [
            QualityFinding(
                code="candidate_too_dark",
                severity="high",
                message="Candidate preview is very dark.",
                metric="brightness_mean",
                value=value,
                baseline_value=baseline_value,
            ),
        ]
    if value < _LOW_BRIGHTNESS_MEDIUM:
        return [
            QualityFinding(
                code="candidate_too_dark",
                severity="medium",
                message="Candidate preview is darker than recommended for review.",
                metric="brightness_mean",
                value=value,
                baseline_value=baseline_value,
            ),
        ]
    if value > _HIGH_BRIGHTNESS_HIGH:
        return [
            QualityFinding(
                code="candidate_too_bright",
                severity="high",
                message="Candidate preview is very bright.",
                metric="brightness_mean",
                value=value,
                baseline_value=baseline_value,
            ),
        ]
    if value > _HIGH_BRIGHTNESS_MEDIUM:
        return [
            QualityFinding(
                code="candidate_too_bright",
                severity="medium",
                message="Candidate preview is brighter than recommended for review.",
                metric="brightness_mean",
                value=value,
                baseline_value=baseline_value,
            ),
        ]
    return []


def _clipping_findings(value: float, baseline_value: float | None) -> list[QualityFinding]:
    if value >= _HIGH_CLIPPING_HIGH:
        return [
            QualityFinding(
                code="candidate_high_clipping",
                severity="high",
                message="Candidate preview has a high fraction of clipped dark or bright pixels.",
                metric="clipping_fraction",
                value=value,
                baseline_value=baseline_value,
            ),
        ]
    if value >= _HIGH_CLIPPING_MEDIUM:
        return [
            QualityFinding(
                code="candidate_high_clipping",
                severity="medium",
                message="Candidate preview has noticeable clipped dark or bright pixels.",
                metric="clipping_fraction",
                value=value,
                baseline_value=baseline_value,
            ),
        ]
    return []


def _compare_annotation_quality(
    baseline_manifest: dict[str, Any],
    candidate_manifest: dict[str, Any],
    *,
    warnings: list[str],
) -> PreviewAnnotationQualitySummary | None:
    baseline_observations = _collect_annotation_observations(baseline_manifest, label="baseline", warnings=warnings)
    candidate_observations = _collect_annotation_observations(candidate_manifest, label="candidate", warnings=warnings)
    if not baseline_observations and not candidate_observations:
        return None

    baseline = _aggregate_annotation_observations(baseline_observations)
    candidate = _aggregate_annotation_observations(candidate_observations)
    return PreviewAnnotationQualitySummary(
        baseline=baseline,
        candidate=candidate,
        deltas=_annotation_deltas(baseline, candidate),
    )


def _collect_annotation_observations(
    manifest: dict[str, Any],
    *,
    label: str,
    warnings: list[str],
) -> list[AnnotationObservation]:
    observations = manifest.get("annotation_observations", [])
    if not isinstance(observations, list):
        warnings.append(f"{label} annotation quality skipped: annotation_observations is not a list")
        return []

    parsed: list[AnnotationObservation] = []
    for index, observation in enumerate(observations):
        parsed_observation, exc = _parse_annotation_observation(observation)
        if parsed_observation is not None:
            parsed.append(parsed_observation)
        else:
            warnings.append(f"{label} annotation observation {index} skipped: {exc}")
    return parsed


def _parse_annotation_observation(observation: Any) -> tuple[AnnotationObservation | None, ValueError | None]:
    try:
        return AnnotationObservation.model_validate(observation), None
    except ValueError as exc:
        return None, exc


def _aggregate_annotation_observations(observations: list[AnnotationObservation]) -> AnnotationQualityAggregate:
    input_bbox_count = sum(observation.input_bbox_count for observation in observations)
    output_bbox_count = sum(observation.output_bbox_count for observation in observations)
    input_keypoint_count = sum(observation.input_keypoint_count for observation in observations)
    output_keypoint_count = sum(observation.output_keypoint_count for observation in observations)
    input_mask_coverage_mean = _mean_optional([observation.input_mask_coverage for observation in observations])
    output_mask_coverage_mean = _mean_optional([observation.output_mask_coverage for observation in observations])
    return AnnotationQualityAggregate(
        observation_count=len(observations),
        input_bbox_count=input_bbox_count,
        output_bbox_count=output_bbox_count,
        bbox_retention_ratio=_ratio(output_bbox_count, input_bbox_count),
        input_keypoint_count=input_keypoint_count,
        output_keypoint_count=output_keypoint_count,
        keypoint_retention_ratio=_ratio(output_keypoint_count, input_keypoint_count),
        input_mask_coverage_mean=input_mask_coverage_mean,
        output_mask_coverage_mean=output_mask_coverage_mean,
        mask_coverage_ratio=_ratio_optional(output_mask_coverage_mean, input_mask_coverage_mean),
    )


def _annotation_deltas(
    baseline: AnnotationQualityAggregate,
    candidate: AnnotationQualityAggregate,
) -> dict[str, float]:
    deltas: dict[str, float] = {}
    for field_name in ("bbox_retention_ratio", "keypoint_retention_ratio", "mask_coverage_ratio"):
        baseline_value = getattr(baseline, field_name)
        candidate_value = getattr(candidate, field_name)
        if baseline_value is not None and candidate_value is not None:
            deltas[field_name] = round(float(candidate_value) - float(baseline_value), 4)
    return deltas


def _annotation_quality_findings(summary: PreviewAnnotationQualitySummary) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    candidate = summary.candidate
    baseline = summary.baseline
    if candidate.bbox_retention_ratio is not None and candidate.bbox_retention_ratio < 1.0:
        findings.append(
            QualityFinding(
                code="candidate_bbox_loss",
                severity="high" if candidate.bbox_retention_ratio == 0 else "medium",
                message="Candidate preview drops bounding boxes from annotated inputs.",
                metric="bbox_retention_ratio",
                value=candidate.bbox_retention_ratio,
                baseline_value=baseline.bbox_retention_ratio,
            ),
        )
    if candidate.keypoint_retention_ratio is not None and candidate.keypoint_retention_ratio < 1.0:
        findings.append(
            QualityFinding(
                code="candidate_keypoint_loss",
                severity="high" if candidate.keypoint_retention_ratio == 0 else "medium",
                message="Candidate preview drops keypoints from annotated inputs.",
                metric="keypoint_retention_ratio",
                value=candidate.keypoint_retention_ratio,
                baseline_value=baseline.keypoint_retention_ratio,
            ),
        )
    if candidate.mask_coverage_ratio is not None and candidate.mask_coverage_ratio < _MASK_COVERAGE_DROP_MEDIUM:
        findings.append(
            QualityFinding(
                code="candidate_mask_coverage_drop",
                severity="high" if candidate.mask_coverage_ratio < _MASK_COVERAGE_DROP_HIGH else "medium",
                message="Candidate preview reduces transformed mask coverage substantially.",
                metric="mask_coverage_ratio",
                value=candidate.mask_coverage_ratio,
                baseline_value=baseline.mask_coverage_ratio,
            ),
        )
    return findings


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _ratio_optional(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0.0:
        return None
    return round(numerator / denominator, 4)


def _mean_optional(values: list[float | None]) -> float | None:
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    return round(sum(filtered) / len(filtered), 4)
