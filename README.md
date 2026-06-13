# AlbumentationsX MCP

Model Context Protocol server for [AlbumentationsX](https://github.com/albumentations-team/AlbumentationsX):
discovering transforms, validating augmentation pipelines, rendering deterministic previews, and exporting reproducible
pipeline specs.

<!-- mcp-name: io.github.dKosarevsky/albu-mcp -->

[![CI](https://github.com/dKosarevsky/albu-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/dKosarevsky/albu-mcp/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10--3.13-blue)](pyproject.toml)
[![MCP](https://img.shields.io/badge/MCP-AlbumentationsX-green)](docs/USAGE.md)

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

After the Python MCP server package is published to PyPI, it can be launched without cloning:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
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
- `explain_pipeline`: summarize likely effects, preview risks, and useful feedback tags.
- `list_feedback_tags`: list the structured feedback contract used by `adjust_pipeline`.
- `render_preview`: create deterministic local preview artifacts inside an allowed output root.
- `list_preview_runs`: list recent preview manifests recorded under the artifact root.
- `get_preview_manifest`: read one recorded preview manifest by run id.
- `delete_preview_run`: delete one preview run and its artifacts.
- `cleanup_preview_runs`: prune older preview runs beyond a retention count.
- `export_pipeline`: export a pipeline as Python, JSON, or YAML.

`render_preview` supports optional bboxes, keypoints, and mask paths for annotation overlay previews.

See [docs/USAGE.md](docs/USAGE.md) for an end-to-end MCP host workflow, [docs/RELEASE.md](docs/RELEASE.md) for the
package and MCP Registry release process, [server.json](server.json) for public discovery metadata, and
[evals/golden_mcp_scenarios.yaml](evals/golden_mcp_scenarios.yaml) for executable MCP scenarios.

## Verification

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv build
```
