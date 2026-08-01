"""Bounded, JSON-safe values and contracts for preview variant traces."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from pydantic import ConfigDict, Field, ValidationError

from albumentationsx_mcp.models import StrictModel

if TYPE_CHECKING:
    from albumentationsx_mcp.preview import ArtifactStore

MAX_INLINE_ARRAY_ELEMENTS = 64
MAX_COLLECTION_ITEMS = 32
MAX_TRACE_DEPTH = 5
MAX_TRACE_NODES = 128
MAX_INLINE_STRING_CHARS = 256
MAX_APPLIED_TRANSFORMS = 32
MAX_APPLIED_TRANSFORM_INPUTS = 1024
MAX_VARIANT_TRACE_JSON_BYTES = 8 * 1024
MAX_TRACE_INPUT_TEXT_CHARS = 32 * 1024
MAX_TRACE_STRING_HASH_CHARS = 64 * 1024
# Preview rendering indexes and seeds use practical signed 64-bit bounds.
MAX_TRACE_INDEX = (1 << 63) - 1
MIN_TRACE_SEED = -(1 << 63)
MAX_TRACE_SEED = (1 << 63) - 1
# Bound both hashing work and any contiguous array copy.
MAX_ARRAY_HASH_BYTES = 1024 * 1024
# Stay comfortably below Python's configurable decimal digit limit.
MAX_INLINE_INTEGER_BITS = 2048

_HASHABLE_ARRAY_KINDS = frozenset("biufcmMSU")
_SHORT_JSON_ESCAPE_CODEPOINTS = frozenset({8, 9, 10, 12, 13})
_FIRST_NON_CONTROL_CODEPOINT = 0x20
_MAX_UNESCAPED_ASCII_CODEPOINT = 0x7E
_MAX_BMP_CODEPOINT = 0xFFFF
_MAX_COMPACT_STRING_JSON_BYTES = 128
_COMPACT_STRING_PREFIX = "~compact:"
_LITERAL_STRING_PREFIX = "~literal:"
_APPLIED_TRANSFORM_ENTRY_ITEMS = 2
_APPLIED_TRANSFORMS_COLLECTION_ERROR = "applied_transforms must be an ordered collection of (name, params) tuples"
_APPLIED_TRANSFORMS_ENTRY_ERROR = (
    "applied_transforms entries must be (name, params) tuples with string names and mapping params"
)
_APPLIED_TRANSFORMS_INPUT_LIMIT_ERROR = (
    f"applied_transforms must contain at most {MAX_APPLIED_TRANSFORM_INPUTS} entries"
)
_APPLIED_TRANSFORMS_NORMALIZATION_ERROR = "applied_transforms could not be normalized safely"
_TRANSFORM_NAME_LENGTH_ERROR = f"applied transform names must not exceed {MAX_TRACE_INPUT_TEXT_CHARS} characters"
_SOURCE_PATH_ERROR = "source_path must be a string or pathlib.Path"
_ARTIFACT_URI_ERROR = "artifact_uri must be a string"
_SOURCE_PATH_LENGTH_ERROR = f"source_path must not exceed {MAX_TRACE_INPUT_TEXT_CHARS} characters"
_ARTIFACT_URI_LENGTH_ERROR = f"artifact_uri must not exceed {MAX_TRACE_INPUT_TEXT_CHARS} characters"
_MALFORMED_PREVIEW_TRACE_MANIFEST_ERROR = "Preview trace manifest is malformed"
_MALFORMED_MANIFEST_TRACE_METADATA_ERROR = "Preview manifest trace metadata is malformed"
_MALFORMED_MANIFEST_TRACES_ERROR = "Preview manifest variant_traces contain malformed entries"
_DUPLICATE_MANIFEST_TRACE_ERROR = "Preview manifest contains duplicate image and variant traces"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _final_trace_json_upper_bound() -> int:
    """Return the exact maximum for 32 compact entries and signed 64-bit metadata."""
    widest_compact_text = "x" * (_MAX_COMPACT_STRING_JSON_BYTES - 2)
    payload = {
        "image_index": MAX_TRACE_INDEX,
        "variant_index": MAX_TRACE_INDEX,
        "source_path": widest_compact_text,
        "artifact_uri": widest_compact_text,
        "effective_seed": MIN_TRACE_SEED,
        "applied_transforms": [{"name": widest_compact_text, "params": {}} for _ in range(MAX_APPLIED_TRANSFORMS)],
        "truncated_transform_count": MAX_TRACE_INDEX,
        "parameters_truncated": True,
    }
    return len(json.dumps(payload, allow_nan=False, sort_keys=True).encode("utf-8"))


_MAX_FINAL_VARIANT_TRACE_JSON_BYTES = _final_trace_json_upper_bound()
assert _MAX_FINAL_VARIANT_TRACE_JSON_BYTES <= MAX_VARIANT_TRACE_JSON_BYTES  # noqa: S101


def _normalize_integer(value: int) -> int | dict[str, int | str]:
    if value.bit_length() <= MAX_INLINE_INTEGER_BITS:
        return value
    return {
        "kind": "integer_summary",
        "sign": -1 if value < 0 else 1,
        "bit_length": value.bit_length(),
    }


def _normalize_float(value: float) -> float | dict[str, str]:
    if math.isfinite(value):
        return value
    return {"kind": "non_finite_float", "value": str(value)}


def _normalize_string(value: str) -> str | dict[str, int | str]:
    if len(value) <= MAX_INLINE_STRING_CHARS:
        return value
    if len(value) > MAX_TRACE_STRING_HASH_CHARS:
        return {
            "kind": "string_summary",
            "length": len(value),
            "content_omitted": True,
        }
    return {
        "kind": "string_summary",
        "length": len(value),
        "sha256": hashlib.sha256(value.encode("utf-8", errors="surrogatepass")).hexdigest(),
    }


def _numpy_scalar_summary(value: np.generic) -> dict[str, Any]:
    return {
        "kind": "numpy_scalar_summary",
        "type": type(value).__qualname__,
        "dtype": str(value.dtype),
        "content_omitted": True,
    }


def _unwrap_numpy_scalar(value: np.generic) -> tuple[Any, bool]:
    item = value.item()
    if isinstance(item, np.generic):
        return _numpy_scalar_summary(value), False
    return item, True


def _large_array_summary(value: np.ndarray[Any, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "kind": "ndarray_summary",
        "shape": [int(dimension) for dimension in value.shape],
        "dtype": str(value.dtype),
        "element_count": int(value.size),
    }
    can_hash_contents = (
        not value.dtype.hasobject
        and value.dtype.fields is None
        and value.dtype.subdtype is None
        and value.dtype.kind in _HASHABLE_ARRAY_KINDS
        and value.nbytes <= MAX_ARRAY_HASH_BYTES
    )
    if not can_hash_contents:
        summary["content_omitted"] = True
        return summary

    contiguous = value if value.flags.c_contiguous else np.ascontiguousarray(value)
    summary["sha256"] = hashlib.sha256(contiguous.data.cast("B")).hexdigest()
    return summary


def _mapping_summary(value: Mapping[Any, Any]) -> dict[str, Any]:
    return {
        "kind": "mapping_summary",
        "type": type(value).__qualname__,
        "item_count": len(value),
        "truncated": True,
    }


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

    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class PreviewVariantTrace(StrictModel):
    """Applied-transform trace for one rendered preview variant."""

    model_config = ConfigDict(extra="forbid", strict=True)

    image_index: int = Field(ge=0)
    variant_index: int = Field(ge=0)
    source_path: str
    artifact_uri: str
    effective_seed: int | None = None
    applied_transforms: list[AppliedTransformTrace] = Field(default_factory=list, max_length=MAX_APPLIED_TRANSFORMS)
    truncated_transform_count: int = Field(default=0, ge=0, le=MAX_TRACE_INDEX)
    parameters_truncated: bool = False


class PreviewVariantTraceResult(StrictModel):
    """Result of querying one preview variant trace."""

    model_config = ConfigDict(extra="forbid", strict=True)

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
                item, should_recurse = _unwrap_numpy_scalar(value)
                normalized = self.normalize(item, depth=depth) if should_recurse else item
            elif value is None or isinstance(value, (bool, int)):
                normalized = value if value is None else _normalize_integer(value)
            elif isinstance(value, float):
                normalized = _normalize_float(value)
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
        return _large_array_summary(value)

    def _normalize_mapping(self, value: Mapping[Any, Any], *, depth: int) -> dict[str, Any]:
        if len(value) > MAX_COLLECTION_ITEMS:
            return _mapping_summary(value)

        item_depth = depth + 1
        token_builder = _TraceOrderTokenBuilder()
        tokenized_items: list[tuple[str, str, Any, Any]] = []
        for key, item in value.items():
            key_token, key_complete = token_builder.build(key, depth=item_depth)
            if not key_complete:
                return _mapping_summary(value)
            item_token, item_complete = token_builder.build(item, depth=item_depth)
            if not item_complete:
                return _mapping_summary(value)
            tokenized_items.append((key_token, item_token, key, item))
        tokenized_items.sort(key=lambda tokenized: (tokenized[0], tokenized[1]))

        grouped_values: dict[str, list[Any]] = {}
        for _, _, key, item in tokenized_items:
            normalized_key = self._normalize_mapping_key(key, depth=depth + 1)
            normalized_value = self.normalize(item, depth=depth + 1)
            grouped_values.setdefault(normalized_key, []).append(normalized_value)
        return {key: self._normalized_mapping_value(values) for key, values in sorted(grouped_values.items())}

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
        digest = hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest()
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
        self._complete = True

    def build(self, value: Any, *, depth: int = 0) -> tuple[str, bool]:
        """Build a bounded canonical sort key without spending output-normalization nodes."""
        normalized = self._normalize(value, depth=depth)
        if not self._complete:
            return "", False
        return _canonical_json(normalized), True

    def _consume_node(self) -> bool:
        if self._remaining_nodes <= 0:
            self._complete = False
            return False
        self._remaining_nodes -= 1
        return True

    def _normalize(self, value: Any, *, depth: int) -> Any:
        if not self._consume_node() or depth >= MAX_TRACE_DEPTH:
            order_structure = _structural_summary(value)
        elif isinstance(value, np.generic):
            order_structure = self._normalize_numpy_scalar(value, depth=depth)
        elif value is None or isinstance(value, bool):
            order_structure = {
                "kind": "scalar",
                "type": type(value).__qualname__,
                "value": value,
            }
        elif isinstance(value, int):
            order_structure = {
                "kind": "scalar",
                "type": type(value).__qualname__,
                "value": _normalize_integer(value),
            }
        elif isinstance(value, float):
            normalized_float = _normalize_float(value)
            order_structure = {
                "kind": "float",
                "type": type(value).__qualname__,
                "value": value.hex() if isinstance(normalized_float, float) else normalized_float,
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
            order_structure = self._normalize_sequence(value, depth=depth)
        else:
            order_structure = {
                "kind": "unsupported",
                "type": type(value).__qualname__,
            }
        return order_structure

    def _normalize_numpy_scalar(self, value: np.generic, *, depth: int) -> dict[str, Any]:
        item, should_recurse = _unwrap_numpy_scalar(value)
        order_structure: dict[str, Any] = {
            "kind": "numpy_scalar",
            "type": type(value).__qualname__,
            "dtype": str(value.dtype),
            "value": self._normalize(item, depth=depth) if should_recurse else item,
        }
        return order_structure

    def _normalize_array(self, value: np.ndarray[Any, Any], *, depth: int) -> dict[str, Any]:
        order_structure: dict[str, Any] = {
            "kind": "ndarray",
            "type": type(value).__qualname__,
            "shape": [int(dimension) for dimension in value.shape],
            "dtype": str(value.dtype),
            "element_count": int(value.size),
        }
        if value.size <= MAX_INLINE_ARRAY_ELEMENTS:
            order_structure["value"] = self._normalize(value.tolist(), depth=depth + 1)
        else:
            order_structure["value"] = _large_array_summary(value)
        return order_structure

    def _normalize_sequence(self, value: list[Any] | tuple[Any, ...], *, depth: int) -> dict[str, Any]:
        items: list[Any] = []
        for item in value[:MAX_COLLECTION_ITEMS]:
            items.append(self._normalize(item, depth=depth + 1))
            if not self._complete:
                break
        return {
            "kind": "sequence",
            "type": type(value).__qualname__,
            "item_count": len(value),
            "items": items,
        }

    def _normalize_mapping(self, value: Mapping[Any, Any], *, depth: int) -> dict[str, Any]:
        if len(value) > MAX_COLLECTION_ITEMS:
            return _mapping_summary(value)

        normalized_items: list[list[Any]] = []
        for key, item in value.items():
            normalized_key = self._normalize(key, depth=depth + 1)
            if not self._complete:
                return _mapping_summary(value)
            normalized_item = self._normalize(item, depth=depth + 1)
            if not self._complete:
                return _mapping_summary(value)
            normalized_items.append([normalized_key, normalized_item])
        normalized_items.sort(key=_canonical_json)
        return {
            "kind": "mapping",
            "type": type(value).__qualname__,
            "item_count": len(value),
            "items": normalized_items,
        }


def normalize_trace_value(value: Any) -> Any:
    """Normalize one value with a fresh shared depth and node budget."""
    return _TraceNormalizer().normalize(value)


def build_variant_trace(  # noqa: PLR0913
    *,
    image_index: int,
    variant_index: int,
    source_path: str | Path,
    artifact_uri: str,
    effective_seed: int | None,
    applied_transforms: Any = None,
) -> PreviewVariantTrace:
    """Build one deterministic, size-bounded applied-transform trace."""
    _validate_trace_scalar_metadata(
        image_index=image_index,
        variant_index=variant_index,
        effective_seed=effective_seed,
    )
    source_path_text, artifact_uri_text = _validate_trace_string_metadata(
        source_path=source_path,
        artifact_uri=artifact_uri,
    )
    validated = _validate_applied_transforms(applied_transforms)
    retained = validated[:MAX_APPLIED_TRANSFORMS]
    truncated_transform_count = len(validated) - len(retained)
    try:
        normalized = [
            (
                name,
                normalize_trace_value(params),
                len(params),
            )
            for name, params in retained
        ]
    except (OSError, OverflowError, RuntimeError, TypeError, ValueError):
        raise ValueError(_APPLIED_TRANSFORMS_NORMALIZATION_ERROR) from None

    if _raw_trace_text_exceeds_json_budget(
        image_index=image_index,
        variant_index=variant_index,
        source_path=source_path_text,
        artifact_uri=artifact_uri_text,
        effective_seed=effective_seed,
        transform_names=[name for name, _, _ in normalized],
        truncated_transform_count=truncated_transform_count,
    ):
        return _build_precompacted_variant_trace(
            image_index=image_index,
            variant_index=variant_index,
            source_path=source_path_text,
            artifact_uri=artifact_uri_text,
            effective_seed=effective_seed,
            normalized=normalized,
            truncated_transform_count=truncated_transform_count,
        )

    transforms = [AppliedTransformTrace(name=name, params=params) for name, params, _ in normalized]
    trace = PreviewVariantTrace(
        image_index=image_index,
        variant_index=variant_index,
        source_path=source_path_text,
        artifact_uri=artifact_uri_text,
        effective_seed=effective_seed,
        applied_transforms=transforms,
        truncated_transform_count=truncated_transform_count,
    )
    if _trace_fits_json_budget(trace):
        return trace

    summarized_transforms = [
        AppliedTransformTrace(
            name=name,
            params=_parameter_summary(params, item_count=item_count),
        )
        for name, params, item_count in normalized
    ]
    summarized_trace = trace.model_copy(
        update={
            "applied_transforms": summarized_transforms,
            "parameters_truncated": True,
        },
    )
    if _trace_fits_json_budget(summarized_trace):
        return summarized_trace

    compacted_transforms = [
        transform.model_copy(
            update={"name": _compact_trace_text(transform.name, field_type="transform_name")},
        )
        for transform in summarized_transforms
    ]
    compacted_trace = summarized_trace.model_copy(
        update={
            "source_path": _compact_trace_text(summarized_trace.source_path, field_type="source_path"),
            "artifact_uri": _compact_trace_text(summarized_trace.artifact_uri, field_type="artifact_uri"),
            "applied_transforms": compacted_transforms,
        },
    )
    if _trace_fits_json_budget(compacted_trace):
        return compacted_trace

    final_trace = compacted_trace.model_copy(
        update={
            "applied_transforms": [transform.model_copy(update={"params": {}}) for transform in compacted_transforms],
        },
    )
    if _trace_fits_json_budget(final_trace):
        return final_trace
    msg = "Preview variant trace exceeded its bounded fallback invariant"
    raise ValueError(msg)


def _build_precompacted_variant_trace(  # noqa: PLR0913
    *,
    image_index: int,
    variant_index: int,
    source_path: str,
    artifact_uri: str,
    effective_seed: int | None,
    normalized: list[tuple[str, dict[str, Any], int]],
    truncated_transform_count: int,
) -> PreviewVariantTrace:
    compacted_transforms = [
        AppliedTransformTrace(
            name=_compact_trace_text(name, field_type="transform_name"),
            params=_parameter_summary(params, item_count=item_count),
        )
        for name, params, item_count in normalized
    ]
    compacted_trace = PreviewVariantTrace(
        image_index=image_index,
        variant_index=variant_index,
        source_path=_compact_trace_text(source_path, field_type="source_path"),
        artifact_uri=_compact_trace_text(artifact_uri, field_type="artifact_uri"),
        effective_seed=effective_seed,
        applied_transforms=compacted_transforms,
        truncated_transform_count=truncated_transform_count,
        parameters_truncated=True,
    )
    if _trace_fits_json_budget(compacted_trace):
        return compacted_trace

    final_trace = compacted_trace.model_copy(
        update={
            "applied_transforms": [transform.model_copy(update={"params": {}}) for transform in compacted_transforms],
        },
    )
    if _trace_fits_json_budget(final_trace):
        return final_trace
    msg = "Preview variant trace exceeded its bounded fallback invariant"
    raise ValueError(msg)


def get_preview_variant_trace(
    artifact_store: ArtifactStore,
    run_id: str,
    *,
    image_index: int,
    variant_index: int,
) -> PreviewVariantTraceResult:
    """Read and validate one variant trace from a controlled preview manifest."""
    _validate_trace_index_type("image_index", image_index)
    _validate_trace_index_type("variant_index", variant_index)
    if image_index < 0 or variant_index < 0:
        msg = "image_index and variant_index must be non-negative"
        raise ValueError(msg)
    _validate_trace_index("image_index", image_index)
    _validate_trace_index("variant_index", variant_index)

    try:
        manifest = artifact_store.read_manifest(run_id)
    except TypeError:
        raise ValueError(_MALFORMED_PREVIEW_TRACE_MANIFEST_ERROR) from None
    summary = manifest.get("summary")
    if not isinstance(summary, dict):
        raise ValueError(  # noqa: TRY004 - lookup exposes one stable malformed-manifest error type.
            _MALFORMED_MANIFEST_TRACE_METADATA_ERROR,
        ) from None
    has_variant_traces = "variant_traces" in manifest
    has_variant_trace_count = "variant_trace_count" in summary
    if not has_variant_traces and not has_variant_trace_count:
        return PreviewVariantTraceResult(
            run_id=run_id,
            image_index=image_index,
            variant_index=variant_index,
            available=False,
            message="Variant traces are unavailable for this legacy preview run.",
        )
    if has_variant_traces != has_variant_trace_count:
        raise ValueError(_MALFORMED_MANIFEST_TRACE_METADATA_ERROR)

    raw_trace_count = summary["variant_trace_count"]
    if type(raw_trace_count) is not int or raw_trace_count < 0 or raw_trace_count > MAX_TRACE_INDEX:
        raise ValueError(_MALFORMED_MANIFEST_TRACE_METADATA_ERROR) from None

    raw_traces = manifest["variant_traces"]
    if not isinstance(raw_traces, list):
        msg = "Preview manifest variant_traces must be a list"
        raise ValueError(msg)  # noqa: TRY004 - public API requires one stable validation error type.
    if raw_trace_count != len(raw_traces):
        raise ValueError(_MALFORMED_MANIFEST_TRACE_METADATA_ERROR)
    traces = _validate_variant_traces(raw_traces)
    _validate_unique_variant_trace_pairs(traces)
    matches = [item for item in traces if item.image_index == image_index and item.variant_index == variant_index]
    if not matches:
        msg = f"Preview variant trace is unavailable for image {image_index}, variant {variant_index}"
        raise ValueError(msg)
    trace = matches[0]
    return PreviewVariantTraceResult(
        run_id=run_id,
        image_index=image_index,
        variant_index=variant_index,
        available=True,
        trace=trace,
        message="Applied transform trace is available.",
    )


def _validate_applied_transforms(value: Any) -> list[tuple[str, dict[Any, Any]]]:
    if value is None:
        return []
    if type(value) not in (list, tuple):
        raise ValueError(_APPLIED_TRANSFORMS_COLLECTION_ERROR) from None
    if len(value) > MAX_APPLIED_TRANSFORM_INPUTS:
        raise ValueError(_APPLIED_TRANSFORMS_INPUT_LIMIT_ERROR) from None

    validated: list[tuple[str, dict[Any, Any]]] = []
    for entry in value:
        if type(entry) is not tuple or len(entry) != _APPLIED_TRANSFORM_ENTRY_ITEMS:
            raise ValueError(_APPLIED_TRANSFORMS_ENTRY_ERROR) from None
        name, params = entry
        if type(name) is not str or type(params) is not dict:
            raise ValueError(_APPLIED_TRANSFORMS_ENTRY_ERROR) from None
        if len(name) > MAX_TRACE_INPUT_TEXT_CHARS:
            raise ValueError(_TRANSFORM_NAME_LENGTH_ERROR) from None
        validated.append((name, params))
    return validated


def _parameter_summary(params: dict[str, Any], *, item_count: int) -> dict[str, Any]:
    encoded = _canonical_json(params).encode("utf-8")
    return {
        "kind": "parameter_summary",
        "item_count": item_count,
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _compact_trace_text(value: str, *, field_type: str) -> str:
    if _json_text_size(value) > _MAX_COMPACT_STRING_JSON_BYTES:
        return _compact_trace_text_digest(value, field_type=field_type)
    if not value.startswith((_COMPACT_STRING_PREFIX, _LITERAL_STRING_PREFIX)):
        return value

    escaped = f"{_LITERAL_STRING_PREFIX}{value}"
    if _json_text_size(escaped) <= _MAX_COMPACT_STRING_JSON_BYTES:
        return escaped
    return _compact_trace_text_digest(value, field_type=field_type)


def _compact_trace_text_digest(value: str, *, field_type: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="surrogatepass")).hexdigest()
    return f"{_COMPACT_STRING_PREFIX}{field_type}:{len(value):016x}:{digest}"


def _json_text_size(value: str) -> int:
    """Return the exact UTF-8 byte size of json.dumps(value, ensure_ascii=True)."""
    size = 2
    for character in value:
        codepoint = ord(character)
        if character in {'"', "\\"} or codepoint in _SHORT_JSON_ESCAPE_CODEPOINTS:
            size += 2
        elif codepoint < _FIRST_NON_CONTROL_CODEPOINT:
            size += 6
        elif codepoint <= _MAX_UNESCAPED_ASCII_CODEPOINT:
            size += 1
        elif codepoint <= _MAX_BMP_CODEPOINT:
            size += 6
        else:
            size += 12
    return size


def _raw_trace_text_exceeds_json_budget(  # noqa: PLR0913
    *,
    image_index: int,
    variant_index: int,
    source_path: str,
    artifact_uri: str,
    effective_seed: int | None,
    transform_names: list[str],
    truncated_transform_count: int,
) -> bool:
    minimum_payload = {
        "image_index": image_index,
        "variant_index": variant_index,
        "source_path": "",
        "artifact_uri": "",
        "effective_seed": effective_seed,
        "applied_transforms": [{"name": "", "params": {}} for _ in transform_names],
        "truncated_transform_count": truncated_transform_count,
        "parameters_truncated": False,
    }
    minimum_size = len(json.dumps(minimum_payload, allow_nan=False, sort_keys=True).encode("utf-8"))
    text_size_delta = _json_text_size(source_path) + _json_text_size(artifact_uri) - 4
    text_size_delta += sum(_json_text_size(name) - 2 for name in transform_names)
    return minimum_size + text_size_delta > MAX_VARIANT_TRACE_JSON_BYTES


def _trace_fits_json_budget(trace: PreviewVariantTrace) -> bool:
    try:
        encoded = json.dumps(trace.model_dump(mode="json"), allow_nan=False, sort_keys=True).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        return False
    return len(encoded) <= MAX_VARIANT_TRACE_JSON_BYTES


def _validate_variant_traces(raw_traces: list[Any]) -> list[PreviewVariantTrace]:
    traces: list[PreviewVariantTrace] = []
    for raw_trace in raw_traces:
        try:
            trace = PreviewVariantTrace.model_validate(raw_trace)
        except (TypeError, ValidationError, ValueError, OverflowError):
            raise ValueError(_MALFORMED_MANIFEST_TRACES_ERROR) from None
        try:
            _validate_trace_scalar_metadata(
                image_index=trace.image_index,
                variant_index=trace.variant_index,
                effective_seed=trace.effective_seed,
            )
        except ValueError:
            raise ValueError(_MALFORMED_MANIFEST_TRACES_ERROR) from None
        if not _trace_fits_json_budget(trace):
            raise ValueError(_MALFORMED_MANIFEST_TRACES_ERROR)
        traces.append(trace)
    return traces


def _validate_unique_variant_trace_pairs(traces: list[PreviewVariantTrace]) -> None:
    seen: set[tuple[int, int]] = set()
    for trace in traces:
        pair = (trace.image_index, trace.variant_index)
        if pair in seen:
            raise ValueError(_DUPLICATE_MANIFEST_TRACE_ERROR)
        seen.add(pair)


def _validate_trace_scalar_metadata(
    *,
    image_index: int,
    variant_index: int,
    effective_seed: int | None,
) -> None:
    _validate_trace_index("image_index", image_index)
    _validate_trace_index("variant_index", variant_index)
    validate_effective_seed(effective_seed)


def validate_effective_seed(effective_seed: Any) -> None:
    """Validate one effective preview seed against the trace serialization contract."""
    if effective_seed is not None and (
        isinstance(effective_seed, bool)
        or not isinstance(effective_seed, int)
        or effective_seed < MIN_TRACE_SEED
        or effective_seed > MAX_TRACE_SEED
    ):
        msg = f"effective_seed must be None or an integer between {MIN_TRACE_SEED} and {MAX_TRACE_SEED}"
        raise ValueError(msg)


def _validate_trace_string_metadata(*, source_path: Any, artifact_uri: Any) -> tuple[str, str]:
    if not isinstance(source_path, (str, Path)):
        raise ValueError(_SOURCE_PATH_ERROR)  # noqa: TRY004 - public API uses stable ValueError validation.
    if not isinstance(artifact_uri, str):
        raise ValueError(_ARTIFACT_URI_ERROR)  # noqa: TRY004 - public API uses stable ValueError validation.
    try:
        source_path_text = str(source_path)
    except (OSError, RuntimeError, TypeError, ValueError):
        raise ValueError(_SOURCE_PATH_ERROR) from None
    if len(source_path_text) > MAX_TRACE_INPUT_TEXT_CHARS:
        raise ValueError(_SOURCE_PATH_LENGTH_ERROR) from None
    if len(artifact_uri) > MAX_TRACE_INPUT_TEXT_CHARS:
        raise ValueError(_ARTIFACT_URI_LENGTH_ERROR) from None
    return source_path_text, artifact_uri


def _validate_trace_index(field: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > MAX_TRACE_INDEX:
        msg = f"{field} must be an integer between 0 and {MAX_TRACE_INDEX}"
        raise ValueError(msg)


def _validate_trace_index_type(field: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field} must be an integer between 0 and {MAX_TRACE_INDEX}"
        raise ValueError(msg)  # noqa: TRY004 - public API requires one stable validation error type.
