"""Transform catalog backed by albu-spec metadata."""

from __future__ import annotations

from typing import Any

from albumentationsx_mcp.models import ConstraintInfo, ParameterInfo, TransformMetadata, TransformSearchResult


def _model_to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return dict(vars(value))


def _convert_parameter(name: str, value: Any) -> ParameterInfo:
    data = _model_to_dict(value)
    constraints = data.get("constraints")
    return ParameterInfo(
        name=data.get("name", name),
        type_hint=data.get("type_hint", "Any"),
        default=data.get("default"),
        description=data.get("description"),
        constraints=ConstraintInfo.model_validate(_model_to_dict(constraints)) if constraints is not None else None,
    )


def convert_albu_spec_metadata(value: Any) -> TransformMetadata:
    """Convert albu-spec Pydantic models to this server's stable metadata schema."""
    data = _model_to_dict(value)
    parameters = {
        name: _convert_parameter(name, parameter) for name, parameter in (data.get("parameters") or {}).items()
    }
    return TransformMetadata(
        name=data["name"],
        module=data.get("module", ""),
        transform_type=data.get("transform_type", "unknown"),
        targets=list(data.get("targets") or []),
        parameters=parameters,
        docstring_short=data.get("docstring_short"),
        supported_bbox_types=data.get("supported_bbox_types"),
    )


class TransformCatalog:
    """Lazy catalog of AlbumentationsX transforms and their metadata."""

    def __init__(self) -> None:
        self._metadata_by_name: dict[str, TransformMetadata] | None = None

    def _load(self) -> dict[str, TransformMetadata]:
        if self._metadata_by_name is None:
            from albu_spec import get_all_transforms_metadata

            collection = get_all_transforms_metadata()
            metadata = [convert_albu_spec_metadata(item) for item in collection.get_all()]
            self._metadata_by_name = {item.name: item for item in metadata}
        return self._metadata_by_name

    def list_transforms(self) -> list[TransformMetadata]:
        """Return all transform metadata sorted by transform name."""
        return sorted(self._load().values(), key=lambda item: item.name)

    def get_transform_schema(self, name: str) -> TransformMetadata:
        """Return metadata for one transform."""
        metadata = self._load()
        try:
            return metadata[name]
        except KeyError as exc:
            raise KeyError(f"Unknown AlbumentationsX transform: {name}") from exc

    def resolve_transform(self, name: str) -> type:
        """Resolve an AlbumentationsX transform class by public name."""
        import albumentations as A

        if not hasattr(A, name):
            raise KeyError(f"Unknown AlbumentationsX transform: {name}")
        transform_class = getattr(A, name)
        if not isinstance(transform_class, type):
            raise KeyError(f"Albumentations attribute is not a transform class: {name}")
        return transform_class

    def search_transforms(
        self,
        query: str = "",
        *,
        targets: list[str] | None = None,
        transform_type: str | None = None,
        bbox_type: str | None = None,
        limit: int = 20,
    ) -> list[TransformSearchResult]:
        """Search transforms by name, description, targets, type, and bbox support."""
        query_tokens = {token.lower() for token in query.split() if token.strip()}
        target_set = set(targets or [])
        results: list[TransformSearchResult] = []

        for item in self.list_transforms():
            if transform_type and item.transform_type != transform_type:
                continue
            if bbox_type and bbox_type not in set(item.supported_bbox_types or []):
                continue
            if target_set and not self._matches_targets(item, target_set):
                continue

            haystack = " ".join(
                [
                    item.name,
                    item.module,
                    item.docstring_short or "",
                    " ".join(item.targets),
                    " ".join(item.parameters),
                ],
            ).lower()
            score = self._score(query_tokens, item.name.lower(), haystack)
            if query_tokens and score == 0:
                continue
            results.append(
                TransformSearchResult(
                    name=item.name,
                    transform_type=item.transform_type,
                    targets=item.targets,
                    score=score,
                    summary=item.docstring_short,
                    supported_bbox_types=item.supported_bbox_types,
                ),
            )

        return sorted(results, key=lambda result: (-result.score, result.name))[:limit]

    @staticmethod
    def _matches_targets(item: TransformMetadata, target_set: set[str]) -> bool:
        if "image" in target_set and "image" not in item.targets:
            return False
        annotation_targets = target_set - {"image", "images", "volume", "volumes"}
        if item.transform_type == "image_only":
            return True
        return annotation_targets.issubset(set(item.targets))

    @staticmethod
    def _score(query_tokens: set[str], name: str, haystack: str) -> float:
        if not query_tokens:
            return 1.0
        score = 0.0
        for token in query_tokens:
            if token == name:
                score += 5.0
            elif token in name:
                score += 3.0
            elif token in haystack:
                score += 1.0
        return score
