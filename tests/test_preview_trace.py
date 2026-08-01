import hashlib
import json
import math
from collections.abc import ItemsView, Iterator, Mapping
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from albumentationsx_mcp import preview_trace
from albumentationsx_mcp.preview_trace import (
    MAX_APPLIED_TRANSFORMS,
    MAX_COLLECTION_ITEMS,
    MAX_INLINE_ARRAY_ELEMENTS,
    MAX_INLINE_STRING_CHARS,
    MAX_TRACE_DEPTH,
    MAX_TRACE_NODES,
    MAX_VARIANT_TRACE_JSON_BYTES,
    AppliedTransformTrace,
    PreviewVariantTrace,
    PreviewVariantTraceResult,
    normalize_trace_value,
)


class UnsupportedValue:
    def __repr__(self) -> str:
        message = "repr must not be called"
        raise AssertionError(message)


class CountingMapping(Mapping[str, object]):
    def __init__(self, values: dict[str, object]) -> None:
        self._values = values
        self.items_call_count = 0

    def __getitem__(self, key: str) -> object:
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def items(self) -> ItemsView[str, object]:
        self.items_call_count += 1
        return self._values.items()


def test_trace_limits_are_stable() -> None:
    assert MAX_INLINE_ARRAY_ELEMENTS == 64
    assert MAX_COLLECTION_ITEMS == 32
    assert MAX_TRACE_DEPTH == 5
    assert MAX_TRACE_NODES == 128
    assert MAX_INLINE_STRING_CHARS == 256
    assert MAX_APPLIED_TRANSFORMS == 32
    assert MAX_VARIANT_TRACE_JSON_BYTES == 8 * 1024
    assert preview_trace.MAX_ARRAY_HASH_BYTES == 1024 * 1024
    assert preview_trace.MAX_INLINE_INTEGER_BITS == 4096


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (True, True),
        (3, 3),
        (1.25, 1.25),
        ("sample", "sample"),
        (Path("sample.png"), "sample.png"),
        (np.int64(7), 7),
        (np.float32(1.5), 1.5),
        (np.array([[1, 2]], dtype=np.int16), [[1, 2]]),
        (("first", 2), ["first", 2]),
    ],
)
def test_normalize_trace_value_preserves_small_json_values(value: object, expected: object) -> None:
    assert normalize_trace_value(value) == expected


def test_normalize_trace_value_summarizes_large_array_from_contiguous_bytes() -> None:
    value = np.arange(70, dtype=np.float32).reshape((7, 10)).T

    result = normalize_trace_value(value)

    assert result == {
        "kind": "ndarray_summary",
        "shape": [10, 7],
        "dtype": "float32",
        "element_count": 70,
        "sha256": hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest(),
    }


def test_normalize_trace_value_omits_large_object_array_contents() -> None:
    first = np.array([{"value": index} for index in range(MAX_INLINE_ARRAY_ELEMENTS + 1)], dtype=object)
    second = np.array([{"value": index} for index in range(MAX_INLINE_ARRAY_ELEMENTS + 1)], dtype=object)
    expected = {
        "kind": "ndarray_summary",
        "shape": [MAX_INLINE_ARRAY_ELEMENTS + 1],
        "dtype": "object",
        "element_count": MAX_INLINE_ARRAY_ELEMENTS + 1,
        "content_omitted": True,
    }

    assert normalize_trace_value(first) == expected
    assert normalize_trace_value(second) == expected
    json.dumps(expected, allow_nan=False, sort_keys=True)


def test_normalize_trace_value_omits_large_padded_structured_array_contents() -> None:
    dtype = np.dtype({"names": ["value"], "formats": ["u1"], "offsets": [0], "itemsize": 8})
    values = [(index,) for index in range(MAX_INLINE_ARRAY_ELEMENTS + 1)]
    first = np.array(values, dtype=dtype)
    second = np.array(values, dtype=dtype)
    expected = {
        "kind": "ndarray_summary",
        "shape": [MAX_INLINE_ARRAY_ELEMENTS + 1],
        "dtype": str(dtype),
        "element_count": MAX_INLINE_ARRAY_ELEMENTS + 1,
        "content_omitted": True,
    }

    assert normalize_trace_value(first) == expected
    assert normalize_trace_value(second) == expected
    json.dumps(expected, allow_nan=False, sort_keys=True)


