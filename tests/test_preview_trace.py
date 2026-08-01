import hashlib
import json
import math
import re
import sys
from collections.abc import ItemsView, Iterator, Mapping, Sequence
from pathlib import Path, PosixPath
from typing import Any, NoReturn

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


class GuardedSequence(Sequence[object]):
    def __init__(self, private_path: str) -> None:
        self.private_path = private_path

    def __getitem__(self, index: int | slice) -> Any:
        raise AssertionError(self.private_path)

    def __len__(self) -> int:
        raise AssertionError(self.private_path)


class GuardedMapping(Mapping[str, object]):
    def __init__(self, private_path: str) -> None:
        self.private_path = private_path

    def __getitem__(self, key: str) -> object:
        raise AssertionError(self.private_path)

    def __iter__(self) -> Iterator[str]:
        raise AssertionError(self.private_path)

    def __len__(self) -> int:
        raise AssertionError(self.private_path)


class FailingNestedMapping(Mapping[str, object]):
    def __init__(self, stage: str, exception_type: type[BaseException], private_path: str) -> None:
        self.stage = stage
        self.exception_type = exception_type
        self.private_path = private_path

    def __getitem__(self, key: str) -> object:
        return 1

    def __iter__(self) -> Iterator[str]:
        if self.stage == "iteration":
            self._fail()
        return iter(("value",))

    def __len__(self) -> int:
        if self.stage == "len":
            self._fail()
        return 1

    def items(self) -> ItemsView[str, object]:
        if self.stage == "items":
            self._fail()
        return super().items()

    def _fail(self) -> NoReturn:
        raise self.exception_type(self.private_path)


class FailingPath(PosixPath):
    private_path = "/private/customer/path-subclass.png"

    def __str__(self) -> str:
        raise KeyError(self.private_path)


class FailingLengthString(str):
    __slots__ = ()

    private_path = "/private/customer/string-subclass.txt"

    def __len__(self) -> int:
        raise KeyError(self.private_path)


class NestedStringPath(PosixPath):
    def __str__(self) -> str:
        return FailingLengthString("source.png")


def _serialized_trace_size(trace: PreviewVariantTrace) -> int:
    encoded = json.dumps(trace.model_dump(mode="json"), allow_nan=False, sort_keys=True)
    return len(encoded.encode("utf-8"))


def _trace_string_digest_token(field_code: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="surrogatepass")).hexdigest()
    return f"~compact:{field_code}:{len(value):016x}:{digest}"


@pytest.mark.parametrize(
    "value",
    ["", 'quote"slash\\', "\x00\x1f\x7f", "é", "😀", "\udcff"],
    ids=["empty", "escaped-ascii", "ascii-boundaries", "bmp", "non-bmp", "surrogate"],
)
def test_json_text_size_matches_standard_encoder_boundaries(value: str) -> None:
    expected = len(json.dumps(value, ensure_ascii=True).encode("utf-8"))

    assert preview_trace._json_text_size(value) == expected


def test_trace_limits_are_stable() -> None:
    assert MAX_INLINE_ARRAY_ELEMENTS == 64
    assert MAX_COLLECTION_ITEMS == 32
    assert MAX_TRACE_DEPTH == 5
    assert MAX_TRACE_NODES == 128
    assert MAX_INLINE_STRING_CHARS == 256
    assert MAX_APPLIED_TRANSFORMS == 32
    assert MAX_VARIANT_TRACE_JSON_BYTES == 8 * 1024
    assert preview_trace.MAX_APPLIED_TRANSFORM_INPUTS == 1024
    assert preview_trace.MAX_TRACE_INPUT_TEXT_CHARS == 32 * 1024
    assert preview_trace.MAX_TRACE_STRING_HASH_CHARS == 64 * 1024
    assert preview_trace.MAX_ARRAY_HASH_BYTES == 1024 * 1024
    assert preview_trace.MAX_INLINE_INTEGER_BITS == 2048
    assert preview_trace.MAX_TRACE_INDEX == (1 << 63) - 1
    assert preview_trace.MIN_TRACE_SEED == -(1 << 63)
    assert preview_trace.MAX_TRACE_SEED == (1 << 63) - 1


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


