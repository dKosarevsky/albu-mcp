"""Classify structured JSON contract drift for release review."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

ContractDriftKind = Literal[
    "no_change",
    "documentation_only",
    "compatible_addition",
    "output_shape_change",
    "breaking_change",
]

_DOCUMENTATION_FIELDS = {"description", "title", "summary", "notes", "documentation"}
_STABLE_LIST_KEYS = ("name", "uri", "template")
_MESSAGE_PATH_LIMIT = 5
_PRIORITY: dict[ContractDriftKind, int] = {
    "no_change": 0,
    "documentation_only": 1,
    "compatible_addition": 2,
    "output_shape_change": 3,
    "breaking_change": 4,
}


@dataclass(frozen=True)
class ContractDriftClassification:
    """Severity and paths for generated-vs-committed JSON contract drift."""

    kind: ContractDriftKind
    paths: list[str]
    message: str


@dataclass(frozen=True)
class _Change:
    kind: ContractDriftKind
    path: str


def classify_contract_drift(committed: object, generated: object) -> ContractDriftClassification:
    """Classify how a generated JSON contract differs from the committed fixture."""
    changes = _collect_changes(committed, generated, path="")
    if not changes:
        return ContractDriftClassification(kind="no_change", paths=[], message="no contract drift")

    kind = max((change.kind for change in changes), key=lambda candidate: _PRIORITY[candidate])
    paths = [change.path for change in changes if change.kind == kind]
    return ContractDriftClassification(kind=kind, paths=paths, message=_message(kind, paths))


def main() -> None:
    """CLI entrypoint for local contract drift classification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--committed", type=Path, required=True, help="Committed JSON snapshot path.")
    parser.add_argument("--generated", type=Path, required=True, help="Generated JSON snapshot path.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    classification = classify_contract_drift(
        json.loads(args.committed.read_text(encoding="utf-8")),
        json.loads(args.generated.read_text(encoding="utf-8")),
    )
    if args.format == "json":
        sys.stdout.write(json.dumps(asdict(classification), indent=2))
        sys.stdout.write("\n")
        return
    sys.stdout.write(f"{classification.kind}: {classification.message}\n")


def _collect_changes(committed: object, generated: object, *, path: str) -> list[_Change]:
    if committed == generated:
        return []
    if type(committed) is not type(generated):
        return [_Change(kind="breaking_change", path=_path(path))]
    if isinstance(committed, dict) and isinstance(generated, dict):
        return _dict_changes(cast("dict[str, Any]", committed), cast("dict[str, Any]", generated), path=path)
    if isinstance(committed, list) and isinstance(generated, list):
        return _list_changes(cast("list[Any]", committed), cast("list[Any]", generated), path=path)
    kind: ContractDriftKind = "documentation_only" if _is_documentation_path(path) else "output_shape_change"
    return [_Change(kind=kind, path=_path(path))]


def _dict_changes(committed: dict[str, Any], generated: dict[str, Any], *, path: str) -> list[_Change]:
    changes: list[_Change] = []
    committed_keys = set(committed)
    generated_keys = set(generated)
    changes.extend(
        _Change(kind="breaking_change", path=_join(path, key)) for key in sorted(committed_keys - generated_keys)
    )
    changes.extend(
        _Change(kind="compatible_addition", path=_join(path, key)) for key in sorted(generated_keys - committed_keys)
    )
    for key in sorted(committed_keys & generated_keys, key=str):
        changes.extend(_collect_changes(committed[key], generated[key], path=_join(path, key)))
    return changes


def _list_changes(committed: list[Any], generated: list[Any], *, path: str) -> list[_Change]:
    keyed = _keyed_items(committed, generated)
    if keyed is not None:
        return _keyed_list_changes(keyed[0], keyed[1], generated, path=path)

    changes: list[_Change] = []
    for index, committed_item in enumerate(committed):
        if index >= len(generated):
            changes.append(_Change(kind="breaking_change", path=f"{_path(path)}[{index}]"))
            continue
        changes.extend(_collect_changes(committed_item, generated[index], path=f"{_path(path)}[{index}]"))
    changes.extend(
        _Change(kind="compatible_addition", path=f"{_path(path)}[{index}]")
        for index in range(len(committed), len(generated))
    )
    return changes


def _keyed_list_changes(
    committed: dict[str, Any],
    generated: dict[str, Any],
    generated_items: list[Any],
    *,
    path: str,
) -> list[_Change]:
    changes: list[_Change] = []
    committed_keys = set(committed)
    generated_keys = set(generated)
    changes.extend(
        _Change(kind="breaking_change", path=f"{_path(path)}[{key}]") for key in sorted(committed_keys - generated_keys)
    )
    changes.extend(
        _Change(kind="compatible_addition", path=f"{_path(path)}[{_list_index(generated_items, key)}]")
        for key in sorted(generated_keys - committed_keys)
    )
    for key in sorted(committed_keys & generated_keys):
        changes.extend(_collect_changes(committed[key], generated[key], path=f"{_path(path)}[{key}]"))
    return changes


def _keyed_items(
    committed: list[Any],
    generated: list[Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    key = _stable_list_key(committed + generated)
    if key is None:
        return None
    committed_items = {str(cast("dict[str, Any]", item)[key]): item for item in committed if isinstance(item, dict)}
    generated_items = {str(cast("dict[str, Any]", item)[key]): item for item in generated if isinstance(item, dict)}
    if len(committed_items) != len(committed) or len(generated_items) != len(generated):
        return None
    return committed_items, generated_items


def _stable_list_key(items: list[Any]) -> str | None:
    if not items or not all(isinstance(item, dict) for item in items):
        return None
    for key in _STABLE_LIST_KEYS:
        if all(key in item for item in items if isinstance(item, dict)):
            return key
    return None


def _list_index(items: list[Any], key_value: str) -> int:
    for index, item in enumerate(items):
        if isinstance(item, dict):
            for key in _STABLE_LIST_KEYS:
                if item.get(key) == key_value:
                    return index
    msg = f"Could not find list item {key_value!r}"
    raise ValueError(msg)


def _join(prefix: str, suffix: str) -> str:
    return f"{prefix}.{suffix}" if prefix else suffix


def _path(path: str) -> str:
    return path or "$"


def _is_documentation_path(path: str) -> bool:
    return path.rsplit(".", maxsplit=1)[-1] in _DOCUMENTATION_FIELDS


def _message(kind: ContractDriftKind, paths: list[str]) -> str:
    listed = ", ".join(paths[:_MESSAGE_PATH_LIMIT])
    if len(paths) > _MESSAGE_PATH_LIMIT:
        listed = f"{listed}, ..."
    return f"{kind} at {listed}"


if __name__ == "__main__":
    main()
