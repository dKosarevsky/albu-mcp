"""Read-only dataset structure and annotation consistency inspection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from albumentationsx_mcp.models import StrictModel

AnnotationSourceFormat = Literal["coco", "yolo"]

_MAX_COCO_MANIFEST_BYTES = 5_000_000
_COCO_BBOX_VALUES = 4
_YOLO_BBOX_VALUES = 5


class DatasetAnnotationSummary(StrictModel):
    """Annotation consistency summary for a local dataset folder."""

    source_format: AnnotationSourceFormat
    image_count: int
    annotated_image_count: int
    missing_annotation_count: int
    orphan_annotation_count: int = 0
    invalid_annotation_count: int = 0
    out_of_bounds_annotation_count: int = 0
    category_count: int = 0
    sample_missing_paths: list[str] = Field(default_factory=list)
    sample_orphan_references: list[str] = Field(default_factory=list)
    sample_invalid_references: list[str] = Field(default_factory=list)
    sample_out_of_bounds_references: list[str] = Field(default_factory=list)


def inspect_annotation_consistency(
    *,
    dataset_path: Path,
    image_paths: list[Path],
) -> DatasetAnnotationSummary | None:
    """Inspect common local annotation formats without loading training data."""
    bounded_image_paths = image_paths
    coco_summary = _inspect_coco_annotations(dataset_path=dataset_path, image_paths=bounded_image_paths)
    if coco_summary is not None:
        return coco_summary
    return _inspect_yolo_annotations(dataset_path=dataset_path, image_paths=bounded_image_paths)


def _inspect_coco_annotations(*, dataset_path: Path, image_paths: list[Path]) -> DatasetAnnotationSummary | None:
    for manifest_path in _coco_manifest_paths(dataset_path):
        payload = _read_coco_manifest(manifest_path)
        if payload is None:
            continue
        return _coco_summary(dataset_path=dataset_path, image_paths=image_paths, payload=payload)
    return None


def _coco_summary(
    *,
    dataset_path: Path,
    image_paths: list[Path],
    payload: dict[str, Any],
) -> DatasetAnnotationSummary:
    image_ids_by_file = _coco_image_ids_by_file(payload)
    image_sizes_by_id = _coco_image_sizes_by_id(payload)
    known_image_ids = set(image_ids_by_file.values())
    matched_image_ids: set[int] = set()
    missing_paths: list[str] = []
    for path in image_paths:
        image_ids = _matching_coco_image_ids(
            dataset_path=dataset_path, image_path=path, image_ids_by_file=image_ids_by_file
        )
        if image_ids:
            matched_image_ids.update(image_ids)
        else:
            missing_paths.append(str(path))

    annotated_image_ids: set[int] = set()
    orphan_references: list[str] = []
    invalid_references: list[str] = []
    out_of_bounds_references: list[str] = []
    for item in payload.get("annotations", []):
        if not isinstance(item, dict):
            invalid_references.append("non-object annotation")
            continue
        image_id = item.get("image_id")
        if not isinstance(image_id, int) or image_id not in known_image_ids:
            orphan_references.append(str(image_id))
            continue
        bbox = item.get("bbox")
        if not _valid_coco_bbox(bbox):
            invalid_references.append(str(item.get("id", image_id)))
            continue
        if _coco_bbox_out_of_bounds(bbox, image_sizes_by_id.get(image_id)):
            out_of_bounds_references.append(str(item.get("id", image_id)))
            continue
        if image_id in matched_image_ids:
            annotated_image_ids.add(image_id)

    missing_annotation_ids = matched_image_ids - annotated_image_ids
    missing_paths.extend(
        str(path)
        for path in image_paths
        if _path_has_coco_image_id(
            dataset_path=dataset_path, image_path=path, image_ids=missing_annotation_ids, by_file=image_ids_by_file
        )
    )
    return DatasetAnnotationSummary(
        source_format="coco",
        image_count=len(image_paths),
        annotated_image_count=len(annotated_image_ids),
        missing_annotation_count=len(set(missing_paths)),
        orphan_annotation_count=len(orphan_references),
        invalid_annotation_count=len(invalid_references),
        out_of_bounds_annotation_count=len(out_of_bounds_references),
        category_count=sum(isinstance(category, dict) for category in payload.get("categories", [])),
        sample_missing_paths=sorted(set(missing_paths))[:3],
        sample_orphan_references=orphan_references[:3],
        sample_invalid_references=invalid_references[:3],
        sample_out_of_bounds_references=out_of_bounds_references[:3],
    )


def _inspect_yolo_annotations(*, dataset_path: Path, image_paths: list[Path]) -> DatasetAnnotationSummary | None:
    label_paths = sorted((dataset_path / "labels").rglob("*.txt")) if (dataset_path / "labels").exists() else []
    if not label_paths:
        return None

    annotated_paths: set[Path] = set()
    missing_paths: list[str] = []
    invalid_references: list[str] = []
    category_ids: set[int] = set()
    image_stems = {path.stem for path in image_paths}
    orphan_references = [str(path) for path in label_paths if path.stem not in image_stems]
    for image_path in image_paths:
        label_path = _find_yolo_label_path(dataset_path=dataset_path, image_path=image_path)
        if label_path is None:
            missing_paths.append(str(image_path))
            continue
        valid_lines = 0
        for index, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), start=1):
            parsed_category = _valid_yolo_line(line)
            if parsed_category is None:
                invalid_references.append(f"{label_path}:{index}")
                continue
            valid_lines += 1
            category_ids.add(parsed_category)
        if valid_lines:
            annotated_paths.add(image_path)
        else:
            missing_paths.append(str(image_path))
    return DatasetAnnotationSummary(
        source_format="yolo",
        image_count=len(image_paths),
        annotated_image_count=len(annotated_paths),
        missing_annotation_count=len(missing_paths),
        orphan_annotation_count=len(orphan_references),
        invalid_annotation_count=len(invalid_references),
        category_count=len(category_ids),
        sample_missing_paths=missing_paths[:3],
        sample_orphan_references=orphan_references[:3],
        sample_invalid_references=invalid_references[:3],
    )


def _coco_manifest_paths(dataset_path: Path) -> list[Path]:
    return [
        path.resolve()
        for path in sorted(dataset_path.rglob("*.json"))
        if path.is_file() and path.stat().st_size <= _MAX_COCO_MANIFEST_BYTES
    ]


def _read_coco_manifest(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not {"annotations", "categories", "images"}.issubset(payload):
        return None
    return payload


def _coco_image_ids_by_file(payload: dict[str, Any]) -> dict[str, int]:
    image_ids: dict[str, int] = {}
    for image in payload.get("images", []):
        if not isinstance(image, dict):
            continue
        image_id = image.get("id")
        file_name = image.get("file_name")
        if isinstance(image_id, int) and isinstance(file_name, str) and file_name:
            image_ids[file_name] = image_id
            image_ids[Path(file_name).name] = image_id
            image_ids[Path(file_name).as_posix()] = image_id
    return image_ids


def _coco_image_sizes_by_id(payload: dict[str, Any]) -> dict[int, tuple[float, float]]:
    sizes: dict[int, tuple[float, float]] = {}
    for image in payload.get("images", []):
        if not isinstance(image, dict):
            continue
        image_id = image.get("id")
        if not isinstance(image_id, int):
            continue
        try:
            width = float(image.get("width"))
            height = float(image.get("height"))
        except (TypeError, ValueError):
            continue
        if width > 0 and height > 0:
            sizes[image_id] = (width, height)
    return sizes


def _matching_coco_image_ids(
    *,
    dataset_path: Path,
    image_path: Path,
    image_ids_by_file: dict[str, int],
) -> set[int]:
    return {
        image_ids_by_file[key]
        for key in _image_keys(dataset_path=dataset_path, image_path=image_path) & image_ids_by_file.keys()
    }


def _path_has_coco_image_id(
    *,
    dataset_path: Path,
    image_path: Path,
    image_ids: set[int],
    by_file: dict[str, int],
) -> bool:
    return bool(
        _matching_coco_image_ids(dataset_path=dataset_path, image_path=image_path, image_ids_by_file=by_file)
        & image_ids
    )


def _image_keys(*, dataset_path: Path, image_path: Path) -> set[str]:
    try:
        relative = image_path.relative_to(dataset_path).as_posix()
    except ValueError:
        relative = image_path.name
    return {relative, image_path.name, Path(relative).as_posix()}


def _valid_coco_bbox(value: object) -> bool:
    if not isinstance(value, list) or len(value) < _COCO_BBOX_VALUES:
        return False
    try:
        _x, _y, width, height = [float(item) for item in value[:_COCO_BBOX_VALUES]]
    except (TypeError, ValueError):
        return False
    return width > 0 and height > 0


def _coco_bbox_out_of_bounds(value: object, size: tuple[float, float] | None) -> bool:
    if size is None or not isinstance(value, list) or len(value) < _COCO_BBOX_VALUES:
        return False
    image_width, image_height = size
    try:
        x_min, y_min, width, height = [float(item) for item in value[:_COCO_BBOX_VALUES]]
    except (TypeError, ValueError):
        return False
    return x_min < 0 or y_min < 0 or x_min + width > image_width or y_min + height > image_height


def _find_yolo_label_path(*, dataset_path: Path, image_path: Path) -> Path | None:
    candidates = [dataset_path / "labels" / f"{image_path.stem}.txt", image_path.with_suffix(".txt")]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return None


def _valid_yolo_line(line: str) -> int | None:
    values = line.split()
    if len(values) < _YOLO_BBOX_VALUES:
        return None
    try:
        category = int(float(values[0]))
        coordinates = [float(value) for value in values[1:_YOLO_BBOX_VALUES]]
    except ValueError:
        return None
    if any(value < 0 or value > 1 for value in coordinates):
        return None
    return category