def test_normalize_trace_value_omits_hash_for_string_above_hash_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "x" * (preview_trace.MAX_TRACE_STRING_HASH_CHARS + 1)
    failure_message = "hashing must remain bounded"

    def fail_hash(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(failure_message)

    monkeypatch.setattr(preview_trace.hashlib, "sha256", fail_hash)

    assert normalize_trace_value(value) == {
        "kind": "string_summary",
        "length": len(value),
        "content_omitted": True,
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
        {f"key-{index:02d}": {"nested": [index] * MAX_COLLECTION_ITEMS} for index in range(MAX_COLLECTION_ITEMS + 1)}
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

    entries = [(bytes([index]), nested_scalar(index)) for index in range(MAX_COLLECTION_ITEMS)]

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
            (bytes([index]), {"payload": f"common-{index:02d}"}) for index in range(2)
        ]
        return dict([*common, (bytes([2]), {"payload": unique_value})])

    entries = [(bytes([index]), nested_value(index)) for index in range(MAX_COLLECTION_ITEMS)]

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


def test_normalize_trace_value_bounds_shared_nested_mapping_order_work(monkeypatch: pytest.MonkeyPatch) -> None:
    leaf = {f"leaf-{index:02d}": index for index in range(MAX_COLLECTION_ITEMS)}
    branch = {f"branch-{index:02d}": leaf for index in range(MAX_COLLECTION_ITEMS)}
    value = {f"root-{index:02d}": branch for index in range(MAX_COLLECTION_ITEMS)}
    builder_count = 0
    token_work = 0
    original_init = preview_trace._TraceOrderTokenBuilder.__init__
    original_normalize = preview_trace._TraceOrderTokenBuilder._normalize

    def counting_init(builder: preview_trace._TraceOrderTokenBuilder) -> None:
        nonlocal builder_count
        builder_count += 1
        original_init(builder)

    def counting_normalize(
        builder: preview_trace._TraceOrderTokenBuilder,
        item: object,
        *,
        depth: int,
    ) -> object:
        nonlocal token_work
        token_work += 1
        if token_work > MAX_TRACE_NODES + 1:
            message = "trace ordering exceeded its shared node budget"
            raise AssertionError(message)
        return original_normalize(builder, item, depth=depth)

    monkeypatch.setattr(preview_trace._TraceOrderTokenBuilder, "__init__", counting_init)
    monkeypatch.setattr(preview_trace._TraceOrderTokenBuilder, "_normalize", counting_normalize)

    assert normalize_trace_value(value) == {
        "kind": "mapping_summary",
        "type": "dict",
        "item_count": MAX_COLLECTION_ITEMS,
        "truncated": True,
    }
    assert builder_count == 1
    assert token_work <= MAX_TRACE_NODES + 1


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


def test_normalize_trace_value_respects_low_json_integer_digit_limit() -> None:
    set_digit_limit = getattr(sys, "set_int_max_str_digits", None)
    get_digit_limit = getattr(sys, "get_int_max_str_digits", None)
    if set_digit_limit is None or get_digit_limit is None:
        pytest.skip("Python does not expose an integer digit limit")

    original_limit = get_digit_limit()
    try:
        set_digit_limit(640)
        value = 1 << 3000

        result = normalize_trace_value({"value": value})

        assert result == {
            "value": {
                "kind": "integer_summary",
                "sign": 1,
                "bit_length": 3001,
            }
        }
        json.dumps(result, allow_nan=False, sort_keys=True)
    finally:
        set_digit_limit(original_limit)


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


def test_build_variant_trace_preserves_transform_order_and_normalizes_params() -> None:
    trace = preview_trace.build_variant_trace(
        image_index=1,
        variant_index=2,
        source_path=Path("source.png"),
        artifact_uri="artifact://run/001-002.png",
        effective_seed=19,
        applied_transforms=[
            ("HorizontalFlip", {"p": np.float32(1.0)}),
            ("GaussNoise", {"noise": np.arange(3, dtype=np.int16)}),
        ],
    )

    assert trace.image_index == 1
    assert trace.variant_index == 2
    assert trace.source_path == "source.png"
    assert trace.artifact_uri == "artifact://run/001-002.png"
    assert trace.effective_seed == 19
    assert [item.name for item in trace.applied_transforms] == ["HorizontalFlip", "GaussNoise"]
    assert trace.applied_transforms[0].params == {"p": 1.0}
    assert trace.applied_transforms[1].params == {"noise": [0, 1, 2]}
    assert trace.truncated_transform_count == 0
    assert trace.parameters_truncated is False
    assert _serialized_trace_size(trace) <= MAX_VARIANT_TRACE_JSON_BYTES


def test_build_variant_trace_accepts_missing_applied_transforms() -> None:
    trace = preview_trace.build_variant_trace(
        image_index=0,
        variant_index=0,
        source_path="source.png",
        artifact_uri="artifact://run/000-000.png",
        effective_seed=None,
        applied_transforms=None,
    )

    assert trace.applied_transforms == []
    assert trace.truncated_transform_count == 0
    assert trace.parameters_truncated is False


@pytest.mark.parametrize("collection_type", [list, tuple], ids=["list", "tuple"])
def test_build_variant_trace_accepts_bounded_concrete_transform_collections(collection_type: type) -> None:
    applied_transforms = collection_type(
        [("HorizontalFlip", {}) for _ in range(preview_trace.MAX_APPLIED_TRANSFORM_INPUTS)]
    )

    trace = preview_trace.build_variant_trace(
        image_index=0,
        variant_index=0,
        source_path=Path("source.png"),
        artifact_uri="artifact://run/000-000.png",
        effective_seed=7,
        applied_transforms=applied_transforms,
    )

    assert len(trace.applied_transforms) == MAX_APPLIED_TRANSFORMS
    assert trace.truncated_transform_count == preview_trace.MAX_APPLIED_TRANSFORM_INPUTS - MAX_APPLIED_TRANSFORMS


def test_build_variant_trace_rejects_custom_sequence_without_probing_it() -> None:
    private_path = "/private/customer/guarded-sequence"

    with pytest.raises(
        ValueError,
        match=r"^applied_transforms must be an ordered collection of \(name, params\) tuples$",
    ) as exc_info:
        preview_trace.build_variant_trace(
            image_index=0,
            variant_index=0,
            source_path="source.png",
            artifact_uri="artifact://run/000-000.png",
            effective_seed=7,
            applied_transforms=GuardedSequence(private_path),
        )

    assert private_path not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


def test_build_variant_trace_rejects_oversized_transform_input_before_iteration() -> None:
    oversized = [UnsupportedValue()] * (preview_trace.MAX_APPLIED_TRANSFORM_INPUTS + 1)
    expected_message = f"applied_transforms must contain at most {preview_trace.MAX_APPLIED_TRANSFORM_INPUTS} entries"

    with pytest.raises(ValueError, match=re.escape(expected_message)) as exc_info:
        preview_trace.build_variant_trace(
            image_index=0,
            variant_index=0,
            source_path="source.png",
            artifact_uri="artifact://run/000-000.png",
            effective_seed=7,
            applied_transforms=oversized,
        )

    assert str(exc_info.value) == expected_message
    assert exc_info.value.__cause__ is None


def test_build_variant_trace_rejects_custom_mapping_in_malformed_tail_without_path_leak() -> None:
    private_path = "/private/customer/guarded-mapping"
    applied_transforms: list[object] = [(f"Transform{index:02d}", {}) for index in range(MAX_APPLIED_TRANSFORMS)]
    applied_transforms.append(("TailTransform", GuardedMapping(private_path)))

    with pytest.raises(
        ValueError,
        match=(r"^applied_transforms entries must be \(name, params\) tuples with string names and mapping params$"),
    ) as exc_info:
        preview_trace.build_variant_trace(
            image_index=0,
            variant_index=0,
            source_path="source.png",
            artifact_uri="artifact://run/000-000.png",
            effective_seed=7,
            applied_transforms=applied_transforms,
        )

    assert private_path not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


@pytest.mark.parametrize("stage", ["len", "items", "iteration"])
def test_build_variant_trace_contains_nested_mapping_exceptions_without_path_leak(stage: str) -> None:
    private_path = f"/private/customer/nested-{stage}.json"
    nested = FailingNestedMapping(stage, KeyError, private_path)

    with pytest.raises(
        ValueError,
        match=r"^applied_transforms could not be normalized safely$",
    ) as exc_info:
        preview_trace.build_variant_trace(
            image_index=0,
            variant_index=0,
            source_path="source.png",
            artifact_uri="artifact://run/000-000.png",
            effective_seed=7,
            applied_transforms=[("HorizontalFlip", {"nested": nested})],
        )

    assert private_path not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


@pytest.mark.parametrize("exception_type", [KeyboardInterrupt, SystemExit])
def test_build_variant_trace_does_not_swallow_normalization_base_exceptions(
    exception_type: type[BaseException],
) -> None:
    nested = FailingNestedMapping("len", exception_type, "/private/customer/base-exception")

    with pytest.raises(exception_type):
        preview_trace.build_variant_trace(
            image_index=0,
            variant_index=0,
            source_path="source.png",
            artifact_uri="artifact://run/000-000.png",
            effective_seed=7,
            applied_transforms=[("HorizontalFlip", {"nested": nested})],
        )


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        ("source_path", 7, "source_path must be a string or pathlib.Path"),
        ("source_path", None, "source_path must be a string or pathlib.Path"),
        ("artifact_uri", 7, "artifact_uri must be a string"),
        ("artifact_uri", None, "artifact_uri must be a string"),
    ],
    ids=["numeric-source-path", "null-source-path", "numeric-artifact-uri", "null-artifact-uri"],
)
def test_build_variant_trace_rejects_invalid_string_metadata(
    field: str,
    value: Any,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=re.escape(expected_message)) as exc_info:
        preview_trace.build_variant_trace(
            image_index=0,
            variant_index=0,
            source_path=value if field == "source_path" else Path("source.png"),
            artifact_uri=value if field == "artifact_uri" else "artifact://run/000-000.png",
            effective_seed=7,
            applied_transforms=[],
        )

    assert str(exc_info.value) == expected_message
    assert len(str(exc_info.value)) < 128


