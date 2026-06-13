# AlbumentationsX MCP

Model Context Protocol server for [AlbumentationsX](https://github.com/albumentations-team/AlbumentationsX):
discovering transforms, validating augmentation pipelines, rendering deterministic previews, and exporting reproducible
pipeline specs.

## Scope

This project is intentionally a thin MCP layer around existing AlbumentationsX primitives:

- `albu-spec` is the source of transform metadata, parameter constraints, targets, and docstrings.
- `albumentationsx` remains the execution engine for validation, serialization, and previews.
- the MCP server exposes resources, tools, and prompts with strict typed schemas and bounded local file access.

The server does not execute arbitrary Python, fetch remote images, overwrite datasets, or train models.

## Install

```bash
uv sync --all-extras --dev
```

## Run

```bash
uv run albumentationsx-mcp
```

Claude Desktop or another MCP host can launch it with stdio:

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

## Core Tools

- `search_transforms`: search transform metadata by query, targets, type, and bbox support.
- `get_transform_schema`: inspect a transform schema and constraints.
- `validate_pipeline`: validate a typed pipeline spec before running it.
- `recommend_pipeline`: create a conservative task preset for classification, detection, segmentation, or OCR.
- `adjust_pipeline`: apply structured preview feedback such as `too_noisy` or `too_blurry`.
- `render_preview`: create deterministic local preview artifacts inside an allowed output root.
- `export_pipeline`: export a pipeline as Python, JSON, or YAML.

## Verification

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
```
