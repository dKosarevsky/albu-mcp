"""Read-only annotation subset extraction for dataset onboarding."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal, TypeGuard

from PIL import Image
from pydantic import Field

from albumentationsx_mcp.annotations import decode_coco_rle
from albumentationsx_mcp.models import ImageAnnotations, MaskRLE, StrictModel

_MAX_COCO_MANIFEST_BYTES = 5_000_000
_COCO_BBOX_VALUES = 4
_YOLO_BBOX_VALUES = 5
_YOLO_SEGMENTATION_MIN_VALUES = 7
_POLYGON_PAIR_SIZE = 2
_POLYGON_BBOX_MIN_VALUES = 6
_RLE_SIZE_VALUES = 2


class SampleAnnotationSet(StrictModel):
    """Annotation subset aligned with sampled preview images."""

    source_format: Literal["coco", "yolo"]
    annotations: list[ImageAnnotations | None]
    matched_count: int
    warnings: list[str] = Field(default_factory=list)


def build_sample_annotations(dataset_path: Path, sample_paths: list[Path]) -> SampleAnnotationSet | None:
    """Build preview annotations for sampled images from common local dataset formats."""
    resolved_dataset = dataset_path.resolve()
    resolved_samples = [path.resolve() for path in sample_paths]
    coco_annotations = _build_coco_annotations(resolved_dataset, resolved_samples)
    if coco_annotations is not None and coco_annotations.matched_count > 0:
        return coco_annotations
    yolo_annotations = _build_yolo_annotations(resolved_dataset, resolved_samples)
    if yolo_annotations is not None and yolo_annotations.matched_count > 0:
        return yolo_annotations
    return None


def _build_coco_annotations(dataset_path: Path, sample_paths: list[Path]) -> SampleAnnotationSet | None:
    sample_keys_by_index = [_sample_keys(dataset_path, path) for path in sample_paths]
    annotations_by_index: dict[int, ImageAnnotations] = {}
    warnings: list[str] = []
    for manifest_path in _coco_manifest_paths(dataset_path):
        payload = _read_json_manifest(manifest_path)
        if payload is None:
            warnings.append(f"Skipped unreadable COCO manifest: {manifest_path}")
            continue
        image_ids_by_index = _coco_image_ids_by_sample_index(payload, sample_keys_by_index)
        if not image_ids_by_index:
            continue
        category_names = _coco_category_names(payload)
        annotations_by_image_id = _coco_annotations_by_image_id(payload, category_names)
        for index, image_ids in image_ids_by_index.items():
            annotation = _merge_image_annotations(
                annotations_by_image_id.get(image_id, ImageAnnotations()) for image_id in image_ids
            )
            if _has_annotation_content(annotation):
                annotations_by_index[index] = annotation
    if not annotations_by_index:
        return None
    annotations = [annotations_by_index.get(index) for index in range(len(sample_paths))]
    return SampleAnnotationSet(
        source_format="coco",
        annotations=annotations,
        matched_count=sum(annotation is not None for annotation in annotations),
        warnings=[*warnings, *_missing_annotation_warnings(annotations)],
    )


def _build_yolo_annotations(dataset_path: Path, sample_paths: list[Path]) -> SampleAnnotationSet | None:
    annotations: list[ImageAnnotations | None] = []
    warnings: list[str] = []
    for image_path in sample_paths:
        label_path = _find_yolo_label_path(dataset_path, image_path)
        if label_path is None:
            annotations.append(None)
            continue
        annotation = _read_yolo_label(label_path, image_path)
        annotations.append(annotation if _has_annotation_content(annotation) else None)
    matched_count = sum(annotation is not None for annotation in annotations)
    if matched_count == 0:
        return None
    return SampleAnnotationSet(
        source_format="yolo",
        annotations=annotations,
        matched_count=matched_count,
        warnings=[*warnings, *_missing_annotation_warnings(annotations)],
    )


def _coco_manifest_paths(dataset_path: Path) -> list[Path]:
    return [
        path.resolve()
        for path in sorted(dataset_path.rglob("*.json"))
        if path.is_file() and path.stat().st_size <= _MAX_COCO_MANIFEST_BYTES
    ]


def _read_json_manifest(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not {"annotations", "categories", "images"}.issubset(payload):
        return None
    return payload


def _coco_image_ids_by_sample_index(
    payload: dict[str, Any],
    sample_keys_by_index: list[set[str]],
) -> dict[int, list[int]]:
    matches: dict[int, list[int]] = defaultdict(list)
    for image in payload.get("images", []):
        if not isinstance(image, dict):
            continue
        image_id = image.get("id")
        file_name = image.get("file_name")
        if not isinstance(image_id, int) or not isinstance(file_name, str):
            continue
        normalized_keys = {file_name, Path(file_name).name, Path(file_name).as_posix()}
        for index, sample_keys in enumerate(sample_keys_by_index):
            if sample_keys.intersection(normalized_keys):
                matches[index].append(image_id)
    return dict(matches)


def _coco_category_names(payload: dict[str, Any]) -> dict[int, str | int]:
    names: dict[int, str | int] = {}
    for category in payload.get("categories", []):
        if not isinstance(category, dict):
            continue
        category_id = category.get("id")
        name = category.get("name")
        if isinstance(category_id, int):
            names[category_id] = name if isinstance(name, str) and name else category_id
    return names


def _coco_annotations_by_image_id(
    payload: dict[str, Any],
    category_names: dict[int, str | int],
) -> dict[int, ImageAnnotations]:
    grouped: dict[int, ImageAnnotations] = defaultdict(ImageAnnotations)
    for item in payload.get("annotations", []):
        if not isinstance(item, dict):
            continue
        image_id = item.get("image_id")
        if not isinstance(image_id, int):
            continue
        annotation = grouped[image_id]
        bbox = item.get("bbox")
        polygons = _coco_segmentation_polygons(item.get("segmentation"))
        mask_rle = _coco_segmentation_rle(item.get("segmentation"))
        bbox_values = _coco_bbox_values(bbox)
        if bbox_values is None and polygons:
            bbox_values = _bbox_from_polygons(polygons)
        if bbox_values is None and mask_rle is not None:
            bbox_values = _bbox_from_rle(mask_rle)
        if bbox_values is not None:
            annotation.bboxes.append(bbox_values)
            category_id = item.get("category_id")
            annotation.bbox_labels.append(category_names.get(category_id, category_id))
        if polygons:
            annotation.mask_polygons.append(polygons)
        if mask_rle is not None:
            annotation.mask_rles.append(mask_rle)
    return dict(grouped)


def _coco_bbox_values(bbox: object) -> list[float] | None:
    if not _is_number_list(bbox, _COCO_BBOX_VALUES):
        return None
    x_min, y_min, width, height = [float(value) for value in bbox[:_COCO_BBOX_VALUES]]
    return [x_min, y_min, x_min + width, y_min + height]


def _coco_segmentation_polygons(segmentation: object) -> list[list[float]]:
    if not isinstance(segmentation, list):
        return []
    return [
        [float(value) for value in polygon]
        for polygon in segmentation
        if _is_number_list(polygon, _POLYGON_BBOX_MIN_VALUES) and len(polygon) % _POLYGON_PAIR_SIZE == 0
    ]


def _coco_segmentation_rle(segmentation: object) -> MaskRLE | None:
    if not isinstance(segmentation, dict):
        return None
    counts = segmentation.get("counts")
    size = segmentation.get("size")
    if not (_is_int_list(size) and len(size) == _RLE_SIZE_VALUES and all(value > 0 for value in size)):
        return None
    if _is_int_list(counts) and all(count >= 0 for count in counts):
        mask_rle = MaskRLE(counts=list(counts), size=list(size))
    elif isinstance(counts, str) and counts:
        mask_rle = MaskRLE(counts=counts, size=list(size))
    else:
        return None
    try:
        decode_coco_rle(mask_rle)
    except ValueError:
        return None
    return mask_rle


def _bbox_from_polygons(polygons: list[list[float]]) -> list[float] | None:
    coordinates = [coordinate for polygon in polygons for coordinate in polygon]
    if len(coordinates) < _POLYGON_BBOX_MIN_VALUES:
        return None
    x_values = coordinates[0::2]
    y_values = coordinates[1::2]
    return [min(x_values), min(y_values), max(x_values), max(y_values)]


def _bbox_from_rle(mask_rle: MaskRLE) -> list[float] | None:
    mask = decode_coco_rle(mask_rle)
    y_values, x_values = (mask > 0).nonzero()
    if len(x_values) == 0 or len(y_values) == 0:
        return None
    return [
        float(x_values.min()),
        float(y_values.min()),
        float(x_values.max() + 1),
        float(y_values.max() + 1),
    ]


def _find_yolo_label_path(dataset_path: Path, image_path: Path) -> Path | None:
    candidates = []
    try:
        relative = image_path.relative_to(dataset_path)
    except ValueError:
        relative = image_path.name
    if isinstance(relative, Path):
        candidates.extend(_relative_yolo_candidates(dataset_path, relative))
    candidates.append(dataset_path / "labels" / f"{image_path.stem}.txt")
    candidates.append(image_path.with_suffix(".txt"))
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _relative_yolo_candidates(dataset_path: Path, relative: Path) -> list[Path]:
    candidates = [dataset_path / "labels" / relative.with_suffix(".txt").name]
    parts = list(relative.parts)
    if parts and parts[0] == "images":
        candidates.append(dataset_path / "labels" / Path(*parts[1:]).with_suffix(".txt"))
    if "images" in parts:
        image_index = parts.index("images")
        replaced = [*parts[:image_index], "labels", *parts[image_index + 1 :]]
        candidates.append(dataset_path / Path(*replaced).with_suffix(".txt"))
    return candidates


def _read_yolo_label(label_path: Path, image_path: Path) -> ImageAnnotations:
    width, height = Image.open(image_path).size
    annotation = ImageAnnotations()
    for line in label_path.read_text(encoding="utf-8").splitlines():
        values = line.split()
        if len(values) < _YOLO_BBOX_VALUES:
            continue
        try:
            class_id = int(float(values[0]))
            coordinates = [float(value) for value in values[1:]]
        except ValueError:
            continue
        if _is_yolo_segmentation_values(coordinates):
            polygon = _yolo_polygon_to_pixels(coordinates, width, height)
            bbox = _bbox_from_polygons([polygon])
            if bbox is not None:
                annotation.bboxes.append(bbox)
                annotation.bbox_labels.append(class_id)
                annotation.mask_polygons.append([polygon])
            continue
        if len(coordinates) >= _COCO_BBOX_VALUES:
            x_center, y_center, box_width, box_height = coordinates[:_COCO_BBOX_VALUES]
            x_min = (x_center - (box_width / 2.0)) * width
            y_min = (y_center - (box_height / 2.0)) * height
            x_max = (x_center + (box_width / 2.0)) * width
            y_max = (y_center + (box_height / 2.0)) * height
            annotation.bboxes.append([x_min, y_min, x_max, y_max])
            annotation.bbox_labels.append(class_id)
    return annotation


def _is_yolo_segmentation_values(coordinates: list[float]) -> bool:
    return len(coordinates) >= _YOLO_SEGMENTATION_MIN_VALUES - 1 and len(coordinates) % _POLYGON_PAIR_SIZE == 0


def _yolo_polygon_to_pixels(coordinates: list[float], width: int, height: int) -> list[float]:
    polygon: list[float] = []
    for index in range(0, len(coordinates) - 1, _POLYGON_PAIR_SIZE):
        polygon.extend([coordinates[index] * width, coordinates[index + 1] * height])
    return polygon


def _sample_keys(dataset_path: Path, path: Path) -> set[str]:
    keys = {path.name}
    try:
        relative = path.relative_to(dataset_path)
    except ValueError:
        return keys
    keys.add(relative.as_posix())
    if relative.parts and relative.parts[0] == "images":
        keys.add(Path(*relative.parts[1:]).as_posix())
    return keys


def _merge_image_annotations(annotations: Iterable[ImageAnnotations]) -> ImageAnnotations:
    merged = ImageAnnotations()
    for annotation in annotations:
        if not isinstance(annotation, ImageAnnotations):
            continue
        merged.bboxes.extend(annotation.bboxes)
        merged.bbox_labels.extend(annotation.bbox_labels)
        merged.keypoints.extend(annotation.keypoints)
        merged.mask_polygons.extend(annotation.mask_polygons)
        merged.mask_rles.extend(annotation.mask_rles)
        if merged.mask_path is None:
            merged.mask_path = annotation.mask_path
    return merged


def _has_annotation_content(annotation: ImageAnnotations) -> bool:
    return bool(
        annotation.bboxes
        or annotation.keypoints
        or annotation.mask_path
        or annotation.mask_polygons
        or annotation.mask_rles
    )


def _missing_annotation_warnings(annotations: list[ImageAnnotations | None]) -> list[str]:
    missing_count = sum(annotation is None for annotation in annotations)
    if missing_count == 0:
        return []
    return [f"{missing_count} sampled image(s) are without annotations."]


def _is_number_list(value: object, min_length: int) -> TypeGuard[list[int | float]]:
    return isinstance(value, list) and len(value) >= min_length and all(_is_number(item) for item in value[:min_length])


def _is_int_list(value: object) -> TypeGuard[list[int]]:
    return isinstance(value, list) and all(isinstance(item, int) and not isinstance(item, bool) for item in value)


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
