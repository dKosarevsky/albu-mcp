# v0.7 Dataset Reports And Recipes Design

## Goal

AlbumentationsX MCP should help an agent move from one-off preview tuning to a repeatable dataset-level decision loop: score several candidate preview runs, produce a portable visual report, and recommend a task-aware recipe before rendering.

## Scope

This release adds three user-facing capabilities:

- Dataset-level candidate scoring across multiple preview runs.
- Markdown and HTML preview reports that include contact sheet references and tuning decision context.
- Typed recipe recommendations that combine a starter pipeline, quality profile, workflow tools, and task-specific feedback tags.

The scope stays local and deterministic. Reports reference local preview artifacts already written by the server. No remote uploads, image hosting, external models, or browser automation are introduced.

## Architecture

The implementation keeps the existing clean boundary: MCP tools are thin adapters, while scoring, reporting, and recipe selection live in focused domain modules.

- `dataset.py` aggregates `PreviewRunComparison` objects, reuses `rank_preview_candidates`, and exposes a typed dataset score.
- `reports.py` renders report content and writes report artifacts under the configured artifact root.
- `recipes.py` selects a task profile, calls the existing conservative preset builder, and returns a typed recipe contract.
- `models.py` defines strict Pydantic contracts for MCP-facing responses.
- `server.py` wires tools and resources only.

This avoids pushing more business logic into `server.py` and lets tests cover the domain behavior without starting MCP.

## Dataset Scoring

The dataset scorer accepts one baseline run and up to 20 candidate run ids through MCP. It compares every candidate with the existing quality pipeline, ranks candidates with the existing ranking helper, and then adds cross-candidate aggregates:

- per-metric minimum, maximum, and mean for candidate quality aggregates;
- finding counts by code and severity;
- best candidate id and decision guidance;
- a bounded set of top findings for quick review.

The score is deterministic. Equal candidate scores keep the existing stable tie-breaker by candidate run id.

## Reports

The report exporter supports `markdown` and `html`.

Reports include:

- baseline run id, quality profile, candidate count, and best candidate;
- baseline and candidate contact sheet paths;
- ranked candidate table with score, risk, export readiness, next tool, and feedback tags;
- dataset metric ranges and finding counts;
- optional persisted tuning decisions for the involved candidates.

Markdown reports use plain file paths and image references. HTML reports escape all dynamic text and include local `file://` links for contact sheets. Both formats are written under `artifact_root/reports/` and returned as an `ArtifactRef`.

## Recipes

The recipe recommender is a higher-level advisory layer over existing presets. It maps common task aliases to:

- quality profile (`ocr`, `detection`, `segmentation`, `classification`, or `balanced`);
- default targets;
- recommended preview workflow tools;
- feedback tags likely to matter for that task;
- a conservative starter pipeline from `recommend_pipeline`.

It does not replace `recommend_pipeline`; it gives agents a complete workflow envelope so they pick the right profile and next tools before rendering.

## Error Handling

Input limits remain bounded:

- candidate ids are capped at 20;
- unknown recipe tasks fall back to `balanced`;
- report formats are restricted to `markdown` and `html`;
- report artifacts are written under the configured artifact root only.

Existing manifest id validation continues to protect preview manifest reads.

## Testing

Tests are added at the domain layer first:

- dataset scoring over synthetic comparisons;
- report rendering and artifact creation with local paths;
- recipe recommendation for OCR, detection, segmentation, classification, and fallback tasks;
- server smoke coverage for new tools/resources.

The release gate remains: `pytest`, `ruff`, `ruff format --check`, `ty`, golden MCP evals, version check, build, GitHub CI, release workflow, PyPI smoke, and MCP Registry publish.
