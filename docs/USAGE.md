# AlbumentationsX MCP Usage

This server is intended for preview-driven augmentation work with a local MCP host. It exposes AlbumentationsX metadata,
pipeline validation, conservative presets, deterministic previews, and reproducible exports without executing arbitrary
Python code.

## Host Configuration

Use `examples/claude_desktop_config.json` as a starting point and replace `/path/to/albu-mcp` with the repository path:

```json
{
  "mcpServers": {
    "albumentationsx": {
      "command": "uv",
      "args": ["run", "albumentationsx-mcp"],
      "cwd": "/path/to/albu-mcp"
    }
  }
}
```

For preview rendering, constrain filesystem access explicitly:

```bash
uv run albumentationsx-mcp \
  --allowed-root /path/to/images \
  --artifact-root /path/to/albu-mcp/artifacts
```

By default, the artifact index keeps the latest 100 preview runs. Set `ALBU_MCP_MAX_PREVIEW_RUNS` to change that
retention limit for long-running MCP hosts.

## Agent Workflow

1. Call `recommend_pipeline` for the target task and intensity.
2. Call `validate_pipeline` before rendering or exporting.
3. Call `explain_pipeline` to identify likely preview risks and feedback tags.
4. Call `render_preview` on a small local image set.
5. Review the generated `contact_sheet` artifact.
6. Call `adjust_pipeline` with tags from `list_feedback_tags`, for example `too_noisy` or `too_distorted`.
7. Re-render, then call `export_pipeline` once the preview set is acceptable.

## Preview Artifacts

Each preview run writes:

- one PNG per input and variant
- `contact_sheet.png` for quick review
- optional overlay PNGs when bboxes, keypoints, or masks are supplied
- optional `overlay_contact_sheet.png` for annotation-aware review
- `manifest.json` with input paths, pipeline JSON, artifact hashes, and timestamps

Use `list_preview_runs` to find recent runs, `get_preview_manifest` to retrieve a manifest by run id,
`delete_preview_run` to remove one run, and `cleanup_preview_runs` to prune older runs.

## Annotation Previews

`render_preview` accepts an optional `annotations` list with one item per `input_paths` entry:

```json
{
  "request": {
    "input_paths": ["/path/to/images/example.png"],
    "annotations": [
      {
        "bboxes": [[4, 5, 20, 24]],
        "bbox_labels": ["object"],
        "keypoints": [[12, 14]],
        "mask_path": "/path/to/images/example-mask.png"
      }
    ],
    "pipeline": {
      "transforms": [{"name": "HorizontalFlip", "p": 1.0}],
      "bbox_params": {"format": "pascal_voc", "label_fields": ["labels"]},
      "keypoint_params": {"format": "xy", "remove_invisible": false}
    },
    "variants_per_image": 2
  }
}
```

Mask paths are resolved through the same `--allowed-root` policy as input images.

## Golden Evals

Run executable MCP scenarios locally before changing tool contracts:

```bash
uv run python scripts/run_golden_evals.py
```

## Resources

- `albumentationsx://transforms/catalog`: all transform metadata from `albu-spec`.
- `albumentationsx://transforms/{name}`: metadata for one transform.
- `albumentationsx://schemas/pipeline`: JSON Schema for pipeline specs.
- `albumentationsx://feedback-tags`: structured feedback tags accepted by `adjust_pipeline`.
- `albumentationsx://capabilities`: configured roots, preview limits, and exposed tools.
