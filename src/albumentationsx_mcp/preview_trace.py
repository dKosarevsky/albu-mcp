"""Bounded, JSON-safe values and contracts for preview variant traces."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import Field

from albumentationsx_mcp.models import StrictModel

MAX_INLINE_ARRAY_ELEMENTS = 64
MAX_COLLECTION_ITEMS = 32
MAX_TRACE_DEPTH = 5
MAX_TRACE_NODES = 128
MAX_INLINE_STRING_CHARS = 256
MAX_APPLIED_TRANSFORMS = 32
MAX_VARIANT_TRACE_JSON_BYTES = 8 * 1024


class AppliedTransformTrace(StrictModel):
    """One applied transform and its bounded sampled parameters."""

    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class PreviewVariantTrace(StrictModel):
    """Applied-transform trace for one rendered preview variant."""

    image_index: int = Field(ge=0)
    variant_index: int = Field(ge=0)
    source_path: str
    artifact_uri: str
    effective_seed: int | None = None
    applied_transforms: list[AppliedTransformTrace] = Field(default_factory=list)
    truncated_transform_count: int = Field(default=0, ge=0)
    parameters_truncated: bool = False


class PreviewVariantTraceResult(StrictModel):
    """Result of querying one preview variant trace."""

    run_id: str
    image_index: int = Field(ge=0)
    variant_index: int = Field(ge=0)
    available: bool
    trace: PreviewVariantTrace | None = None
    message: str


class _TraceNormalizer:
    def __init__(self) -> None:
        self._remaining_nodes = MAX_TRACE_NODES

    def normalize(self, value: Any, *, depth: int = 0) -> Any:
        if self._remaining_nodes <= 0:
            normalized = self._structural_summary(value)
        else:
            self._remaining_nodes -= 1
            if depth >= MAX_TRACE_DEPTH:
                normalized = self._structural_summary(value)
            elif isinstance(value, np.generic):
                normalized = self.normalize(value.item(), depth=depth)
            elif value is None or isinstance(value, (bool, int)):
                normalized = value
            elif isinstance(value, float):
                normalized = value if math.isfinite(value) else {"kind": "non_finite_float", "value": str(value)}
            elif isinstance(value, str):
                normalized = self._normalize_string(value)
            elif isinstance(value, Path):
                normalized = self._normalize_string(str(value))
            elif isinstance(value, np.ndarray):
                normalized = self._normalize_array(value, depth=depth)
            elif isinstance(value, Mapping):
                normalized = self._normalize_mapping(value, depth=depth)
            elif isinstance(value, (list, tuple)):
                normalized = self._normalize_sequence(value, depth=depth)
            else:
                normalized = {"kind": "unsupported", "type": type(value).__qualname__}
        return normalized

    def _normalize_array(self, value: np.ndarray[Any, Any], *, depth: int) -> Any:
        if value.size <= MAX_INLINE_ARRAY_ELEMENTS:
            return self.normalize(value.tolist(), depth=depth + 1)
        contiguous = np.ascontiguousarray(value)
        return {
            "kind": "ndarray_summary",
            "shape": [int(dimension) for dimension in value.shape],
            "dtype": str(value.dtype),
            "element_count": int(value.size),
            "sha256": hashlib.sha256(contiguous.tobytes()).hexdigest(),
        }

    def _normalize_mapping(self, value: Mapping[Any, Any], *, depth: int) -> dict[str, Any]:
        items = [(self._normalize_mapping_key(key), item) for key, item in value.items()]
        items.sort(key=lambda pair: pair[0])
        return {key: self.normalize(item, depth=depth + 1) for key, item in items[:MAX_COLLECTION_ITEMS]}

    def _normalize_sequence(self, value: list[Any] | tuple[Any, ...], *, depth: int) -> Any:
        items = [self.normalize(item, depth=depth + 1) for item in value[:MAX_COLLECTION_ITEMS]]
        if len(value) <= MAX_COLLECTION_ITEMS:
            return items
        return {
            "kind": "sequence_summary",
            "type": type(value).__qualname__,
            "items": items,
            "item_count": len(value),
            "truncated": True,
        }

    @staticmethod
    def _normalize_string(value: str) -> str | dict[str, int | str]:
        if len(value) <= MAX_INLINE_STRING_CHARS:
            return value
        return {
            "kind": "string_summary",
            "length": len(value),
            "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        }

    @classmethod
    def _normalize_mapping_key(cls, key: Any) -> str:
        if isinstance(key, np.generic):
            return cls._normalize_mapping_key(key.item())
        if isinstance(key, str):
            text = key
        elif key is None or isinstance(key, (Path, bool, int, float)):
            text = str(key)
        else:
            text = type(key).__qualname__
        if len(text) <= MAX_INLINE_STRING_CHARS:
            return text
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"string_summary:{len(text)}:{digest}"

    @staticmethod
    def _structural_summary(value: Any) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "kind": "structural_summary",
            "type": type(value).__qualname__,
        }
        if isinstance(value, np.ndarray):
            summary["length"] = int(value.size)
        elif isinstance(value, (str, Mapping, list, tuple)):
            summary["length"] = len(value)
        return summary


def normalize_trace_value(value: Any) -> Any:
    """Normalize one value with a fresh shared depth and node budget."""
    return _TraceNormalizer().normalize(value)
