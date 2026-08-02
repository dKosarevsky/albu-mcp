from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from albumentationsx_mcp.models import (
    ComposeSpec,
    TargetSpec,
    TensorInputContract,
    TensorTargetContract,
    TransformMetadata,
    TransformSpec,
)
from albumentationsx_mcp.pipeline import PipelineService


class _TensorTransform:
    supports_cpu_tensor = True
    cpu_tensor_targets: frozenset[str] | None = None
    cpu_tensor_channels: frozenset[int] | None = None

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class _ImageMaskTensorTransform(_TensorTransform):
    cpu_tensor_targets = frozenset({"image", "mask", "masks", "mask3d"})
    cpu_tensor_channels = frozenset({1, 3})


class _UnsupportedTensorTransform(_TensorTransform):
    supports_cpu_tensor = False


class _LegacyTransform:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


@dataclass
class _CapabilityCatalog:
    classes: dict[str, type]

    def get_transform_schema(self, name: str) -> TransformMetadata:
        if name not in self.classes:
            raise KeyError(name)
        return TransformMetadata(
            name=name,
            module="tests",
            transform_type="dual",
            targets=["image", "mask", "masks", "mask3d", "bboxes", "keypoints"],
        )

    def resolve_transform(self, name: str) -> type:
        return self.classes[name]


def _contract(*targets: TensorTargetContract, device: str = "cpu", requires_grad: bool = False) -> TensorInputContract:
    return TensorInputContract(targets=list(targets), device=device, requires_grad=requires_grad)


def _image(*, channels: int = 3, dtype: str = "uint8") -> TensorTargetContract:
    return TensorTargetContract(name="image", shape=[channels, None, None], dtype=dtype)


def test_validate_pipeline_reports_compatible_cpu_tensor_pipeline() -> None:
    service = PipelineService(
        _CapabilityCatalog(
            {
                "NoOp": _TensorTransform,
                "Transpose": _ImageMaskTensorTransform,
            },
        ),
    )
    pipeline = ComposeSpec(transforms=[TransformSpec(name="NoOp"), TransformSpec(name="Transpose")])
    input_contract = _contract(
        _image(),
        TensorTargetContract(name="mask", shape=[None, None], dtype="int64"),
    )

    report = service.validate_pipeline(
        pipeline,
        TargetSpec(targets=["image", "mask"]),
        input_contract=input_contract,
    )

    assert report.valid
    assert report.tensor_compatibility is not None
    assert report.tensor_compatibility.status == "compatible"
    assert report.tensor_compatibility.compatible
    assert [item.name for item in report.tensor_compatibility.transforms] == ["NoOp", "Transpose"]
    assert report.tensor_compatibility.constraints == [
        "All supplied spatial targets must be CPU torch.Tensor values.",
        "Tensor input and output preserve channel-first public layouts.",
        "Do not include ToTensorV2 or ToTensor3D in a Tensor-input pipeline.",
    ]


def test_validate_pipeline_reports_transform_without_tensor_capability() -> None:
    service = PipelineService(_CapabilityCatalog({"HorizontalFlip": _UnsupportedTensorTransform}))

    report = service.validate_pipeline(
        ComposeSpec(transforms=[TransformSpec(name="HorizontalFlip")]),
        TargetSpec(targets=["image"]),
        input_contract=_contract(_image()),
    )

    assert not report.valid
    assert report.tensor_compatibility is not None
    assert report.tensor_compatibility.status == "incompatible"
    assert report.errors[0].code == "cpu_tensor_transform_unsupported"
    assert report.errors[0].path == "transforms.0.name"
    assert report.tensor_compatibility.transforms[0].compatible is False
    assert "NumPy input" in report.tensor_compatibility.remediation_actions[0]


def test_validate_pipeline_reports_unsupported_tensor_channel_count() -> None:
    service = PipelineService(_CapabilityCatalog({"Transpose": _ImageMaskTensorTransform}))

    report = service.validate_pipeline(
        ComposeSpec(transforms=[TransformSpec(name="Transpose")]),
        TargetSpec(targets=["image"]),
        input_contract=_contract(_image(channels=5)),
    )

    assert not report.valid
    assert report.tensor_compatibility is not None
    transform = report.tensor_compatibility.transforms[0]
    assert report.errors[0].code == "cpu_tensor_channels_unsupported"
    assert transform.accepted_channels == [1, 3]
    assert transform.compatible is False


@pytest.mark.parametrize(
    ("contract", "target", "expected_code"),
    [
        (
            _contract(TensorTargetContract(name="image", shape=[3, None], dtype="uint8")),
            ["image"],
            "tensor_rank_invalid",
        ),
        (_contract(_image(dtype="int64")), ["image"], "tensor_dtype_unsupported"),
        (_contract(_image(), device="cuda"), ["image"], "tensor_device_unsupported"),
        (_contract(_image(), requires_grad=True), ["image"], "tensor_autograd_unsupported"),
        (_contract(_image()), ["image", "mask"], "tensor_spatial_target_missing"),
    ],
)
def test_validate_pipeline_reports_tensor_boundary_errors(
    contract: TensorInputContract,
    target: list[str],
    expected_code: str,
) -> None:
    service = PipelineService(_CapabilityCatalog({"NoOp": _TensorTransform}))

    report = service.validate_pipeline(
        ComposeSpec(transforms=[TransformSpec(name="NoOp")]),
        TargetSpec(targets=target),
        input_contract=contract,
    )

    assert not report.valid
    assert report.tensor_compatibility is not None
    assert report.tensor_compatibility.status == "incompatible"
    assert expected_code in {issue.code for issue in report.errors}


def test_validate_pipeline_reports_runtime_without_tensor_capability_api() -> None:
    service = PipelineService(_CapabilityCatalog({"NoOp": _LegacyTransform}))

    report = service.validate_pipeline(
        ComposeSpec(transforms=[TransformSpec(name="NoOp")]),
        TargetSpec(targets=["image"]),
        input_contract=_contract(_image()),
    )

    assert not report.valid
    assert report.tensor_compatibility is not None
    assert report.tensor_compatibility.status == "runtime_unavailable"
    assert report.errors[0].code == "cpu_tensor_runtime_unavailable"
    assert report.tensor_compatibility.runtime_version is not None


@pytest.mark.parametrize("name", ["ToTensorV2", "ToTensor3D"])
def test_validate_pipeline_rejects_terminal_tensor_transform(name: str) -> None:
    service = PipelineService(_CapabilityCatalog({name: _TensorTransform}))

    report = service.validate_pipeline(
        ComposeSpec(transforms=[TransformSpec(name=name)]),
        TargetSpec(targets=["image"]),
        input_contract=_contract(_image()),
    )

    assert not report.valid
    assert report.tensor_compatibility is not None
    assert report.errors[0].code == "terminal_tensor_transform_redundant"
    assert "remove" in report.tensor_compatibility.transforms[0].reason.lower()
