"""Annotation preparation and overlay rendering for preview artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from albumentationsx_mcp.models import ImageAnnotations

_BOX_COLOR = (255, 64, 64, 255)
_KEYPOINT_COLOR = (0, 180, 255, 255)
_MASK_COLOR = (0, 210, 90, 100)
_BBOX_COORDINATES = 4
_KEYPOINT_COORDINATES = 2


def annotation_has_content(annotation: ImageAnnotations | None) -> bool:
    """Return true when an annotation should produce overlay artifacts."""
    return bool(annotation and (annotation.bboxes or annotation.keypoints or annotation.mask_path))


def scale_annotations(
    annotation: ImageAnnotations | None,
    *,
    original_size: tuple[int, int],
    output_size: tuple[int, int],
) -> ImageAnnotations | None:
    """Scale annotation coordinates when preview input images are resized."""
    if annotation is None:
        return None
    original_width, original_height = original_size
    output_width, output_height = output_size
    if original_width == output_width and original_height == output_height:
        return annotation

    scale_x = output_width / original_width
    scale_y = output_height / original_height
    return ImageAnnotations(
        bboxes=[_scale_bbox(bbox, scale_x, scale_y) for bbox in annotation.bboxes],
        bbox_labels=list(annotation.bbox_labels),
        keypoints=[_scale_keypoint(keypoint, scale_x, scale_y) for keypoint in annotation.keypoints],
        mask_path=annotation.mask_path,
    )


def load_mask(mask_path: Path | None, size: tuple[int, int]) -> np.ndarray | None:
    """Load an annotation mask as a single-channel array matching the preview image size."""
    if mask_path is None:
        return None
    return np.asarray(Image.open(mask_path).convert("L").resize(size, Image.Resampling.NEAREST))


def build_transform_payload(
    image: Image.Image,
    annotation: ImageAnnotations | None,
    mask: np.ndarray | None,
) -> dict[str, Any]:
    """Build keyword arguments for an Albumentations transform call."""
    payload: dict[str, Any] = {"image": np.asarray(image)}
    if annotation is None:
        return payload
    if annotation.bboxes:
        payload["bboxes"] = annotation.bboxes
        if annotation.bbox_labels:
            payload["labels"] = annotation.bbox_labels
    if annotation.keypoints:
        payload["keypoints"] = annotation.keypoints
    if mask is not None:
        payload["mask"] = mask
    return payload


def render_overlay(result: Mapping[str, Any]) -> Image.Image:
    """Render bboxes, keypoints, and masks over a transformed preview image."""
    base = Image.fromarray(np.asarray(result["image"])).convert("RGBA")
    mask = result.get("mask")
    if mask is not None:
        base = _apply_mask(base, np.asarray(mask))

    draw = ImageDraw.Draw(base)
    width = max(2, min(base.size) // 120)
    labels = list(result.get("labels") or [])
    for index, bbox in enumerate(result.get("bboxes") or []):
        label = str(labels[index]) if index < len(labels) else None
        _draw_bbox(draw, bbox, label, width)
    for keypoint in result.get("keypoints") or []:
        _draw_keypoint(draw, keypoint, width)
    return base.convert("RGB")


def _scale_bbox(bbox: list[float], scale_x: float, scale_y: float) -> list[float]:
    if len(bbox) < _BBOX_COORDINATES:
        return bbox
    scaled = list(bbox)
    scaled[0] *= scale_x
    scaled[2] *= scale_x
    scaled[1] *= scale_y
    scaled[3] *= scale_y
    return scaled


def _scale_keypoint(keypoint: list[float], scale_x: float, scale_y: float) -> list[float]:
    if len(keypoint) < _KEYPOINT_COORDINATES:
        return keypoint
    scaled = list(keypoint)
    scaled[0] *= scale_x
    scaled[1] *= scale_y
    return scaled


def _apply_mask(base: Image.Image, mask: np.ndarray) -> Image.Image:
    mask_layer_data = np.zeros((*mask.shape[:2], 4), dtype=np.uint8)
    mask_layer_data[mask > 0] = _MASK_COLOR
    mask_layer = Image.fromarray(mask_layer_data, mode="RGBA").resize(base.size, Image.Resampling.NEAREST)
    composed = base.copy()
    composed.alpha_composite(mask_layer)
    return composed


def _draw_bbox(draw: ImageDraw.ImageDraw, bbox: list[float], label: str | None, width: int) -> None:
    if len(bbox) < _BBOX_COORDINATES:
        return
    x_min, y_min, x_max, y_max = bbox[:4]
    draw.rectangle((x_min, y_min, x_max, y_max), outline=_BOX_COLOR, width=width)
    if label:
        draw.text((x_min + width, y_min + width), label, fill=_BOX_COLOR)


def _draw_keypoint(draw: ImageDraw.ImageDraw, keypoint: list[float], radius: int) -> None:
    if len(keypoint) < _KEYPOINT_COORDINATES:
        return
    x, y = keypoint[:2]
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=_KEYPOINT_COLOR)