def test_build_variant_trace_contains_path_subclass_string_exception() -> None:
    source_path = FailingPath("source.png")

    with pytest.raises(
        ValueError,
        match=r"^source_path must be a string or pathlib\.Path$",
    ) as exc_info:
        preview_trace.build_variant_trace(
            image_index=0,
            variant_index=0,
            source_path=source_path,
            artifact_uri="artifact://run/000-000.png",
            effective_seed=7,
            applied_transforms=[],
        )

    assert FailingPath.private_path not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


def test_build_variant_trace_canonicalizes_path_string_subclass_inside_boundary() -> None:
    trace = preview_trace.build_variant_trace(
        image_index=0,
        variant_index=0,
        source_path=NestedStringPath("source.png"),
        artifact_uri="artifact://run/000-000.png",
        effective_seed=7,
        applied_transforms=[],
    )

    assert trace.source_path == "source.png"
    assert type(trace.source_path) is str


@pytest.mark.parametrize(
    ("field", "expected_message"),
    [
        ("source_path", "source_path must not exceed 32768 characters"),
        ("artifact_uri", "artifact_uri must not exceed 32768 characters"),
    ],
)
def test_build_variant_trace_rejects_oversized_path_and_uri_text(field: str, expected_message: str) -> None:
    oversized = "x" * (preview_trace.MAX_TRACE_INPUT_TEXT_CHARS + 1)

    with pytest.raises(ValueError, match=re.escape(expected_message)) as exc_info:
        preview_trace.build_variant_trace(
            image_index=0,
            variant_index=0,
            source_path=oversized if field == "source_path" else "source.png",
            artifact_uri=oversized if field == "artifact_uri" else "artifact://run/000-000.png",
            effective_seed=7,
            applied_transforms=[],
        )

    assert str(exc_info.value) == expected_message
    assert oversized not in str(exc_info.value)


