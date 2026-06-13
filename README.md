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

Public MCP tool, resource, prompt, and metadata changes follow the
[compatibility policy](docs/COMPATIBILITY.md) and are guarded by contract snapshots.

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
- `recommend_recipe`: return a task-aware starter pipeline, quality profile, feedback tags, explanations, and next MCP tools.
- `adjust_pipeline`: apply structured preview feedback such as `too_noisy` or `too_blurry`.
- `explain_pipeline`: summarize likely effects, preview risks, and useful feedback tags.
- `list_feedback_tags`: list the structured feedback contract used by `adjust_pipeline`.
- `list_quality_profiles`: list task-aware quality profiles for balanced, classification, detection, segmentation, and OCR review.
- `render_preview`: create deterministic local preview artifacts inside an allowed output root.
- `render_preview_batch`: create deterministic multi-image preview contact sheets using the same request schema.
- `compare_preview_runs`: compare two preview manifests before choosing feedback tags or exporting a pipeline.
- `summarize_tuning_session`: summarize quality findings, feedback tags, score, risk, and export readiness.
- `rank_preview_candidates`: rank several candidate preview runs against one baseline.
- `score_dataset_preview_candidates`: score a candidate set across dataset-level metrics, findings, and ranking.
- `record_preview_feedback`: persist user feedback for one concrete preview example and variant.
- `list_preview_feedback`: list concrete preview feedback and aggregate tags for the next adjustment.
- `record_tuning_decision`: persist a local accepted or rejected tuning decision.
- `list_tuning_decisions`: list local tuning decisions newest-first or score-ranked.
- `export_tuning_report`: export persisted tuning decisions as Markdown or JSON.
- `export_preview_report`: export Markdown or HTML reports with contact sheets, ranking, metrics, decisions, and concrete
  feedback.
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

## What Changed In 0.3

- `adjust_pipeline` accepts optional feedback severity suffixes such as `too_noisy:low`, `too_noisy:medium`, and
  `too_noisy:high`.
- `compare_preview_runs` returns `suggested_feedback_tags` for candidate transforms that deserve visual review.
- Suggested tags are review candidates only; the user still chooses feedback after inspecting contact sheets.

## What Changed In 0.4

- `compare_preview_runs` includes local `quality_summary` metrics for preview image artifacts.
- `summarize_tuning_session` explains baseline-to-candidate feedback, quality deltas, and export readiness.
- task workflow profiles and [docs/RECIPES.md](docs/RECIPES.md) guide classification, detection, segmentation, and OCR
  MCP host sessions.

## What Changed In 0.5

- `quality_summary` now includes saturation, colorfulness, entropy, clipping, and deterministic quality findings.
- Annotation previews record bbox, keypoint, and mask retention observations in preview manifests.
- `compare_preview_runs` includes `annotation_summary` when annotation observations are available.
- `summarize_tuning_session` returns `quality_score`, `quality_risk`, and structured `quality_findings`.
- `record_tuning_decision` and `list_tuning_decisions` provide a local JSON-backed tuning decision journal.

## What Changed In 0.6

- Added task-aware quality profiles for balanced, classification, detection, segmentation, and OCR review.
- Added `rank_preview_candidates` to choose between multiple candidate preview runs.
- Added `export_tuning_report` for Markdown or JSON handoff from the local tuning decision journal.
- Extended golden MCP evals to cover two-candidate ranking and report export.

## What Changed In 0.7

- Added `recommend_recipe` for task-aware workflow envelopes around conservative starter pipelines.
- Added `score_dataset_preview_candidates` for dataset-level candidate metrics and finding counts.
- Added `export_preview_report` for Markdown or HTML visual handoff with contact sheets and decision context.
- Exposed `albumentationsx://recipes/catalog` for recipe discovery by MCP hosts.
- Extended golden MCP evals to cover recipes, dataset scoring, and preview report export.

## What Changed In 0.8

- `recommend_recipe` now returns structured explanations for profile selection, targets, feedback tags, and workflow.
- `export_preview_report` now embeds Markdown image refs or HTML thumbnails for contact sheet artifacts.
- Report snapshot tests use deterministic tiny PNG fixtures to lock visual handoff output.
- Golden MCP evals verify recipe explanations and preview report image markup.

## What Changed In 0.9

- Added `record_preview_feedback` and `list_preview_feedback` for concrete example/variant feedback.
- Added host example resources for the preview feedback loop and visual report handoff.
- Golden MCP evals now cover the "example 8 is too noisy" review path through stdio.

## What Changed In 0.10

- `export_preview_report` now includes matching concrete preview feedback records in Markdown and HTML handoffs.
- Golden MCP evals verify that recorded feedback note, target, and tags appear in the visual preview report.
- v1 readiness is defined around stable public MCP contracts, schema snapshots, and a compatibility policy.

## V1 Readiness

The next major milestone should be `v1.0.0` once public tool/resource names, response fields, and host workflows are
frozen. Before cutting v1, add contract snapshot checks for MCP schemas, document compatibility/deprecation rules, and
run a final docs pass over README, usage, recipes, and release automation.

## Demo Workflow

1. Use `recommend_recipe` to choose the starter pipeline, quality profile, feedback tags, explanations, and next tools.
2. Call `validate_pipeline` for the recommended pipeline.
3. Call `render_preview_batch` on a small local image set.
4. Adjust with structured feedback such as `too_noisy`, `too_noisy:high`, or `too_distorted`.
5. Render one or more candidate preview batches with the same inputs.
6. Call `compare_preview_runs` before accepting a candidate and inspect `quality_summary.findings`.
7. Call `record_preview_feedback` when the user points to a concrete example such as "example 8 is too noisy".
8. Call `list_preview_feedback` and reuse `aggregated_feedback_tags` for the next `adjust_pipeline` call.
9. Call `rank_preview_candidates` and `score_dataset_preview_candidates` with the matching quality profile.
10. Call `record_tuning_decision` for accepted or rejected candidates.
11. Call `export_preview_report` for visual handoff with contact sheet thumbnails and concrete feedback,
    `export_tuning_report` for decision history, then `export_pipeline`.

See [docs/USAGE.md](docs/USAGE.md) for an end-to-end MCP host workflow, [docs/RECIPES.md](docs/RECIPES.md) for
task-specific host recipes, [docs/DEMO.md](docs/DEMO.md) for a generated preview comparison demo,
[CHANGELOG.md](CHANGELOG.md) for release notes, [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) for public contract
rules, [docs/RELEASE.md](docs/RELEASE.md) for the package and MCP Registry release process, [server.json](server.json)
for public discovery metadata, and
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
