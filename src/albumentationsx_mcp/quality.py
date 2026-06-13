"""Local preview artifact quality metrics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from albumentationsx_mcp.models import ImageQualityAggregate, ImageQualityMetrics, PreviewQualitySummary

_METRIC_FIELDS = ("brightness_mean", "contrast_std", "sharpness_score")
_MIN_SHARPNESS_SIDE = 2


def collect_image_quality_metrics(path: Path) -> ImageQualityMetrics:
    """Collect lightweight quality metrics for one local image artifact."""
    image = Image.open(path).convert("L")
    pixels = np.asarray(image, dtype=np.float32)
    return ImageQualityMetrics(
        path=str(path),
        brightness_mean=round(float(pixels.mean()), 4),
        contrast_std=round(float(pixels.std()), 4),
        sharpness_score=round(_sharpness_score(pixels), 4),
    )


def compare_manifest_quality(
    baseline_manifest: dict[str, Any],
    candidate_manifest: dict[str, Any],
) -> tuple[PreviewQualitySummary | None, list[str]]:
    """Compare image quality metrics for preview image artifacts in two manifests."""
    warnings: list[str] = []
    baseline = _collect_manifest_metrics(baseline_manifest, label="baseline", warnings=warnings)
    candidate = _collect_manifest_metrics(candidate_manifest, label="candidate", warnings=warnings)
    if not baseline and not candidate:
        return None, warnings

    baseline_aggregate = _aggregate_quality_metrics(baseline)
    candidate_aggregate = _aggregate_quality_metrics(candidate)
    return (
        PreviewQualitySummary(
            baseline=baseline_aggregate,
            candidate=candidate_aggregate,
            deltas=_quality_deltas(baseline_aggregate, candidate_aggregate),
        ),
        warnings,
    )


def _sharpness_score(pixels: np.ndarray) -> float:
    if pixels.shape[0] < _MIN_SHARPNESS_SIDE or pixels.shape[1] < _MIN_SHARPNESS_SIDE:
        return 0.0
    horizontal = np.abs(np.diff(pixels, axis=1)).mean()
    vertical = np.abs(np.diff(pixels, axis=0)).mean()
    return float((horizontal + vertical) / 2)


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