def test_build_variant_trace_rejects_one_megabyte_name_before_hash_or_serialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_name = "/private/customer/" + "x" * (1024 * 1024)
    expected_message = "applied transform names must not exceed 32768 characters"
    failure_message = "expensive trace work must not run"

    def fail_expensive_work(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(failure_message)

    monkeypatch.setattr(preview_trace, "_compact_trace_text_digest", fail_expensive_work)
    monkeypatch.setattr(preview_trace, "_trace_fits_json_budget", fail_expensive_work)

    with pytest.raises(ValueError, match=re.escape(expected_message)) as exc_info:
        preview_trace.build_variant_trace(
            image_index=0,
            variant_index=0,
            source_path="source.png",
            artifact_uri="artifact://run/000-000.png",
            effective_seed=7,
            applied_transforms=[(private_name, {})],
        )

    assert str(exc_info.value) == expected_message
    assert private_name not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


def test_build_variant_trace_precompacts_accepted_worst_case_before_first_serialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    max_chars = preview_trace.MAX_TRACE_INPUT_TEXT_CHARS
    transform_names = [f"{index:02d}" + "n" * (max_chars - 2) for index in range(MAX_APPLIED_TRANSFORMS)]
    serialized_text_lengths: list[int] = []
    original_fits = preview_trace._trace_fits_json_budget

    def record_serialized_text_lengths(trace: PreviewVariantTrace) -> bool:
        serialized_text_lengths.append(
            max(
                len(trace.source_path),
                len(trace.artifact_uri),
                *(len(transform.name) for transform in trace.applied_transforms),
            )
        )
        return original_fits(trace)

    monkeypatch.setattr(preview_trace, "_trace_fits_json_budget", record_serialized_text_lengths)

    trace = preview_trace.build_variant_trace(
        image_index=preview_trace.MAX_TRACE_INDEX,
        variant_index=preview_trace.MAX_TRACE_INDEX,
        source_path="s" * max_chars,
        artifact_uri="a" * max_chars,
        effective_seed=preview_trace.MIN_TRACE_SEED,
        applied_transforms=[(name, {}) for name in transform_names],
    )

    assert len(trace.applied_transforms) == MAX_APPLIED_TRANSFORMS
    assert trace.parameters_truncated is True
    assert serialized_text_lengths
    assert serialized_text_lengths[0] <= preview_trace._MAX_COMPACT_STRING_JSON_BYTES
    assert _serialized_trace_size(trace) <= MAX_VARIANT_TRACE_JSON_BYTES


def test_build_variant_trace_caps_applied_transforms() -> None:
    applied_transforms = [(f"Transform{index:02d}", {"index": index}) for index in range(MAX_APPLIED_TRANSFORMS + 5)]

    trace = preview_trace.build_variant_trace(
        image_index=0,
        variant_index=0,
        source_path="source.png",
        artifact_uri="artifact://run/000-000.png",
        effective_seed=7,
        applied_transforms=applied_transforms,
    )

    assert [item.name for item in trace.applied_transforms] == [
        f"Transform{index:02d}" for index in range(MAX_APPLIED_TRANSFORMS)
    ]
    assert trace.truncated_transform_count == 5
    assert _serialized_trace_size(trace) <= MAX_VARIANT_TRACE_JSON_BYTES


def test_build_variant_trace_summarizes_parameters_to_fit_json_budget() -> None:
    params = {f"parameter-{index:02d}": "x" * MAX_INLINE_STRING_CHARS for index in range(MAX_COLLECTION_ITEMS)}

    first = preview_trace.build_variant_trace(
        image_index=0,
        variant_index=0,
        source_path="source.png",
        artifact_uri="artifact://run/000-000.png",
        effective_seed=7,
        applied_transforms=[("LargeParameters", params)],
    )
    second = preview_trace.build_variant_trace(
        image_index=0,
        variant_index=0,
        source_path="source.png",
        artifact_uri="artifact://run/000-000.png",
        effective_seed=7,
        applied_transforms=[("LargeParameters", dict(reversed(list(params.items()))))],
    )

    assert first == second
    assert first.parameters_truncated is True
    assert first.applied_transforms[0].name == "LargeParameters"
    assert first.applied_transforms[0].params["kind"] == "parameter_summary"
    assert len(first.applied_transforms[0].params["sha256"]) == 64
    assert _serialized_trace_size(first) <= MAX_VARIANT_TRACE_JSON_BYTES


def test_build_variant_trace_final_fallback_preserves_all_capped_transform_identities() -> None:
    long_value = "private-segment/" + "x" * (MAX_VARIANT_TRACE_JSON_BYTES * 2)
    transform_names = [f"Transform{index:02d}-{long_value}" for index in range(MAX_APPLIED_TRANSFORMS)]

    trace = preview_trace.build_variant_trace(
        image_index=preview_trace.MAX_TRACE_INDEX,
        variant_index=preview_trace.MAX_TRACE_INDEX,
        source_path=long_value,
        artifact_uri=f"artifact://{long_value}",
        effective_seed=preview_trace.MIN_TRACE_SEED,
        applied_transforms=[(name, {"value": long_value}) for name in transform_names],
    )
    encoded = json.dumps(trace.model_dump(mode="json"), allow_nan=False, sort_keys=True)

    assert trace.parameters_truncated is True
    assert trace.source_path == _trace_string_digest_token("source_path", long_value)
    assert trace.artifact_uri == _trace_string_digest_token("artifact_uri", f"artifact://{long_value}")
    assert [item.name for item in trace.applied_transforms] == [
        _trace_string_digest_token("transform_name", name) for name in transform_names
    ]
    assert all(item.params == {} for item in trace.applied_transforms)
    assert len(trace.applied_transforms) == MAX_APPLIED_TRANSFORMS
    assert trace.truncated_transform_count == 0
    assert long_value not in encoded
    assert len(encoded.encode("utf-8")) <= MAX_VARIANT_TRACE_JSON_BYTES
    assert preview_trace._MAX_FINAL_VARIANT_TRACE_JSON_BYTES <= MAX_VARIANT_TRACE_JSON_BYTES


def test_build_variant_trace_compaction_does_not_collide_with_compact_token_literal() -> None:
    long_name = "Transform-" + "x" * (MAX_VARIANT_TRACE_JSON_BYTES * 2)
    compact_token_literal = _trace_string_digest_token("transform_name", long_name)

    trace = preview_trace.build_variant_trace(
        image_index=0,
        variant_index=0,
        source_path="source.png",
        artifact_uri="artifact://run/000-000.png",
        effective_seed=7,
        applied_transforms=[(long_name, {}), (compact_token_literal, {})],
    )

    assert [item.name for item in trace.applied_transforms] == [
        _trace_string_digest_token("transform_name", long_name),
        f"~literal:{compact_token_literal}",
    ]
    assert trace.applied_transforms[0].name != trace.applied_transforms[1].name
    assert _serialized_trace_size(trace) <= MAX_VARIANT_TRACE_JSON_BYTES


def test_build_variant_trace_escapes_reserved_prefixes_during_fallback() -> None:
    long_value = "x" * (MAX_VARIANT_TRACE_JSON_BYTES * 2)
    compact_literal = _trace_string_digest_token("transform_name", long_value)
    reserved_names = [
        compact_literal,
        f"~literal:{compact_literal}",
        "~literal:~literal:ordinary",
        "HorizontalFlip",
    ]

    trace = preview_trace.build_variant_trace(
        image_index=0,
        variant_index=0,
        source_path=long_value,
        artifact_uri=f"artifact://{long_value}",
        effective_seed=7,
        applied_transforms=[(name, {}) for name in reserved_names],
    )

    assert [item.name for item in trace.applied_transforms] == [
        f"~literal:{compact_literal}",
        f"~literal:~literal:{compact_literal}",
        "~literal:~literal:~literal:ordinary",
        "HorizontalFlip",
    ]
    assert _serialized_trace_size(trace) <= MAX_VARIANT_TRACE_JSON_BYTES


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        (
            "image_index",
            10**5000,
            f"image_index must be an integer between 0 and {(1 << 63) - 1}",
        ),
        (
            "variant_index",
            10**5000,
            f"variant_index must be an integer between 0 and {(1 << 63) - 1}",
        ),
        (
            "effective_seed",
            10**5000,
            f"effective_seed must be None or an integer between {-(1 << 63)} and {(1 << 63) - 1}",
        ),
        (
            "effective_seed",
            -(10**5000),
            f"effective_seed must be None or an integer between {-(1 << 63)} and {(1 << 63) - 1}",
        ),
    ],
    ids=["image-too-large", "variant-too-large", "seed-too-large", "seed-too-small"],
)
def test_build_variant_trace_rejects_unbounded_integer_metadata_before_json(
    field: str,
    value: int,
    expected_message: str,
) -> None:
    private_path = "/private/customer/input.png"

    with pytest.raises(ValueError, match=re.escape(expected_message)) as exc_info:
        preview_trace.build_variant_trace(
            image_index=value if field == "image_index" else 0,
            variant_index=value if field == "variant_index" else 0,
            source_path=private_path,
            artifact_uri="artifact://run/000-000.png",
            effective_seed=value if field == "effective_seed" else 0,
            applied_transforms=[("HorizontalFlip", {"p": 1.0})],
        )

    assert str(exc_info.value) == expected_message
    assert private_path not in str(exc_info.value)
    assert len(str(exc_info.value)) < 128


