"""Pipeline validation, construction, and export."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any, Literal, Protocol

import yaml

from albumentationsx_mcp.models import (
    ComposeSpec,
    ConstraintInfo,
    ExportResult,
    PipelineValidationReport,
    TargetSpec,
    TransformMetadata,
    TransformSpec,
    ValidationIssue,
)


class CatalogLike(Protocol):
    """Catalog methods needed by PipelineService."""

    def get_transform_schema(self, name: str) -> TransformMetadata: ...

    def resolve_transform(self, name: str) -> type: ...


class PipelineService:
    """Validate and materialize typed pipeline specs."""

    def __init__(self, catalog: CatalogLike) -> None:
        self.catalog = catalog

    def validate_pipeline(self, pipeline: ComposeSpec, target: TargetSpec | None = None) -> PipelineValidationReport:
        """Validate transform names, parameters, constraints, and target hints."""
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        target = target or TargetSpec()

        for index, transform in enumerate(pipeline.transforms):
            metadata = self._get_metadata(transform, index, errors)
            if metadata is None:
                continue
            self._validate_params(transform, metadata, index, errors)
            self._validate_target_warnings(transform, metadata, target, index, warnings)

        return PipelineValidationReport(
            valid=not errors,
            errors=errors,
            warnings=warnings,
            normalized_pipeline=pipeline.model_dump(mode="json", exclude_none=True),
        )

    def build_pipeline(self, pipeline: ComposeSpec) -> Any:
        """Build a real AlbumentationsX Compose instance."""
        import albumentations as A

        transforms = []
        for transform_spec in pipeline.transforms:
            transform_class = self.catalog.resolve_transform(transform_spec.name)
            params = dict(transform_spec.params)
            if transform_spec.p is not None:
                params["p"] = transform_spec.p
            transforms.append(transform_class(**params))

        bbox_params = A.BboxParams(**pipeline.bbox_params) if pipeline.bbox_params is not None else None
        keypoint_params = A.KeypointParams(**pipeline.keypoint_params) if pipeline.keypoint_params is not None else None
        return A.Compose(
            transforms,
            bbox_params=bbox_params,
            keypoint_params=keypoint_params,
            additional_targets=pipeline.additional_targets,
            is_check_shapes=pipeline.is_check_shapes,
            strict=pipeline.strict,
            seed=pipeline.seed,
        )

    def export_pipeline(
        self,
        pipeline: ComposeSpec,
        *,
        output_format: Literal["python", "json", "yaml"],
    ) -> ExportResult:
        """Export a pipeline to Python code, JSON, or YAML."""
        if output_format == "python":
            content = self._export_python(pipeline)
        else:
            data = pipeline.model_dump(mode="json", exclude_none=True)
            if output_format == "json":
                content = json.dumps(data, indent=2, sort_keys=True)
            elif output_format == "yaml":
                content = yaml.safe_dump(data, sort_keys=True)
            else:
                raise ValueError(f"Unsupported export format: {output_format}")
        return ExportResult(format=output_format, content=content)

    def _get_metadata(
        self,
        transform: TransformSpec,
        index: int,
        errors: list[ValidationIssue],
    ) -> TransformMetadata | None:
        try:
            return self.catalog.get_transform_schema(transform.name)
        except KeyError:
            errors.append(
                ValidationIssue(
                    code="unknown_transform",
                    path=f"transforms.{index}.name",
                    message=f"Unknown transform: {transform.name}",
                ),
            )
            return None

    def _validate_params(
        self,
        transform: TransformSpec,
        metadata: TransformMetadata,
        index: int,
        errors: list[ValidationIssue],
    ) -> None:
        params = dict(transform.params)
        if transform.p is not None:
            params["p"] = transform.p

        for param_name, value in params.items():
            path = f"transforms.{index}.params.{param_name}"
            parameter = metadata.parameters.get(param_name)
            if parameter is None:
                errors.append(
                    ValidationIssue(
                        code="unknown_parameter",
                        path=path,
                        message=f"{metadata.name} has no parameter named {param_name}",
                    ),
                )
                continue
            if parameter.constraints is not None:
                errors.extend(self._constraint_errors(path, value, parameter.constraints))

    def _validate_target_warnings(
        self,
        transform: TransformSpec,
        metadata: TransformMetadata,
        target: TargetSpec,
        index: int,
        warnings: list[ValidationIssue],
    ) -> None:
        if target.bbox_type and metadata.supported_bbox_types and target.bbox_type not in metadata.supported_bbox_types:
            warnings.append(
                ValidationIssue(
                    code="bbox_type_not_supported",
                    path=f"transforms.{index}.name",
                    message=f"{transform.name} does not advertise {target.bbox_type} bbox support",
                ),
            )

    def _constraint_errors(self, path: str, value: Any, constraints: ConstraintInfo) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        for numeric_value in self._numeric_values(value):
            if constraints.ge is not None and numeric_value < constraints.ge:
                errors.append(self._constraint_issue(path, f"{numeric_value} violates ge={constraints.ge}"))
            if constraints.le is not None and numeric_value > constraints.le:
                errors.append(self._constraint_issue(path, f"{numeric_value} violates le={constraints.le}"))
            if constraints.gt is not None and numeric_value <= constraints.gt:
                errors.append(self._constraint_issue(path, f"{numeric_value} violates gt={constraints.gt}"))
            if constraints.lt is not None and numeric_value >= constraints.lt:
                errors.append(self._constraint_issue(path, f"{numeric_value} violates lt={constraints.lt}"))
        return errors

    @staticmethod
    def _constraint_issue(path: str, message: str) -> ValidationIssue:
        return ValidationIssue(code="constraint_violation", path=path, message=message)

    def _numeric_values(self, value: Any) -> Iterable[float]:
        if isinstance(value, bool):
            return []
        if isinstance(value, (int, float)):
            return [float(value)]
        if isinstance(value, dict):
            values: list[float] = []
            for nested in value.values():
                values.extend(self._numeric_values(nested))
            return values
        if isinstance(value, (list, tuple)):
            values = []
            for nested in value:
                values.extend(self._numeric_values(nested))
            return values
        return []

    def _export_python(self, pipeline: ComposeSpec) -> str:
        lines = ["import albumentations as A", "", "transform = A.Compose(["]
        lines.extend(f"    {self._format_transform(transform)}," for transform in pipeline.transforms)
        lines.append("],")
        if pipeline.bbox_params is not None:
            lines.append(f"    bbox_params=A.BboxParams(**{pipeline.bbox_params!r}),")
        if pipeline.keypoint_params is not None:
            lines.append(f"    keypoint_params=A.KeypointParams(**{pipeline.keypoint_params!r}),")
        if pipeline.additional_targets:
            lines.append(f"    additional_targets={pipeline.additional_targets!r},")
        lines.append(f"    is_check_shapes={pipeline.is_check_shapes!r},")
        lines.append(f"    strict={pipeline.strict!r},")
        if pipeline.seed is not None:
            lines.append(f"    seed={pipeline.seed!r},")
        lines.append(")")
        return "\n".join(lines)

    @staticmethod
    def _format_transform(transform: TransformSpec) -> str:
        params = dict(transform.params)
        if transform.p is not None:
            params["p"] = transform.p
        args = ", ".join(f"{name}={value!r}" for name, value in sorted(params.items()))
        return f"A.{transform.name}({args})" if args else f"A.{transform.name}()"