def test_normalize_trace_value_omits_oversized_numeric_array_contents() -> None:
    element_count = preview_trace.MAX_ARRAY_HASH_BYTES // np.dtype(np.float64).itemsize + 1
    value = np.zeros(element_count, dtype=np.float64)

    assert normalize_trace_value(value) == {
        "kind": "ndarray_summary",
        "shape": [element_count],
        "dtype": "float64",
        "element_count": element_count,
        "content_omitted": True,
    }


def test_normalize_trace_value_summarizes_long_string() -> None:
    value = "x" * (MAX_INLINE_STRING_CHARS + 1)

    assert normalize_trace_value(value) == {
        "kind": "string_summary",
        "length": len(value),
        "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
    }


def test_normalize_trace_value_applies_string_bound_to_paths() -> None:
    value = Path("x" * (MAX_INLINE_STRING_CHARS + 1))

    result = normalize_trace_value(value)

    assert result["kind"] == "string_summary"
    assert result["length"] == MAX_INLINE_STRING_CHARS + 1


def test_normalize_trace_value_hashes_surrogate_strings_and_paths_safely() -> None:
    text = "x" * MAX_INLINE_STRING_CHARS + "\udcff"
    expected = {
        "kind": "string_summary",
        "length": len(text),
        "sha256": hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest(),
    }

    assert normalize_trace_value(text) == expected
    assert normalize_trace_value(Path(text)) == expected
    json.dumps(expected, allow_nan=False, sort_keys=True)


@pytest.mark.parametrize(("value", "type_name"), [(list(range(33)), "list"), (tuple(range(33)), "tuple")])
def test_normalize_trace_value_caps_long_sequences(value: object, type_name: str) -> None:
    result = normalize_trace_value(value)

    assert result == {
        "kind": "sequence_summary",
        "type": type_name,
        "items": list(range(MAX_COLLECTION_ITEMS)),
        "item_count": MAX_COLLECTION_ITEMS + 1,
        "truncated": True,
    }


def test_normalize_trace_value_summarizes_oversized_mapping() -> None:
    items = [(f"key-{index:02d}", index) for index in range(MAX_COLLECTION_ITEMS + 5)]
    forward = normalize_trace_value(dict(items))
    reverse = normalize_trace_value(dict(reversed(items)))

    expected = {
        "kind": "mapping_summary",
        "type": "dict",
        "item_count": len(items),
        "truncated": True,
    }
    assert forward == expected
    assert reverse == expected
    json.dumps(expected, allow_nan=False, sort_keys=True)


def test_normalize_trace_value_does_not_iterate_oversized_mapping_values() -> None:
    value = CountingMapping(
        {
            f"key-{index:02d}": {"nested": [index] * MAX_COLLECTION_ITEMS}
            for index in range(MAX_COLLECTION_ITEMS + 1)
        }
    )

    assert normalize_trace_value({"oversized": value}) == {
        "oversized": {
            "kind": "mapping_summary",
            "type": "CountingMapping",
            "item_count": MAX_COLLECTION_ITEMS + 1,
            "truncated": True,
        }
    }
    assert value.items_call_count == 0


def test_normalize_trace_value_bounds_mapping_keys() -> None:
    key = "k" * (MAX_INLINE_STRING_CHARS + 1)

    result = normalize_trace_value({key: 1})

    normalized_key = next(iter(result))
    assert len(normalized_key) <= MAX_INLINE_STRING_CHARS
    assert hashlib.sha256(key.encode("utf-8")).hexdigest() in normalized_key


def test_normalize_trace_value_preserves_colliding_mapping_values_deterministically() -> None:
    entries = [(1, {"source": "numeric"}), ("1", {"source": "string"})]

    forward = normalize_trace_value(dict(entries))
    reverse = normalize_trace_value(dict(reversed(entries)))

    expected = {
        "1": {
            "kind": "mapping_key_collision",
            "item_count": 2,
            "values": [{"source": "numeric"}, {"source": "string"}],
        }
    }
    assert forward == expected
    assert reverse == expected


