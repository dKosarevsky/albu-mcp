"""Bounded, JSON-safe values and contracts for preview variant traces."""

from __future__ import annotations

import hashlib
import json
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
        items = sorted(value.items(), key=lambda pair: self._mapping_key_order_token(pair[0]))
        grouped_values: dict[str, list[Any]] = {}
        for key, item in items[:MAX_COLLECTION_ITEMS]:
            normalized_key = self._normalize_mapping_key(key, depth=depth + 1)
            normalized_value = self.normalize(item, depth=depth + 1)
            grouped_values.setdefault(normalized_key, []).append(normalized_value)
        return {
            key: self._normalized_mapping_value(values)
            for key, values in sorted(grouped_values.items())
        }

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

    def _normalize_mapping_key(self, key: Any, *, depth: int) -> str:
        normalized = self.normalize(key, depth=depth)
        text = normalized if isinstance(normalized, str) else self._canonical_json(normalized)
        if len(text) <= MAX_INLINE_STRING_CHARS:
            return text
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"string_summary:{len(text)}:{digest}"

    @classmethod
    def _mapping_key_order_token(cls, key: Any, *, depth: int = 0) -> str:
        if depth >= MAX_TRACE_DEPTH:
            order_value = f"{type(key).__qualname__}:depth_limit"
        elif isinstance(key, np.generic):
            scalar = np.asarray(key)
            if scalar.dtype.hasobject:
                order_value = f"numpy:{scalar.dtype}:{type(key).__qualname__}"
            else:
                digest = hashlib.sha256(np.ascontiguousarray(scalar).tobytes()).hexdigest()
                order_value = f"numpy:{scalar.dtype}:{digest}"
        elif isinstance(key, str):
            order_value = f"str:{cls._bounded_order_text(key)}"
        elif isinstance(key, Path):
            order_value = f"path:{cls._bounded_order_text(str(key))}"
        elif key is None:
            order_value = "none"
        elif isinstance(key, bool):
            order_value = f"bool:{int(key)}"
        elif isinstance(key, int):
            order_value = f"int:{key}"
        elif isinstance(key, float):
            order_value = f"float:{key.hex() if math.isfinite(key) else str(key)}"
        elif isinstance(key, tuple):
            parts = [cls._mapping_key_order_token(item, depth=depth + 1) for item in key[:MAX_COLLECTION_ITEMS]]
            encoded = cls._canonical_json(parts)
            digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
            order_value = f"tuple:{len(key)}:{digest}"
        else:
            order_value = f"unsupported:{type(key).__qualname__}"
        return order_value

    @staticmethod
    def _bounded_order_text(value: str) -> str:
        if len(value) <= MAX_INLINE_STRING_CHARS:
            return value
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return f"{len(value)}:{digest}"

    @classmethod
    def _normalized_mapping_value(cls, values: list[Any]) -> Any:
        if len(values) == 1:
            return values[0]
        return {
            "kind": "mapping_key_collision",
            "item_count": len(values),
            "values": sorted(values, key=cls._canonical_json),
        }

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(value, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True)

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
