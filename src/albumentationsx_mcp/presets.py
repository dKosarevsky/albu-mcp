"""Conservative task presets and feedback adjustments."""

from __future__ import annotations

from typing import Literal

from albumentationsx_mcp.feedback import normalize_feedback_tags, severity_scaled_factor
from albumentationsx_mcp.models import ComposeSpec, TransformSpec

Intensity = Literal["low", "medium", "high"]


def recommend_pipeline(task: str, intensity: Intensity = "medium", targets: list[str] | None = None) -> ComposeSpec:
    """Create a conservative reproducible pipeline for a common CV task."""
    normalized_task = task.lower().replace("-", "_")
    target_set = set(targets or ["image"])
    probability = {"low": 0.2, "medium": 0.4, "high": 0.65}[intensity]

    transforms = [TransformSpec(name="HorizontalFlip", p=probability)]
    bbox_params = None
    keypoint_params = None

    if normalized_task in {"object_detection", "detection"}:
        transforms.extend(
            [
                TransformSpec(name="Affine", params={"scale": (0.9, 1.1), "rotate": (-8, 8)}, p=probability),
                TransformSpec(name="RandomBrightnessContrast", p=min(probability, 0.5)),
            ],
        )
        if "bboxes" in target_set:
            bbox_params = {"format": "pascal_voc", "label_fields": ["labels"]}
    elif normalized_task in {"segmentation", "semantic_segmentation", "instance_segmentation"}:
        transforms.extend(
            [
                TransformSpec(name="Affine", params={"scale": (0.95, 1.05), "rotate": (-5, 5)}, p=probability),
                TransformSpec(name="RandomBrightnessContrast", p=min(probability, 0.5)),
                TransformSpec(name="GaussNoise", params={"std_range": (0.02, 0.08)}, p=probability / 2),
            ],
        )
    elif normalized_task in {"ocr", "document", "document_distortion"}:
        transforms.extend(
            [
                TransformSpec(name="Perspective", params={"scale": (0.02, 0.06)}, p=probability),
                TransformSpec(name="ImageCompression", params={"quality_range": (70, 100)}, p=probability),
            ],
        )
    else:
        transforms.extend(
            [
                TransformSpec(name="RandomBrightnessContrast", p=min(probability, 0.5)),
                TransformSpec(name="GaussNoise", params={"std_range": (0.02, 0.1)}, p=probability / 2),
                TransformSpec(name="MotionBlur", params={"blur_range": (3, 5)}, p=probability / 3),
            ],
        )

    if "keypoints" in target_set:
        keypoint_params = {"format": "xy", "remove_invisible": False}

    return ComposeSpec(transforms=transforms, bbox_params=bbox_params, keypoint_params=keypoint_params, seed=137)


def adjust_pipeline(pipeline: ComposeSpec, feedback_tags: list[str]) -> ComposeSpec:
    """Adjust a pipeline using structured preview feedback tags."""
    adjusted = pipeline.model_copy(deep=True)
    tags = normalize_feedback_tags(feedback_tags)

    for transform in adjusted.transforms:
        name = transform.name.lower()
        if "too_noisy" in tags and "noise" in name:
            severity = tags["too_noisy"]
            _scale_probability(transform, severity_scaled_factor(0.5, severity))
            _scale_numeric_ranges(transform, severity_scaled_factor(0.5, severity))
        if "too_blurry" in tags and "blur" in name:
            severity = tags["too_blurry"]
            _scale_probability(transform, severity_scaled_factor(0.5, severity))
            _scale_numeric_ranges(transform, severity_scaled_factor(0.75, severity))
        if "too_distorted" in tags and any(token in name for token in ["affine", "perspective", "distortion"]):
            severity = tags["too_distorted"]
            _scale_probability(transform, severity_scaled_factor(0.6, severity))
            _scale_numeric_ranges(transform, severity_scaled_factor(0.75, severity))
        if any(tag in tags for tag in ["too_dark", "too_bright"]) and _is_exposure_transform(name):
            severity = tags.get("too_dark", tags.get("too_bright", "medium"))
            _scale_probability(transform, severity_scaled_factor(0.6, severity))
            _scale_numeric_ranges(transform, severity_scaled_factor(0.6, severity))
        if "color_shift" in tags and _is_color_shift_transform(name):
            severity = tags["color_shift"]
            _scale_probability(transform, severity_scaled_factor(0.5, severity))
            _scale_numeric_ranges(transform, severity_scaled_factor(0.5, severity))
        if "object_unrecognizable" in tags:
            severity = tags["object_unrecognizable"]
            _scale_probability(transform, severity_scaled_factor(0.7, severity))
            if any(token in name for token in ["noise", "blur", "dropout", "compression"]):
                _scale_numeric_ranges(transform, severity_scaled_factor(0.6, severity))

    return adjusted


def _scale_probability(transform: TransformSpec, factor: float) -> None:
    current = 0.5 if transform.p is None else transform.p
    transform.p = round(max(0.0, min(1.0, current * factor)), 4)


def _is_exposure_transform(name: str) -> bool:
    return any(token in name for token in ["brightness", "contrast"])


def _is_color_shift_transform(name: str) -> bool:
    return any(token in name for token in ["hue", "saturation", "rgb", "color"])


def _scale_numeric_ranges(transform: TransformSpec, factor: float) -> None:
    for key, value in list(transform.params.items()):
        if isinstance(value, tuple):
            transform.params[key] = tuple(_scale_value(item, factor) for item in value)
        elif isinstance(value, list):
            transform.params[key] = [_scale_value(item, factor) for item in value]
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            transform.params[key] = _scale_value(value, factor)


def _scale_value(value: object, factor: float) -> object:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return round(value * factor)
    if isinstance(value, float):
        return round(value * factor, 6)
    return value