def test_normalize_trace_value_orders_equal_key_tokens_deterministically() -> None:
    entries = [(bytes([index]), index) for index in range(MAX_COLLECTION_ITEMS)]

    forward = normalize_trace_value(dict(entries))
    reverse = normalize_trace_value(dict(reversed(entries)))

    assert forward == reverse
    collision = next(iter(forward.values()))
    assert collision["kind"] == "mapping_key_collision"
    assert collision["item_count"] == MAX_COLLECTION_ITEMS
    assert len(collision["values"]) == MAX_COLLECTION_ITEMS
    json.dumps(forward, allow_nan=False, sort_keys=True)


def test_normalize_trace_value_caps_object_numpy_scalar_values_deterministically() -> None:
    dtype = np.dtype([("label", object), ("index", np.int64)])
    entries = [
        (bytes([index]), np.array((f"value-{index:02d}", index), dtype=dtype)[()])
        for index in range(MAX_COLLECTION_ITEMS)
    ]

    forward = normalize_trace_value(dict(entries))
    reverse = normalize_trace_value(dict(reversed(entries)))

    assert forward == reverse
    json.dumps(forward, allow_nan=False, sort_keys=True)


def test_normalize_trace_value_orders_object_numpy_scalars_at_depth_boundary() -> None:
    dtype = np.dtype([("payload", object)])

    def nested_scalar(index: int) -> list[object]:
        value = np.array((list(range(index)),), dtype=dtype)[()]
        return [[[value]]]

    entries = [
        (bytes([index]), nested_scalar(index))
        for index in range(MAX_COLLECTION_ITEMS)
    ]

    forward = normalize_trace_value(dict(entries))
    reverse = normalize_trace_value(dict(reversed(entries)))

    assert forward == reverse
    json.dumps(forward, allow_nan=False, sort_keys=True)


def test_normalize_trace_value_orders_inline_object_arrays_beyond_collection_prefix() -> None:
    prefix = list(range(MAX_COLLECTION_ITEMS))
    entries = [
        (
            bytes([index]),
            np.array([*prefix, f"tail-{index:02d}", "shared-tail"], dtype=object).reshape((2, 17)),
        )
        for index in range(MAX_COLLECTION_ITEMS)
    ]

    forward = normalize_trace_value(dict(entries))
    reverse = normalize_trace_value(dict(reversed(entries)))

    assert forward == reverse
    json.dumps(forward, allow_nan=False, sort_keys=True)


def test_normalize_trace_value_orders_nested_mapping_values_canonically() -> None:
    def nested_value(unique_value: int) -> dict[bytes, dict[str, object]]:
        common: list[tuple[bytes, dict[str, object]]] = [
            (bytes([index]), {"payload": f"common-{index:02d}"})
            for index in range(2)
        ]
        return dict([*common, (bytes([2]), {"payload": unique_value})])

    entries = [
        (bytes([index]), nested_value(index))
        for index in range(MAX_COLLECTION_ITEMS)
    ]

    forward = normalize_trace_value(dict(entries))
    reverse = normalize_trace_value(dict(reversed(entries)))

    assert forward == reverse
    json.dumps(forward, allow_nan=False, sort_keys=True)


def test_normalize_trace_value_bounds_recursive_mapping_order_tokens() -> None:
    recursive: dict[str, object] = {}
    recursive["self"] = recursive

    result = normalize_trace_value({b"recursive": recursive})
    encoded = json.dumps(result, allow_nan=False, sort_keys=True)

    assert "structural_summary" in encoded


def test_normalize_trace_value_bounds_numpy_scalar_without_starving_sibling() -> None:
    scalar = np.longdouble("1.25")

    result = normalize_trace_value({"numpy": scalar, "sibling": "preserved"})

    assert result == {
        "numpy": {
            "kind": "numpy_scalar_summary",
            "type": type(scalar).__qualname__,
            "dtype": str(scalar.dtype),
            "content_omitted": True,
        },
        "sibling": "preserved",
    }
    json.dumps(result, allow_nan=False)


