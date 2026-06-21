"""Read-only dataset structure profiling for onboarding."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import Field

from albumentationsx_mcp.models import StrictModel

_SPLIT_NAMES = frozenset({"test", "train", "val", "valid", "validation"})
_NON_CLASS_DIRS = frozenset({"annotations", "image", "images", "imgs", "label", "labels", "mask", "masks"})
_MAX_ANNOTATION_BYTES = 5_000_000
_MAX_SAMPLE_PATHS = 3
_MIN_CLASS_BUCKETS_FOR_BALANCE = 2
_SPLIT_CLASS_PARTS = 2
_IMBALANCE_RATIO_THRESHOLD = 0.5


class DatasetClassDirectory(StrictModel):
    """Detected class-directory bucket."""

    name: str
    image_count: int
    sample_paths: list[str] = Field(default_factory=list)


class DatasetSplitDirectory(StrictModel):
    """Detected split-directory bucket."""

    name: str
    image_count: int
    sample_paths: list[str] = Field(default_factory=list)


class DatasetAnnotationFormat(StrictModel):
    """Detected annotation format signal."""

    format: Literal["coco", "yolo"]
    file_count: int
    sample_files: list[str] = Field(default_factory=list)
    details: dict[str, int] = Field(default_factory=dict)


class DatasetStructureProfile(StrictModel):
    """Best-effort local dataset structure profile."""

    detected_layouts: list[str] = Field(default_factory=list)
    class_directories: list[DatasetClassDirectory] = Field(default_factory=list)
    splits: list[DatasetSplitDirectory] = Field(default_factory=list)
    annotation_formats: list[DatasetAnnotationFormat] = Field(default_factory=list)
    balance_warnings: list[str] = Field(default_factory=list)
    recipe_hints: list[str] = Field(default_factory=list)


def build_dataset_structure_profile(dataset_path: Path, image_paths: list[Path]) -> DatasetStructureProfile:
    """Detect common local dataset layout signals without mutating or rendering files."""
    class_directories = _detect_class_directories(dataset_path, image_paths)
    splits = _detect_split_directories(dataset_path, image_paths)
    annotation_formats = _detect_annotation_formats(dataset_path)
    detected_layouts = _detected_layouts(class_directories, splits, annotation_formats)
    return DatasetStructureProfile(
        detected_layouts=detected_layouts,
        class_directories=class_directories,
        splits=splits,
        annotation_formats=annotation_formats,
        balance_warnings=_balance_warnings(class_directories),
        recipe_hints=_recipe_hints(detected_layouts),
    )


def _detect_class_directories(dataset_path: Path, image_paths: list[Path]) -> list[DatasetClassDirectory]:
    counts: Counter[str] = Counter()
    samples: dict[str, list[str]] = {}
    for image_path in image_paths:
        class_name = _class_name_for_image(dataset_path, image_path)
        if class_name is None:
            continue
        counts[class_name] += 1
        samples.setdefault(class_name, [])
        if len(samples[class_name]) < _MAX_SAMPLE_PATHS:
            samples[class_name].append(str(image_path))
    return [
        DatasetClassDirectory(name=name, image_count=count, sample_paths=samples.get(name, []))
        for name, count in sorted(counts.items())
    ]


def _detect_split_directories(dataset_path: Path, image_paths: list[Path]) -> list[DatasetSplitDirectory]:
    counts: Counter[str] = Counter()
    samples: dict[str, list[str]] = {}
    for image_path in image_paths:
        parts = _relative_parts(dataset_path, image_path)
        if not parts or parts[0].lower() not in _SPLIT_NAMES:
            continue
        split_name = parts[0]
        counts[split_name] += 1
        samples.setdefault(split_name, [])
        if len(samples[split_name]) < _MAX_SAMPLE_PATHS:
            samples[split_name].append(str(image_path))
    return [
        DatasetSplitDirectory(name=name, image_count=count, sample_paths=samples.get(name, []))
        for name, count in sorted(counts.items())
    ]


def _detect_annotation_formats(dataset_path: Path) -> list[DatasetAnnotationFormat]:
    formats: list[DatasetAnnotationFormat] = []
    yolo_files = sorted(path.resolve() for path in (dataset_path / "labels").rglob("*.txt") if path.is_file())
    if yolo_files:
        formats.append(
            DatasetAnnotationFormat(
                format="yolo",
                file_count=len(yolo_files),
                sample_files=[str(path) for path in yolo_files[:3]],
            )
        )
    coco_manifests = _detect_coco_manifests(dataset_path)
    if coco_manifests:
        formats.append(
            DatasetAnnotationFormat(
                format="coco",
                file_count=len(coco_manifests),
                sample_files=[str(path) for path in coco_manifests[:3]],
                details={"manifest_count": len(coco_manifests)},
            )
        )
    return formats


def _detect_coco_manifests(dataset_path: Path) -> list[Path]:
    manifests: list[Path] = []
    for json_path in sorted(path.resolve() for path in dataset_path.rglob("*.json") if path.is_file()):
        if json_path.stat().st_size > _MAX_ANNOTATION_BYTES:
            continue
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and {"annotations", "categories", "images"}.issubset(payload):
            manifests.append(json_path)
    return manifests


def _class_name_for_image(dataset_path: Path, image_path: Path) -> str | None:
    parts = _relative_parts(dataset_path, image_path)
    if not parts:
        return None
    parent_parts = parts[:-1]
    if not parent_parts:
        return None
    if parent_parts[0].lower() in _SPLIT_NAMES:
        if len(parent_parts) < _SPLIT_CLASS_PARTS:
            return None
        candidate = parent_parts[1]
    else:
        candidate = parent_parts[0]
    if candidate.lower() in _NON_CLASS_DIRS or candidate.startswith("."):
        return None
    return candidate


def _relative_parts(dataset_path: Path, path: Path) -> tuple[str, ...]:
    try:
        return path.relative_to(dataset_path).parts
    except ValueError:
        return ()


def _detected_layouts(
    class_directories: list[DatasetClassDirectory],
    splits: list[DatasetSplitDirectory],
    annotation_formats: list[DatasetAnnotationFormat],
) -> list[str]:
    layouts: list[str] = []
    if class_directories:
        layouts.append("class_directories")
    if splits:
        layouts.append("split_directories")
    annotation_format_names = {annotation.format for annotation in annotation_formats}
    if "yolo" in annotation_format_names:
        layouts.append("yolo_labels")
    if "coco" in annotation_format_names:
        layouts.append("coco_manifest")
    return layouts


def _balance_warnings(class_directories: list[DatasetClassDirectory]) -> list[str]:
    if len(class_directories) < _MIN_CLASS_BUCKETS_FOR_BALANCE:
        return []
    smallest = min(class_directories, key=lambda item: item.image_count)
    largest = max(class_directories, key=lambda item: item.image_count)
    if largest.image_count == 0 or smallest.image_count / largest.image_count > _IMBALANCE_RATIO_THRESHOLD:
        return []
    return [
        "Potential class imbalance: "
        f"{smallest.name} has {smallest.image_count} image(s), "
        f"{largest.name} has {largest.image_count} image(s)."
    ]


def _recipe_hints(detected_layouts: list[str]) -> list[str]:
    hints: list[str] = []
    if "class_directories" in detected_layouts:
        hints.append("Classification class directories detected; start with a low or medium classification recipe.")
    if "split_directories" in detected_layouts:
        hints.append(
            "Split directories detected; sample from training and validation splits before increasing intensity."
        )
    if "yolo_labels" in detected_layouts or "coco_manifest" in detected_layouts:
        hints.append(
            "Detection annotations found; use bbox targets and inspect overlay previews before accepting a pipeline."
        )
    return hints