def test_build_variant_trace_rejects_non_collection_without_repr() -> None:
    with pytest.raises(
        ValueError,
        match=r"^applied_transforms must be an ordered collection of \(name, params\) tuples$",
    ):
        preview_trace.build_variant_trace(
            image_index=0,
            variant_index=0,
            source_path="source.png",
            artifact_uri="artifact://run/000-000.png",
            effective_seed=None,
            applied_transforms=UnsupportedValue(),
        )


def test_build_variant_trace_rejects_malformed_entries_without_leaking_values() -> None:
    private_name = "/private/customer/input.png"

    with pytest.raises(
        ValueError,
        match=(r"^applied_transforms entries must be \(name, params\) tuples with string names and mapping params$"),
    ) as exc_info:
        preview_trace.build_variant_trace(
            image_index=0,
            variant_index=0,
            source_path="source.png",
            artifact_uri="artifact://run/000-000.png",
            effective_seed=None,
            applied_transforms=[(private_name, UnsupportedValue())],
        )

    assert str(exc_info.value) == (
        "applied_transforms entries must be (name, params) tuples with string names and mapping params"
    )
    assert private_name not in str(exc_info.value)


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


def test_preview_variant_trace_accepts_collection_and_count_boundaries() -> None:
    transforms = [{"name": f"Transform{index:02d}", "params": {}} for index in range(MAX_APPLIED_TRANSFORMS)]

    trace = PreviewVariantTrace.model_validate(
        {
            "image_index": 0,
            "variant_index": 0,
            "source_path": "source.png",
            "artifact_uri": "albumentationsx://runs/run-1/images/0/0",
            "applied_transforms": transforms,
            "truncated_transform_count": preview_trace.MAX_TRACE_INDEX,
        }
    )

    assert len(trace.applied_transforms) == MAX_APPLIED_TRANSFORMS
    assert trace.truncated_transform_count == preview_trace.MAX_TRACE_INDEX


