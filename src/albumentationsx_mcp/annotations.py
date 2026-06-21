"""Annotation preparation and overlay rendering for preview artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from albumentationsx_mcp.models import ImageAnnotations, MaskRLE

_BOX_COLOR = (255, 64, 64, 255)
_KEYPOINT_COLOR = (0, 180, 255, 255)
_MASK_COLOR = (0, 210, 90, 100)
_BBOX_COORDINATES = 4
_KEYPOINT_COORDINATES = 2
_POLYGON_MIN_POINTS = 3


def annotation_has_content(annotation: ImageAnnotations | None) -> bool:
    """Return true when an annotation should produce overlay artifacts."""
    return bool(
        annotation
        and (
            annotation.bboxes
            or annotation.keypoints
            or annotation.mask_path
            or annotation.mask_polygons
            or annotation.mask_rles
        )
    )


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
        mask_polygons=[
            [_scale_polygon(polygon, scale_x, scale_y) for polygon in item] for item in annotation.mask_polygons
        ],
        mask_rles=list(annotation.mask_rles),
    )


def load_mask(mask_path: Path | None, size: tuple[int, int]) -> np.ndarray | None:
    """Load an annotation mask as a single-channel array matching the preview image size."""
    if mask_path is None:
        return None
    return np.asarray(Image.open(mask_path).convert("L").resize(size, Image.Resampling.NEAREST))


def build_annotation_mask(annotation: ImageAnnotations | None, size: tuple[int, int]) -> np.ndarray | None:
    """Build a single-channel mask from path, polygon, and RLE annotation sources."""
    if annotation is None:
        return None
    masks: list[np.ndarray] = []
    path_mask = load_mask(annotation.mask_path, size)
    if path_mask is not None:
        masks.append(path_mask)
    polygon_mask = rasterize_polygons(annotation.mask_polygons, size)
    if polygon_mask is not None:
        masks.append(polygon_mask)
    masks.extend(decode_uncompressed_rle(mask_rle, size) for mask_rle in annotation.mask_rles)
    if not masks:
        return None
    combined = np.zeros((size[1], size[0]), dtype=np.uint8)
    for mask in masks:
        combined = np.maximum(combined, np.asarray(mask, dtype=np.uint8))
    return combined


def rasterize_polygons(polygons: list[list[list[float]]], size: tuple[int, int]) -> np.ndarray | None:
    """Rasterize annotation polygons into a binary mask for Albumentations transforms."""
    if not polygons:
        return None
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for instance in polygons:
        for polygon in instance:
            points = _polygon_points(polygon)
            if len(points) >= _POLYGON_MIN_POINTS:
                draw.polygon(points, fill=255)
    return np.asarray(mask, dtype=np.uint8)


def decode_uncompressed_rle(mask_rle: MaskRLE, size: tuple[int, int] | None = None) -> np.ndarray:
    """Decode an uncompressed COCO-style RLE mask, optionally resizing it."""
    height, width = mask_rle.size[:2]
    total = height * width
    values: list[int] = []
    current = 0
    for count in mask_rle.counts:
        values.extend([current] * max(0, count))
        current = 1 - current
    if len(values) < total:
        values.extend([0] * (total - len(values)))
    data = np.asarray(values[:total], dtype=np.uint8).reshape((width, height)).T * 255
    if size is None or size == (width, height):
        return data
    return np.asarray(Image.fromarray(data).resize(size, Image.Resampling.NEAREST), dtype=np.uint8)


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
    labels = annotation_values(result.get("labels"))
    for index, bbox in enumerate(annotation_values(result.get("bboxes"))):
        label = str(labels[index]) if index < len(labels) else None
        _draw_bbox(draw, bbox, label, width)
    for keypoint in annotation_values(result.get("keypoints")):
        _draw_keypoint(draw, keypoint, width)
    return base.convert("RGB")


def annotation_values(value: Any) -> list[Any]:
    """Return annotation container values without relying on ambiguous array truthiness."""
    if value is None:
        return []
    return list(value)


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


def _scale_polygon(polygon: list[float], scale_x: float, scale_y: float) -> list[float]:
    scaled = list(polygon)
    for index in range(0, len(scaled) - 1, 2):
        scaled[index] *= scale_x
        scaled[index + 1] *= scale_y
    return scaled


def _polygon_points(polygon: list[float]) -> list[tuple[float, float]]:
    return [(polygon[index], polygon[index + 1]) for index in range(0, len(polygon) - 1, 2)]


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
