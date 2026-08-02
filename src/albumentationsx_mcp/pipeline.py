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
    TensorInputContract,
    TransformMetadata,
    TransformSpec,
    ValidationIssue,
)
from albumentationsx_mcp.tensor_compatibility import TensorCompatibilityService


class CatalogLike(Protocol):
    """Catalog methods needed by PipelineService."""

    def get_transform_schema(self, name: str) -> TransformMetadata: ...

    def resolve_transform(self, name: str) -> type: ...


class PipelineService:
    """Validate and materialize typed pipeline specs."""

    def __init__(self, catalog: CatalogLike) -> None:
        self.catalog = catalog
        self.tensor_compatibility = TensorCompatibilityService(catalog)

    def validate_pipeline(
        self,
        pipeline: ComposeSpec,
        target: TargetSpec | None = None,
        *,
        input_contract: TensorInputContract | None = None,
    ) -> PipelineValidationReport:
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

        tensor_compatibility = None
        if input_contract is not None:
            tensor_compatibility = self.tensor_compatibility.inspect(pipeline, target, input_contract)
            errors.extend(tensor_compatibility.issues)

        return PipelineValidationReport(
            valid=not errors,
            errors=errors,
            warnings=warnings,
            normalized_pipeline=pipeline.model_dump(mode="json", exclude_none=True),
            tensor_compatibility=tensor_compatibility,
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

        bbox_params = (
            A.BboxParams(**_runtime_bbox_params(pipeline.bbox_params)) if pipeline.bbox_params is not None else None
        )
        keypoint_params = A.KeypointParams(**pipeline.keypoint_params) if pipeline.keypoint_params is not None else None
        return A.Compose(
            transforms,
            bbox_params=bbox_params,
            keypoint_params=keypoint_params,
            additional_targets=pipeline.additional_targets,
            is_check_shapes=pipeline.is_check_shapes,
            strict=pipeline.strict,
            seed=pipeline.seed,
            save_applied_params=True,
        )

    def export_pipeline(
        self,
        pipeline: ComposeSpec,
        *,
        output_format: Literal["python", "json", "yaml"],
        target: TargetSpec | None = None,
        input_contract: TensorInputContract | None = None,
    ) -> ExportResult:
        """Export a pipeline to Python code, JSON, or YAML."""
        if input_contract is not None:
            if output_format != "python":
                msg = "A CPU Tensor input contract can be exported only as Python."
                raise ValueError(msg)
            effective_target = target or TargetSpec(targets=[item.name for item in input_contract.targets])
            validation = self.validate_pipeline(
                pipeline,
                effective_target,
                input_contract=input_contract,
            )
            if not validation.valid:
                issues = "; ".join(f"{issue.code}: {issue.message}" for issue in validation.errors)
                msg = f"Cannot export an incompatible CPU Tensor pipeline: {issues}"
                raise ValueError(msg)

        if output_format == "python":
            content = self._export_python(pipeline, input_contract=input_contract)
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

    def _export_python(self, pipeline: ComposeSpec, *, input_contract: TensorInputContract | None = None) -> str:
        lines = ["import albumentations as A"]
        if input_contract is not None:
            lines.append("import torch")
        lines.extend(["", "transform = A.Compose(["])
        lines.extend(f"    {self._format_transform(transform)}," for transform in pipeline.transforms)
        lines.append("],")
        if pipeline.bbox_params is not None:
            lines.append(f"    bbox_params=A.BboxParams(**{_runtime_bbox_params(pipeline.bbox_params)!r}),")
        if pipeline.keypoint_params is not None:
            lines.append(f"    keypoint_params=A.KeypointParams(**{pipeline.keypoint_params!r}),")
        if pipeline.additional_targets:
            lines.append(f"    additional_targets={pipeline.additional_targets!r},")
        lines.append(f"    is_check_shapes={pipeline.is_check_shapes!r},")
        lines.append(f"    strict={pipeline.strict!r},")
        if pipeline.seed is not None:
            lines.append(f"    seed={pipeline.seed!r},")
        lines.append(")")
        if input_contract is not None:
            lines.extend(self._export_tensor_handoff(input_contract))
        return "\n".join(lines)

    @staticmethod
    def _export_tensor_handoff(input_contract: TensorInputContract) -> list[str]:
        target_names = [target.name for target in input_contract.targets]
        arguments = ", ".join(f"{name}: torch.Tensor" for name in target_names)
        lines = [
            "",
            f"def augment({arguments}) -> dict[str, torch.Tensor]:",
            '    """Apply a validated channel-first CPU Tensor pipeline."""',
        ]
        for target in input_contract.targets:
            dtype = target.dtype.removeprefix("torch.")
            lines.extend(
                [
                    f"    if not isinstance({target.name}, torch.Tensor):",
                    f"        raise TypeError({target.name!r} + ' must be a torch.Tensor')",
                    f"    if {target.name}.device.type != {input_contract.device!r}:",
                    f"        raise ValueError({target.name!r} + ' must be on device {input_contract.device}')",
                    f"    if {target.name}.requires_grad:",
                    f"        raise ValueError({target.name!r} + ' must have requires_grad=False')",
                    f"    if {target.name}.dtype is not torch.{dtype}:",
                    f"        raise TypeError({target.name!r} + ' must have dtype torch.{dtype}')",
                    f"    if {target.name}.ndim != {len(target.shape)}:",
                    f"        raise TypeError({target.name!r} + ' must have rank {len(target.shape)}')",
                    f"    expected_shape = {tuple(target.shape)!r}",
                    "    if any(",
                    "        expected is not None and actual != expected",
                    f"        for actual, expected in zip({target.name}.shape, expected_shape, strict=True)",
                    "    ):",
                    f"        raise ValueError({target.name!r} + f' must match shape {{expected_shape}}')",
                ],
            )
        call_arguments = ", ".join(f"{name}={name}" for name in target_names)
        lines.append(f"    return transform({call_arguments})")
        return lines

    @staticmethod
    def _format_transform(transform: TransformSpec) -> str:
        params = dict(transform.params)
        if transform.p is not None:
            params["p"] = transform.p
        args = ", ".join(f"{name}={value!r}" for name, value in sorted(params.items()))
        return f"A.{transform.name}({args})" if args else f"A.{transform.name}()"


def _runtime_bbox_params(params: dict[str, Any] | None) -> dict[str, Any]:
    """Adapt public bbox params to the installed AlbumentationsX runtime API."""
    if params is None:
        return {}
    runtime_params = dict(params)
    if "format" in runtime_params and "coord_format" not in runtime_params:
        runtime_params["coord_format"] = runtime_params.pop("format")
    return runtime_params
