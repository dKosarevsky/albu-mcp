"""Read-only annotation subset extraction for dataset onboarding."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal

from PIL import Image
from pydantic import Field

from albumentationsx_mcp.models import ImageAnnotations, StrictModel

_MAX_COCO_MANIFEST_BYTES = 5_000_000
_COCO_BBOX_VALUES = 4
_YOLO_BBOX_VALUES = 5


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
        bboxes_by_image_id = _coco_bboxes_by_image_id(payload, category_names)
        for index, image_ids in image_ids_by_index.items():
            annotation = _merge_image_annotations(
                bboxes_by_image_id.get(image_id, ImageAnnotations()) for image_id in image_ids
            )
            if annotation.bboxes:
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
        annotations.append(annotation if annotation.bboxes else None)
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


def _coco_bboxes_by_image_id(
    payload: dict[str, Any],
    category_names: dict[int, str | int],
) -> dict[int, ImageAnnotations]:
    grouped: dict[int, ImageAnnotations] = defaultdict(ImageAnnotations)
    for item in payload.get("annotations", []):
        if not isinstance(item, dict):
            continue
        image_id = item.get("image_id")
        bbox = item.get("bbox")
        if not isinstance(image_id, int) or not _is_number_list(bbox, _COCO_BBOX_VALUES):
            continue
        x_min, y_min, width, height = [float(value) for value in bbox[:_COCO_BBOX_VALUES]]
        grouped[image_id].bboxes.append([x_min, y_min, x_min + width, y_min + height])
        category_id = item.get("category_id")
        grouped[image_id].bbox_labels.append(category_names.get(category_id, category_id))
    return dict(grouped)


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
            x_center, y_center, box_width, box_height = [float(value) for value in values[1:_YOLO_BBOX_VALUES]]
        except ValueError:
            continue
        x_min = (x_center - (box_width / 2.0)) * width
        y_min = (y_center - (box_height / 2.0)) * height
        x_max = (x_center + (box_width / 2.0)) * width
        y_max = (y_center + (box_height / 2.0)) * height
        annotation.bboxes.append([x_min, y_min, x_max, y_max])
        annotation.bbox_labels.append(class_id)
    return annotation


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


def _merge_image_annotations(annotations: object) -> ImageAnnotations:
    merged = ImageAnnotations()
    for annotation in annotations:
        if not isinstance(annotation, ImageAnnotations):
            continue
        merged.bboxes.extend(annotation.bboxes)
        merged.bbox_labels.extend(annotation.bbox_labels)
    return merged


def _missing_annotation_warnings(annotations: list[ImageAnnotations | None]) -> list[str]:
    missing_count = sum(annotation is None for annotation in annotations)
    if missing_count == 0:
        return []
    return [f"{missing_count} sampled image(s) are without annotations."]


def _is_number_list(value: object, min_length: int) -> bool:
    return isinstance(value, list) and len(value) >= min_length and all(_is_number(item) for item in value[:min_length])


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
