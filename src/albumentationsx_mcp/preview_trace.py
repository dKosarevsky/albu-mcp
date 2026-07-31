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


def _canonical_json(value: Any) -> str:
    return json.dumps(value, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _normalize_string(value: str) -> str | dict[str, int | str]:
    if len(value) <= MAX_INLINE_STRING_CHARS:
        return value
    return {
        "kind": "string_summary",
        "length": len(value),
        "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
    }


def _bounded_order_text(value: str) -> str:
    if len(value) <= MAX_INLINE_STRING_CHARS:
        return value
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{len(value)}:{digest}"


def _mapping_key_order_token(key: Any, *, depth: int = 0) -> str:
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
        order_value = f"str:{_bounded_order_text(key)}"
    elif isinstance(key, Path):
        order_value = f"path:{_bounded_order_text(str(key))}"
    elif key is None:
        order_value = "none"
    elif isinstance(key, bool):
        order_value = f"bool:{int(key)}"
    elif isinstance(key, int):
        order_value = f"int:{key}"
    elif isinstance(key, float):
        order_value = f"float:{key.hex() if math.isfinite(key) else str(key)}"
    elif isinstance(key, tuple):
        parts = [_mapping_key_order_token(item, depth=depth + 1) for item in key[:MAX_COLLECTION_ITEMS]]
        encoded = _canonical_json(parts)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        order_value = f"tuple:{len(key)}:{digest}"
    else:
        order_value = f"unsupported:{type(key).__qualname__}"
    return order_value


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
            normalized = _structural_summary(value)
        else:
            self._remaining_nodes -= 1
            if depth >= MAX_TRACE_DEPTH:
                normalized = _structural_summary(value)
            elif isinstance(value, np.generic):
                normalized = self.normalize(value.item(), depth=depth)
            elif value is None or isinstance(value, (bool, int)):
                normalized = value
            elif isinstance(value, float):
                normalized = value if math.isfinite(value) else {"kind": "non_finite_float", "value": str(value)}
            elif isinstance(value, str):
                normalized = _normalize_string(value)
            elif isinstance(value, Path):
                normalized = _normalize_string(str(value))
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
        items = sorted(
            value.items(),
            key=lambda pair: (
                _mapping_key_order_token(pair[0]),
                _TraceOrderTokenBuilder().build(pair[1]),
            ),
        )
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

    def _normalize_mapping_key(self, key: Any, *, depth: int) -> str:
        normalized = self.normalize(key, depth=depth)
        text = normalized if isinstance(normalized, str) else _canonical_json(normalized)
        if len(text) <= MAX_INLINE_STRING_CHARS:
            return text
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"string_summary:{len(text)}:{digest}"

    @staticmethod
    def _normalized_mapping_value(values: list[Any]) -> Any:
        if len(values) == 1:
            return values[0]
        return {
            "kind": "mapping_key_collision",
            "item_count": len(values),
            "values": sorted(values, key=_canonical_json),
        }


class _TraceOrderTokenBuilder:
    def __init__(self) -> None:
        self._remaining_nodes = MAX_TRACE_NODES

    def build(self, value: Any) -> str:
        """Build a bounded canonical sort key without spending output-normalization nodes."""
        return _canonical_json(self._normalize(value, depth=0))

    def _normalize(self, value: Any, *, depth: int) -> Any:
        if self._remaining_nodes <= 0 or depth >= MAX_TRACE_DEPTH:
            order_structure = _structural_summary(value)
        else:
            self._remaining_nodes -= 1
            if isinstance(value, np.generic):
                order_structure = self._normalize_numpy_scalar(value)
            elif value is None or isinstance(value, (bool, int)):
                order_structure = {
                    "kind": "scalar",
                    "type": type(value).__qualname__,
                    "value": value,
                }
            elif isinstance(value, float):
                order_structure = {
                    "kind": "float",
                    "type": type(value).__qualname__,
                    "value": value.hex() if math.isfinite(value) else str(value),
                }
            elif isinstance(value, str):
                order_structure = {
                    "kind": "string",
                    "type": type(value).__qualname__,
                    "value": _normalize_string(value),
                }
            elif isinstance(value, Path):
                order_structure = {
                    "kind": "path",
                    "type": type(value).__qualname__,
                    "value": _normalize_string(str(value)),
                }
            elif isinstance(value, np.ndarray):
                order_structure = self._normalize_array(value, depth=depth)
            elif isinstance(value, Mapping):
                order_structure = self._normalize_mapping(value, depth=depth)
            elif isinstance(value, (list, tuple)):
                order_structure = {
                    "kind": "sequence",
                    "type": type(value).__qualname__,
                    "item_count": len(value),
                    "items": [
                        self._normalize(item, depth=depth + 1)
                        for item in value[:MAX_COLLECTION_ITEMS]
                    ],
                }
            else:
                order_structure = {
                    "kind": "unsupported",
                    "type": type(value).__qualname__,
                }
        return order_structure

    @staticmethod
    def _normalize_numpy_scalar(value: np.generic) -> dict[str, Any]:
        scalar = np.asarray(value)
        order_structure: dict[str, Any] = {
            "kind": "numpy_scalar",
            "type": type(value).__qualname__,
            "dtype": str(scalar.dtype),
        }
        if not scalar.dtype.hasobject:
            order_structure["sha256"] = hashlib.sha256(np.ascontiguousarray(scalar).tobytes()).hexdigest()
        return order_structure

    def _normalize_array(self, value: np.ndarray[Any, Any], *, depth: int) -> dict[str, Any]:
        order_structure: dict[str, Any] = {
            "kind": "ndarray",
            "type": type(value).__qualname__,
            "shape": [int(dimension) for dimension in value.shape],
            "dtype": str(value.dtype),
            "element_count": int(value.size),
        }
        if value.dtype.hasobject:
            order_structure["items"] = [
                self._normalize(value.flat[index], depth=depth + 1)
                for index in range(min(int(value.size), MAX_COLLECTION_ITEMS))
            ]
        else:
            contiguous = np.ascontiguousarray(value)
            order_structure["sha256"] = hashlib.sha256(contiguous.tobytes()).hexdigest()
        return order_structure

    def _normalize_mapping(self, value: Mapping[Any, Any], *, depth: int) -> dict[str, Any]:
        items = sorted(
            value.items(),
            key=lambda pair: (
                _mapping_key_order_token(pair[0]),
                self._shallow_order_value(pair[1]),
            ),
        )
        normalized_items = [
            [
                self._normalize(key, depth=depth + 1),
                self._normalize(item, depth=depth + 1),
            ]
            for key, item in items[:MAX_COLLECTION_ITEMS]
        ]
        normalized_items.sort(key=_canonical_json)
        return {
            "kind": "mapping",
            "type": type(value).__qualname__,
            "item_count": len(value),
            "items": normalized_items,
        }

    @staticmethod
    def _shallow_order_value(value: Any) -> str:
        if value is None or isinstance(value, (bool, int)):
            order_value = f"{type(value).__qualname__}:{value}"
        elif isinstance(value, float):
            order_value = f"{type(value).__qualname__}:{value.hex() if math.isfinite(value) else str(value)}"
        elif isinstance(value, str):
            order_value = f"str:{_bounded_order_text(value)}"
        elif isinstance(value, Path):
            order_value = f"path:{_bounded_order_text(str(value))}"
        elif isinstance(value, np.generic):
            scalar = np.asarray(value)
            if scalar.dtype.hasobject:
                order_value = f"numpy:{scalar.dtype}:{type(value).__qualname__}"
            else:
                digest = hashlib.sha256(np.ascontiguousarray(scalar).tobytes()).hexdigest()
                order_value = f"numpy:{scalar.dtype}:{digest}"
        elif isinstance(value, np.ndarray):
            order_value = f"ndarray:{value.dtype}:{tuple(int(item) for item in value.shape)}"
        elif isinstance(value, (Mapping, list, tuple)):
            order_value = f"{type(value).__qualname__}:{len(value)}"
        else:
            order_value = f"unsupported:{type(value).__qualname__}"
        return order_value


def normalize_trace_value(value: Any) -> Any:
    """Normalize one value with a fresh shared depth and node budget."""
    return _TraceNormalizer().normalize(value)
