# AlbumentationsX MCP

Model Context Protocol server for [AlbumentationsX](https://github.com/albumentations-team/AlbumentationsX):
discovering transforms, validating augmentation pipelines, rendering deterministic previews, and exporting reproducible
pipeline specs.

<!-- mcp-name: io.github.dKosarevsky/albu-mcp -->

[![CI](https://github.com/dKosarevsky/albu-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/dKosarevsky/albu-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/albumentationsx-mcp)](https://pypi.org/project/albumentationsx-mcp/)
[![Python](https://img.shields.io/badge/python-3.10--3.13-blue)](pyproject.toml)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-active-green)](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp)

## Scope

This project is intentionally a thin MCP layer around existing AlbumentationsX primitives:

- `albu-spec` is the source of transform metadata, parameter constraints, targets, and docstrings.
- `albumentationsx` remains the execution engine for validation, serialization, and previews.
- the MCP server exposes resources, tools, and prompts with strict typed schemas and bounded local file access.

The server does not execute arbitrary Python, fetch remote images, overwrite datasets, or train models.

## Install

Run the published MCP server without cloning:

```bash
uvx --from albumentationsx-mcp albumentationsx-mcp
```

For local development:

```bash
uv sync --all-extras --dev
```

## Run

```bash
uv run albumentationsx-mcp
```

Claude Desktop or another JSON-configured MCP host can launch a local checkout with stdio:

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

Installed from PyPI:

```json
{
  "mcpServers": {
    "albumentationsx": {
      "command": "uvx",
      "args": ["--from", "albumentationsx-mcp", "albumentationsx-mcp"]
    }
  }
}
```

See [examples/claude_desktop_pypi_config.json](examples/claude_desktop_pypi_config.json),
[examples/cursor_mcp_config.json](examples/cursor_mcp_config.json), and
[examples/codex_mcp_config.toml](examples/codex_mcp_config.toml) for copyable host snippets.

## Core Tools

- `search_transforms`: search transform metadata by query, targets, type, and bbox support.
- `get_transform_schema`: inspect a transform schema and constraints.
- `validate_pipeline`: validate a typed pipeline spec before running it.
- `recommend_pipeline`: create a conservative task preset for classification, detection, segmentation, or OCR.
- `adjust_pipeline`: apply structured preview feedback such as `too_noisy` or `too_blurry`.
- `explain_pipeline`: summarize likely effects, preview risks, and useful feedback tags.
- `list_feedback_tags`: list the structured feedback contract used by `adjust_pipeline`.
- `render_preview`: create deterministic local preview artifacts inside an allowed output root.
- `render_preview_batch`: create deterministic multi-image preview contact sheets using the same request schema.
- `compare_preview_runs`: compare two preview manifests before choosing feedback tags or exporting a pipeline.
- `list_preview_runs`: list recent preview manifests recorded under the artifact root.
- `get_preview_manifest`: read one recorded preview manifest by run id.
- `delete_preview_run`: delete one preview run and its artifacts.
- `cleanup_preview_runs`: prune older preview runs beyond a retention count.
- `export_pipeline`: export a pipeline as Python, JSON, or YAML.

`render_preview` and `render_preview_batch` support optional bboxes, keypoints, and mask paths for annotation overlay
previews. Preview manifests include an agent-legible `summary` block with input counts, seeds, transform names, artifact
counts, contact sheets, and warnings.

## What Changed In 0.2

- PyPI and MCP Registry publishing are automated with release version guardrails and post-release smoke checks.
- `render_preview_batch` produces batch previews and contact sheets for multi-image review.
- `compare_preview_runs` summarizes baseline and candidate manifests to compare preview runs before choosing feedback tags.
- Preview manifests include reproducibility summaries for seeds, transforms, artifact counts, and contact sheets.
- agent workflow resources and prompts guide preview tuning, annotation review, feedback adjustment, and final export.

## Demo Workflow

1. Use `recommend_pipeline` and `validate_pipeline` for a conservative baseline.
2. Call `render_preview_batch` on a small local image set.
3. Adjust with structured feedback such as `too_noisy` or `too_distorted`.
4. Render the candidate preview batch with the same inputs.
5. Call `compare_preview_runs` before accepting the candidate.
6. Export the accepted pipeline with `export_pipeline`.

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
