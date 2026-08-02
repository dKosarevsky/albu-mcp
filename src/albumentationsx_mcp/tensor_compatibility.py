"""CPU Tensor boundary validation backed by AlbumentationsX transform capabilities."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Protocol, cast

from albumentationsx_mcp.models import (
    ComposeSpec,
    TargetSpec,
    TensorInputContract,
    TensorPipelineCompatibility,
    TensorTargetContract,
    TensorTransformCompatibility,
    TransformSpec,
    ValidationIssue,
)

_TARGET_RANKS = {
    "image": 3,
    "images": 4,
    "volume": 4,
    "mask": 2,
    "masks": 3,
    "mask3d": 3,
    "bboxes": 2,
    "keypoints": 2,
}
_TARGET_DTYPES = {
    "image": frozenset({"uint8", "float32"}),
    "images": frozenset({"uint8", "float32"}),
    "volume": frozenset({"uint8", "float32"}),
    "mask": frozenset({"uint8", "int64", "float32", "bool"}),
    "masks": frozenset({"uint8", "int64", "float32", "bool"}),
    "mask3d": frozenset({"uint8", "int64", "float32", "bool"}),
    "bboxes": frozenset({"float32"}),
    "keypoints": frozenset({"float32"}),
}
_IMAGE_TARGETS = frozenset({"image", "images", "volume"})
_ANNOTATION_TARGETS = frozenset({"bboxes", "keypoints"})
_SPATIAL_TARGETS = frozenset(_TARGET_RANKS)
_TERMINAL_TENSOR_TRANSFORMS = frozenset({"ToTensorV2", "ToTensor3D"})
_CONSTRAINTS = [
    "All supplied spatial targets must be CPU torch.Tensor values.",
    "Tensor input and output preserve channel-first public layouts.",
    "Do not include ToTensorV2 or ToTensor3D in a Tensor-input pipeline.",
]


class TransformResolver(Protocol):
    """Runtime transform lookup required for capability inspection."""

    def resolve_transform(self, name: str) -> type: ...


class TensorCompatibilityService:
    """Inspect a pipeline without executing transforms or sampling parameters."""

    def __init__(self, catalog: TransformResolver) -> None:
        self.catalog = catalog

    def inspect(
        self,
        pipeline: ComposeSpec,
        target: TargetSpec,
        input_contract: TensorInputContract,
    ) -> TensorPipelineCompatibility:
        """Return a structured compatibility decision for one CPU Tensor boundary."""
        boundary_issues = self._validate_boundary(target, input_contract)
        if boundary_issues:
            return self._report(
                status="incompatible",
                input_contract=input_contract,
                issues=boundary_issues,
                remediation_actions=self._boundary_remediation(boundary_issues),
            )

        requested_targets = frozenset(item.name for item in input_contract.targets) - _ANNOTATION_TARGETS
        image_channels = {
            item.shape[0]
            for item in input_contract.targets
            if item.name in _IMAGE_TARGETS and item.shape[0] is not None
        }
        transforms: list[TensorTransformCompatibility] = []
        issues: list[ValidationIssue] = []
        remediation_actions: list[str] = []
        observed_capability_api = False

        for index, transform_spec in enumerate(pipeline.transforms):
            decision, issue, remediation, capability_api_present = self._inspect_transform(
                transform_spec,
                index=index,
                requested_targets=requested_targets,
                image_channels=image_channels,
            )
            transforms.append(decision)
            observed_capability_api = observed_capability_api or capability_api_present
            if issue is not None:
                issues.append(issue)
            if remediation is not None and remediation not in remediation_actions:
                remediation_actions.append(remediation)

        if not observed_capability_api and pipeline.transforms:
            runtime_issue = ValidationIssue(
                code="cpu_tensor_runtime_unavailable",
                path="input_contract.representation",
                message=(
                    "The installed AlbumentationsX runtime does not expose the CPU Tensor capability API; "
                    "this pipeline cannot be validated for Tensor input."
                ),
            )
            return self._report(
                status="runtime_unavailable",
                input_contract=input_contract,
                transforms=[],
                issues=[runtime_issue],
                remediation_actions=[
                    "Install an AlbumentationsX release that includes the CPU Tensor Compose boundary, "
                    "then validate again."
                ],
            )

        return self._report(
            status="compatible" if not issues else "incompatible",
            input_contract=input_contract,
            transforms=transforms,
            issues=issues,
            remediation_actions=remediation_actions,
        )

    def _inspect_transform(  # noqa: PLR0911 - each capability gate returns its own typed decision.
        self,
        transform_spec: TransformSpec,
        *,
        index: int,
        requested_targets: frozenset[str],
        image_channels: set[int],
    ) -> tuple[TensorTransformCompatibility, ValidationIssue | None, str | None, bool]:
        if transform_spec.name in _TERMINAL_TENSOR_TRANSFORMS:
            reason = f"Remove {transform_spec.name}; Tensor input is already model-ready."
            return (
                self._decision(transform_spec, index=index, compatible=False, reason=reason),
                ValidationIssue(
                    code="terminal_tensor_transform_redundant",
                    path=f"transforms.{index}.name",
                    message=reason,
                ),
                reason,
                True,
            )

        try:
            transform = self._instantiate(transform_spec)
        except (KeyError, TypeError, ValueError) as exc:
            reason = f"Could not inspect {transform_spec.name} Tensor capability: {exc}"
            return (
                self._decision(transform_spec, index=index, compatible=False, reason=reason),
                ValidationIssue(
                    code="cpu_tensor_capability_inspection_failed",
                    path=f"transforms.{index}",
                    message=reason,
                ),
                "Fix transform parameters before validating its CPU Tensor capability.",
                True,
            )

        if not hasattr(transform, "supports_cpu_tensor"):
            reason = f"{transform_spec.name} does not expose the AlbumentationsX CPU Tensor capability contract."
            return self._decision(transform_spec, index=index, compatible=False, reason=reason), None, None, False

        accepted_targets = self._sorted_string_set(getattr(transform, "cpu_tensor_targets", None))
        accepted_channels = self._sorted_int_set(getattr(transform, "cpu_tensor_channels", None))
        if not bool(transform.supports_cpu_tensor):
            reason = f"{transform_spec.name} does not yet declare an accepted CPU Tensor route."
            return (
                self._decision(
                    transform_spec,
                    index=index,
                    compatible=False,
                    reason=reason,
                    accepted_targets=accepted_targets,
                    accepted_channels=accepted_channels,
                ),
                ValidationIssue(
                    code="cpu_tensor_transform_unsupported",
                    path=f"transforms.{index}.name",
                    message=reason,
                ),
                f"Use NumPy input or replace {transform_spec.name} until its Tensor route is accepted upstream.",
                True,
            )

        accepted_target_set = None if accepted_targets is None else frozenset(accepted_targets)
        if accepted_target_set is not None and not requested_targets.issubset(accepted_target_set):
            unsupported = ", ".join(sorted(requested_targets - accepted_target_set))
            reason = f"{transform_spec.name} does not accept Tensor target(s): {unsupported}."
            return (
                self._decision(
                    transform_spec,
                    index=index,
                    compatible=False,
                    reason=reason,
                    accepted_targets=accepted_targets,
                    accepted_channels=accepted_channels,
                ),
                ValidationIssue(
                    code="cpu_tensor_targets_unsupported",
                    path=f"transforms.{index}.name",
                    message=reason,
                ),
                f"Use NumPy input or remove unsupported targets from {transform_spec.name}.",
                True,
            )

        accepted_channel_set = None if accepted_channels is None else frozenset(accepted_channels)
        if accepted_channel_set is not None and not image_channels.issubset(accepted_channel_set):
            unsupported = ", ".join(str(channel) for channel in sorted(image_channels - accepted_channel_set))
            reason = f"{transform_spec.name} does not accept Tensor image channel count(s): {unsupported}."
            return (
                self._decision(
                    transform_spec,
                    index=index,
                    compatible=False,
                    reason=reason,
                    accepted_targets=accepted_targets,
                    accepted_channels=accepted_channels,
                ),
                ValidationIssue(
                    code="cpu_tensor_channels_unsupported",
                    path=f"transforms.{index}.name",
                    message=reason,
                ),
                f"Use an accepted channel count for {transform_spec.name} or keep this pipeline on NumPy input.",
                True,
            )

        reason = f"{transform_spec.name} declares CPU Tensor capability for the requested targets and channels."
        return (
            self._decision(
                transform_spec,
                index=index,
                compatible=True,
                reason=reason,
                accepted_targets=accepted_targets,
                accepted_channels=accepted_channels,
            ),
            None,
            None,
            True,
        )

    def _instantiate(self, transform_spec: TransformSpec) -> object:
        transform_class = self.catalog.resolve_transform(transform_spec.name)
        params = dict(transform_spec.params)
        if transform_spec.p is not None:
            params["p"] = transform_spec.p
        return transform_class(**params)

    @staticmethod
    def _validate_boundary(target: TargetSpec, input_contract: TensorInputContract) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if input_contract.device != "cpu":
            issues.append(
                ValidationIssue(
                    code="tensor_device_unsupported",
                    path="input_contract.device",
                    message=f"CPU Tensor input requires device='cpu', got {input_contract.device!r}.",
                ),
            )
        if input_contract.requires_grad:
            issues.append(
                ValidationIssue(
                    code="tensor_autograd_unsupported",
                    path="input_contract.requires_grad",
                    message="CPU Tensor input requires requires_grad=false.",
                ),
            )

        names = [item.name for item in input_contract.targets]
        duplicate_names = sorted({name for name in names if names.count(name) > 1})
        issues.extend(
            [
                ValidationIssue(
                    code="tensor_target_duplicate",
                    path="input_contract.targets",
                    message=f"Tensor target {name!r} is declared more than once.",
                )
                for name in duplicate_names
            ],
        )

        for index, item in enumerate(input_contract.targets):
            issues.extend(TensorCompatibilityService._validate_target_contract(item, index=index))

        requested_spatial_targets = set(target.targets) & _SPATIAL_TARGETS
        contract_targets = set(names)
        issues.extend(
            [
                ValidationIssue(
                    code="tensor_spatial_target_missing",
                    path="input_contract.targets",
                    message=(
                        f"Tensor input requires a contract for spatial target {missing!r}; "
                        "Tensor and NumPy spatial targets cannot be mixed."
                    ),
                )
                for missing in sorted(requested_spatial_targets - contract_targets)
            ],
        )
        return issues

    @staticmethod
    def _validate_target_contract(item: TensorTargetContract, *, index: int) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        expected_rank = _TARGET_RANKS[item.name]
        if len(item.shape) != expected_rank:
            issues.append(
                ValidationIssue(
                    code="tensor_rank_invalid",
                    path=f"input_contract.targets.{index}.shape",
                    message=f"Tensor target {item.name!r} requires rank {expected_rank}, got {len(item.shape)}.",
                ),
            )
        invalid_dimensions = [dimension for dimension in item.shape if dimension is not None and dimension <= 0]
        if invalid_dimensions:
            issues.append(
                ValidationIssue(
                    code="tensor_shape_invalid",
                    path=f"input_contract.targets.{index}.shape",
                    message=f"Tensor target {item.name!r} dimensions must be positive integers or null.",
                ),
            )

        dtype = item.dtype.removeprefix("torch.")
        if dtype not in _TARGET_DTYPES[item.name]:
            accepted = ", ".join(sorted(_TARGET_DTYPES[item.name]))
            issues.append(
                ValidationIssue(
                    code="tensor_dtype_unsupported",
                    path=f"input_contract.targets.{index}.dtype",
                    message=f"Tensor target {item.name!r} accepts dtype(s) {accepted}, got {item.dtype!r}.",
                ),
            )
        return issues

    @staticmethod
    def _decision(  # noqa: PLR0913 - mirrors the serialized transform decision contract.
        transform_spec: TransformSpec,
        *,
        index: int,
        compatible: bool,
        reason: str,
        accepted_targets: list[str] | None = None,
        accepted_channels: list[int] | None = None,
    ) -> TensorTransformCompatibility:
        return TensorTransformCompatibility(
            index=index,
            name=transform_spec.name,
            compatible=compatible,
            accepted_targets=accepted_targets,
            accepted_channels=accepted_channels,
            reason=reason,
        )

    @staticmethod
    def _sorted_string_set(value: object) -> list[str] | None:
        if value is None:
            return None
        if not isinstance(value, (set, frozenset)):
            return None
        if all(isinstance(item, str) for item in value):
            return sorted(cast("set[str] | frozenset[str]", value))
        return None

    @staticmethod
    def _sorted_int_set(value: object) -> list[int] | None:
        if value is None:
            return None
        if not isinstance(value, (set, frozenset)):
            return None
        if all(type(item) is int for item in value):
            return sorted(cast("set[int] | frozenset[int]", value))
        return None

    @staticmethod
    def _boundary_remediation(issues: list[ValidationIssue]) -> list[str]:
        actions: list[str] = []
        codes = {issue.code for issue in issues}
        if "tensor_device_unsupported" in codes:
            actions.append("Move inputs to CPU before Compose; device transfer remains training-code responsibility.")
        if "tensor_autograd_unsupported" in codes:
            actions.append("Detach Tensor inputs and keep requires_grad=false before augmentation.")
        if codes - {"tensor_device_unsupported", "tensor_autograd_unsupported"}:
            actions.append(
                "Correct the target shapes, dtypes, and complete spatial-target contract, then validate again."
            )
        return actions

    @staticmethod
    def _report(
        *,
        status: str,
        input_contract: TensorInputContract,
        transforms: list[TensorTransformCompatibility] | None = None,
        issues: list[ValidationIssue] | None = None,
        remediation_actions: list[str] | None = None,
    ) -> TensorPipelineCompatibility:
        try:
            runtime_version = version("albumentationsx")
        except PackageNotFoundError:
            runtime_version = None
        return TensorPipelineCompatibility.model_validate(
            {
                "status": status,
                "compatible": status == "compatible",
                "runtime_version": runtime_version,
                "input_contract": input_contract,
                "transforms": transforms or [],
                "issues": issues or [],
                "constraints": _CONSTRAINTS,
                "remediation_actions": remediation_actions or [],
            },
        )
