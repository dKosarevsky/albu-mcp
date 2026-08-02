# CPU Tensor Compose

AlbumentationsX MCP can check whether a pipeline accepts channel-first CPU `torch.Tensor` targets before an agent
exports integration code. It does not transport live Tensor objects through MCP or execute arbitrary Python.

The upstream implementation is capability-gated: CPU Tensor input is accepted only when every selected transform
declares support for the requested targets and image channel counts. The MCP reads those public runtime capabilities
instead of maintaining a separate transform allowlist.

## Host Workflow

Read `albumentationsx://examples/torch-cpu-compose`. If the host cannot read resources, call
`get_workflow_example` with `example_id="torch-cpu-compose"`.

1. Call `validate_pipeline` with the pipeline, canonical targets, and `input_contract`.
2. Continue only when `tensor_compatibility.status` is `compatible`.
3. Call `export_pipeline` with `output_format="python"` and the same `target` and `input_contract`.

## Validate

`null` dimensions are dynamic. A known channel dimension allows the MCP to check channel-specific transform
capabilities without fixing image height and width.

```json
{
  "pipeline": {
    "transforms": [
      {"name": "NoOp", "p": 1.0}
    ]
  },
  "target": {
    "targets": ["image"]
  },
  "input_contract": {
    "representation": "torch",
    "device": "cpu",
    "requires_grad": false,
    "targets": [
      {"name": "image", "shape": [3, null, null], "dtype": "uint8"}
    ]
  }
}
```

For masks, bboxes, or keypoints, list every spatial target in both `target.targets` and `input_contract.targets`.
Tensor and NumPy spatial targets cannot be mixed at the Compose boundary.

## Interpret The Result

| Status | Meaning | Action |
| --- | --- | --- |
| `compatible` | Every transform accepts the declared Tensor targets and channels. | Export with the same contract. |
| `incompatible` | A boundary rule or transform capability blocks Tensor input. | Follow `issues` and `remediation_actions`, or keep NumPy input. |
| `runtime_unavailable` | The installed AlbumentationsX does not expose the CPU Tensor capability API. | Upgrade after an upstream release includes the feature, then validate again. |

The report includes the installed AlbumentationsX version, per-transform decisions, accepted targets and channels,
machine-readable issue codes, and remediation actions.

## Export

```json
{
  "pipeline": {
    "transforms": [
      {"name": "NoOp", "p": 1.0}
    ]
  },
  "output_format": "python",
  "target": {
    "targets": ["image"]
  },
  "input_contract": {
    "representation": "torch",
    "device": "cpu",
    "requires_grad": false,
    "targets": [
      {"name": "image", "shape": [3, null, null], "dtype": "uint8"}
    ]
  }
}
```

Tensor-aware export is Python-only and fail-closed. The generated handoff:

- imports `torch` and builds the ordinary `A.Compose` pipeline;
- checks type, CPU device, `requires_grad`, dtype, rank, and known shape dimensions;
- passes every declared spatial target to the same Compose call;
- does not add `ToTensorV2` or `ToTensor3D`;
- is generated only after the runtime compatibility check succeeds.

## Boundary Rules

- CPU only; CUDA, MPS, XPU, and other accelerator inputs are rejected.
- `requires_grad` must be false. Device transfer and autograd remain training-code responsibilities.
- Image-like targets are channel first: `C,H,W` for `image` and `C,L,H,W` for `images` or `volume`.
- Image dtypes are `uint8` or `float32`; masks and annotations use their upstream target-specific dtypes.
- Every selected transform branch must declare an accepted CPU Tensor capability.
- Tensor-input pipelines must not contain terminal `ToTensorV2` or `ToTensor3D` transforms.

See the upstream [CPU Tensor Compose pull request](https://github.com/albumentations-team/AlbumentationsX/pull/389)
and [backend migration design](https://github.com/albumentations-team/AlbumentationsX/blob/main/docs/design/torch-cpu-backend-migration.md)
for the current capability and performance policy.
