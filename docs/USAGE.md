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
- `manifest.json` with input paths, pipeline JSON, artifact hashes, and timestamps

Use `list_preview_runs` to find recent runs and `get_preview_manifest` to retrieve a manifest by run id.

## Resources

- `albumentationsx://transforms/catalog`: all transform metadata from `albu-spec`.
- `albumentationsx://transforms/{name}`: metadata for one transform.
- `albumentationsx://schemas/pipeline`: JSON Schema for pipeline specs.
- `albumentationsx://feedback-tags`: structured feedback tags accepted by `adjust_pipeline`.
- `albumentationsx://capabilities`: configured roots, preview limits, and exposed tools.
