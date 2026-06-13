# Next MCP Development Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add quality-aware preview comparison, tuning summaries, richer workflow recipes, and eval coverage.

**Architecture:** Keep image quality analysis in a focused domain module. Keep `PreviewService` as the orchestration
boundary and expose only typed model additions through MCP tools.

**Tech Stack:** Python 3.10-3.13, Pydantic, Pillow, NumPy, pytest, ruff, ty, uv, MCP FastMCP.

---

### Task 1: Quality-Aware Preview Comparison

**Files:**
- Create: `src/albumentationsx_mcp/quality.py`
- Modify: `src/albumentationsx_mcp/models.py`
- Modify: `src/albumentationsx_mcp/preview.py`
- Test: `tests/test_quality.py`
- Test: `tests/test_artifacts.py`

- [ ] Write failing tests for brightness, contrast, sharpness, and pairwise deltas on synthetic images.
- [ ] Implement `ImageQualityMetrics` collection with Pillow/NumPy only.
- [ ] Add optional `quality_summary` and `quality_warnings` to `PreviewRunComparison`.
- [ ] Have `PreviewService.compare_preview_runs` enrich comparisons from local image artifacts.
- [ ] Run focused tests and commit `feat: add quality-aware preview comparisons`.

### Task 2: Tuning Session Summaries

**Files:**
- Create: `src/albumentationsx_mcp/tuning.py`
- Modify: `src/albumentationsx_mcp/models.py`
- Modify: `src/albumentationsx_mcp/server.py`
- Test: `tests/test_tuning.py`
- Test: `tests/test_server.py`

- [ ] Write failing tests for summarizing baseline, candidate, feedback tags, quality deltas, and export readiness.
- [ ] Implement a pure tuning summary builder from `PreviewRunComparison` and feedback tags.
- [ ] Expose a `summarize_tuning_session` MCP tool.
- [ ] Run focused tests and commit `feat: summarize preview tuning sessions`.

### Task 3: Workflow Profiles And Recipes

**Files:**
- Modify: `src/albumentationsx_mcp/workflows.py`
- Modify: `docs/USAGE.md`
- Create: `docs/RECIPES.md`
- Test: `tests/test_workflows.py`
- Test: `tests/test_project_scaffolding.py`

- [ ] Write failing tests for task-specific workflow profile names and recipe docs.
- [ ] Add compact profiles for classification, detection, segmentation, OCR, and annotation review.
- [ ] Document host-facing recipes without changing runtime safety boundaries.
- [ ] Run focused tests and commit `docs: add workflow recipes and task profiles`.

### Task 4: Golden Evals And Release

**Files:**
- Modify: `evals/golden_mcp_scenarios.yaml`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`
- Modify: `server.json`
- Modify: `uv.lock`
- Test: `tests/test_golden_evals.py`
- Test: `tests/test_release_version.py`

- [ ] Add eval assertions for quality comparison and tuning summary outputs.
- [ ] Run full local gate: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`,
  `uv run python scripts/run_golden_evals.py`, and `uv build`.
- [ ] Bump version, commit `chore: release v0.4.0`, tag `v0.4.0`, push, and verify PyPI plus MCP Registry.