def test_preview_variant_trace_rejects_too_many_applied_transforms() -> None:
    transforms = [{"name": f"Transform{index:02d}", "params": {}} for index in range(MAX_APPLIED_TRANSFORMS + 1)]

    with pytest.raises(ValidationError):
        PreviewVariantTrace.model_validate(
            {
                "image_index": 0,
                "variant_index": 0,
                "source_path": "source.png",
                "artifact_uri": "albumentationsx://runs/run-1/images/0/0",
                "applied_transforms": transforms,
            }
        )


def test_preview_variant_trace_rejects_oversized_truncated_transform_count() -> None:
    with pytest.raises(ValidationError):
        PreviewVariantTrace.model_validate(
            {
                "image_index": 0,
                "variant_index": 0,
                "source_path": "source.png",
                "artifact_uri": "albumentationsx://runs/run-1/images/0/0",
                "truncated_transform_count": preview_trace.MAX_TRACE_INDEX + 1,
            }
        )


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


def test_trace_models_reject_coercive_values_and_containers() -> None:
    with pytest.raises(ValidationError):
        AppliedTransformTrace.model_validate({"name": b"Blur", "params": {}})

    with pytest.raises(ValidationError):
        PreviewVariantTrace.model_validate(
            {
                "image_index": 0,
                "variant_index": 0,
                "source_path": "source.png",
                "artifact_uri": "albumentationsx://runs/run-1/images/0/0",
                "applied_transforms": (),
            }
        )

    with pytest.raises(ValidationError):
        PreviewVariantTraceResult.model_validate(
            {
                "run_id": "run-1",
                "image_index": 0,
                "variant_index": 0,
                "available": "false",
                "message": "Trace unavailable.",
            }
        )