def test_normalize_trace_value_summarizes_huge_integer_for_strict_json() -> None:
    value = 10**5000

    result = normalize_trace_value({"value": value})

    assert result == {
        "value": {
            "kind": "integer_summary",
            "sign": 1,
            "bit_length": value.bit_length(),
        }
    }
    json.dumps(result, allow_nan=False, sort_keys=True)


def test_normalize_trace_value_summarizes_excessive_nesting() -> None:
    value: object = 0
    for _ in range(MAX_TRACE_DEPTH + 1):
        value = [value]

    result = normalize_trace_value(value)
    for _ in range(MAX_TRACE_DEPTH):
        result = result[0]

    assert result == {"kind": "structural_summary", "type": "list", "length": 1}


def test_normalize_trace_value_uses_one_shared_node_budget() -> None:
    value = [list(range(MAX_COLLECTION_ITEMS)) for _ in range(4)]

    result = normalize_trace_value(value)

    assert result[3][27] == {"kind": "structural_summary", "type": "int"}
    assert normalize_trace_value(27) == 27
    assert MAX_TRACE_NODES == 128


@pytest.mark.parametrize(
    ("value", "text"),
    [(math.inf, "inf"), (-math.inf, "-inf"), (math.nan, "nan")],
)
def test_normalize_trace_value_represents_non_finite_float(value: float, text: str) -> None:
    assert normalize_trace_value(value) == {"kind": "non_finite_float", "value": text}


def test_normalize_trace_value_does_not_repr_unsupported_objects() -> None:
    assert normalize_trace_value(UnsupportedValue()) == {
        "kind": "unsupported",
        "type": "UnsupportedValue",
    }


def test_normalized_trace_value_is_strict_json_serializable() -> None:
    value = {
        "array": np.arange(MAX_INLINE_ARRAY_ELEMENTS + 1),
        "nested": [{"value": np.float32(2.5)}],
        "non_finite": math.nan,
        "path": Path("sample.png"),
        "unsupported": UnsupportedValue(),
    }

    encoded = json.dumps(normalize_trace_value(value), allow_nan=False, sort_keys=True)

    assert json.loads(encoded)["non_finite"] == {"kind": "non_finite_float", "value": "nan"}


def test_trace_models_use_independent_default_collections() -> None:
    first_transform = AppliedTransformTrace(name="Blur")
    second_transform = AppliedTransformTrace(name="Noise")
    first_transform.params["limit"] = 3

    first_trace = PreviewVariantTrace(
        image_index=0,
        variant_index=0,
        source_path="source.png",
        artifact_uri="albumentationsx://runs/run-1/images/0/0",
    )
    second_trace = PreviewVariantTrace(
        image_index=0,
        variant_index=1,
        source_path="source.png",
        artifact_uri="albumentationsx://runs/run-1/images/0/1",
    )
    first_trace.applied_transforms.append(first_transform)

    assert second_transform.params == {}
    assert second_trace.applied_transforms == []
    assert first_trace.truncated_transform_count == 0
    assert first_trace.parameters_truncated is False


@pytest.mark.parametrize(("field", "value"), [("image_index", -1), ("variant_index", -1)])
def test_preview_variant_trace_rejects_negative_indexes(field: str, value: int) -> None:
    data = {
        "image_index": 0,
        "variant_index": 0,
        "source_path": "source.png",
        "artifact_uri": "albumentationsx://runs/run-1/images/0/0",
        field: value,
    }

    with pytest.raises(ValidationError):
        PreviewVariantTrace.model_validate(data)


@pytest.mark.parametrize(("field", "value"), [("image_index", -1), ("variant_index", -1)])
def test_preview_variant_trace_result_rejects_negative_indexes(field: str, value: int) -> None:
    data = {
        "run_id": "run-1",
        "image_index": 0,
        "variant_index": 0,
        "available": False,
        "message": "Trace unavailable.",
        field: value,
    }

    with pytest.raises(ValidationError):
        PreviewVariantTraceResult.model_validate(data)


def test_trace_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AppliedTransformTrace.model_validate({"name": "Blur", "unknown": True})
