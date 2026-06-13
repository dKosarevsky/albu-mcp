# v0.7 Dataset Reports And Recipes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build dataset-level candidate scoring, visual preview report export, and typed task-aware recipe recommendations for AlbumentationsX MCP.

**Architecture:** Add focused domain modules for dataset scoring, report rendering, and recipe recommendation. Keep `server.py` as a thin adapter that validates inputs, loads manifests/comparisons, and serializes strict Pydantic models.

**Tech Stack:** Python 3.10+, Pydantic strict models, FastMCP, pytest fixtures/parametrization, ruff, ty, uv.

---

### Task 1: Dataset Candidate Scoring

**Files:**
- Create: `src/albumentationsx_mcp/dataset.py`
- Modify: `src/albumentationsx_mcp/models.py`
- Test: `tests/test_dataset.py`

- [ ] **Step 1: Write failing dataset scoring tests**

Create tests that build synthetic `PreviewRunComparison` objects and assert that `score_dataset_preview_candidates()` returns ranked candidates, metric stats, finding counts, and decision guidance.

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `uv run pytest tests/test_dataset.py -q`

Expected: import failure for `albumentationsx_mcp.dataset`.

- [ ] **Step 3: Add strict models**

Add `DatasetMetricStats`, `DatasetFindingCount`, and `DatasetPreviewScore` to `models.py`.

- [ ] **Step 4: Implement dataset scorer**

Create `score_dataset_preview_candidates(comparisons, feedback_tags_by_candidate, accepted_candidate_ids, quality_profile)` in `dataset.py`. Reuse `rank_preview_candidates`, compute candidate metric stats from each comparison quality summary, and count findings by `(severity, code)`.

- [ ] **Step 5: Verify focused tests pass and commit**

Run: `uv run pytest tests/test_dataset.py -q`

Commit: `feat: score dataset preview candidates`

### Task 2: Preview Report Export

**Files:**
- Create: `src/albumentationsx_mcp/reports.py`
- Modify: `src/albumentationsx_mcp/models.py`
- Test: `tests/test_reports.py`

- [ ] **Step 1: Write failing report tests**

Create tests for Markdown and HTML report exports. Use temporary manifest/contact sheet paths and synthetic dataset score data. Assert report artifacts are written under `reports/`, include best candidate, include contact sheet references, and HTML escapes dynamic text.

- [ ] **Step 2: Run focused report tests and verify failure**

Run: `uv run pytest tests/test_reports.py -q`

Expected: import failure for `albumentationsx_mcp.reports`.

- [ ] **Step 3: Add report models and artifact kind**

Extend `ArtifactKind` with `report`. Add `PreviewReportExport` to `models.py`.

- [ ] **Step 4: Implement report export service**

Create `PreviewReportService` with `export_report(...)`. It renders Markdown or HTML, writes the report under `artifact_root/reports/`, and returns a `PreviewReportExport`.

- [ ] **Step 5: Verify focused tests pass and commit**

Run: `uv run pytest tests/test_reports.py -q`

Commit: `feat: export visual preview reports`

### Task 3: Task-Aware Recipe Recommendations

**Files:**
- Create: `src/albumentationsx_mcp/recipes.py`
- Modify: `src/albumentationsx_mcp/models.py`
- Test: `tests/test_recipes.py`

- [ ] **Step 1: Write failing recipe tests**

Parametrize OCR, detection, segmentation, classification, and unknown tasks. Assert the selected quality profile, default targets, workflow tools, feedback tags, and starter pipeline are deterministic.

- [ ] **Step 2: Run focused recipe tests and verify failure**

Run: `uv run pytest tests/test_recipes.py -q`

Expected: import failure for `albumentationsx_mcp.recipes`.

- [ ] **Step 3: Add recipe models**

Add `RecipeInfo` and `RecipeRecommendation` to `models.py`.

- [ ] **Step 4: Implement recipe recommender**

Create `list_recipe_catalog()` and `recommend_recipe(task, intensity, targets)` in `recipes.py`. Use existing `presets.recommend_pipeline` and map aliases to quality profiles and task guidance.

- [ ] **Step 5: Verify focused tests pass and commit**

Run: `uv run pytest tests/test_recipes.py -q`

Commit: `feat: recommend task-aware recipes`

### Task 4: MCP Wiring And Golden Eval

**Files:**
- Modify: `src/albumentationsx_mcp/server.py`
- Modify: `tests/test_server.py`
- Modify: `tests/test_mcp_stdio.py`
- Modify: `evals/golden_mcp_scenarios.yaml`
- Modify: `scripts/run_golden_evals.py`

- [ ] **Step 1: Write failing server/eval tests**

Assert new MCP capabilities include `score_dataset_preview_candidates`, `export_preview_report`, `recommend_recipe`, and `albumentationsx://recipes/catalog`.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `uv run pytest tests/test_server.py tests/test_mcp_stdio.py -q`

Expected: missing tool/resource assertions fail.

- [ ] **Step 3: Wire tools/resources**

Add MCP tools and resource. Keep tool bodies small: read manifests/comparisons, call domain services, return `model_dump(mode="json")`.

- [ ] **Step 4: Extend golden evals**

Update the preview quality scenario to score candidates, export a preview report, and request an OCR recipe.

- [ ] **Step 5: Verify and commit**

Run: `uv run pytest tests/test_server.py tests/test_mcp_stdio.py tests/test_golden_evals.py -q`

Run: `uv run python scripts/run_golden_evals.py`

Commit: `feat: expose dataset reports and recipes over mcp`

### Task 5: Documentation And Release

**Files:**
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `docs/RECIPES.md`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`
- Modify: `server.json`
- Modify: `uv.lock`

- [ ] **Step 1: Update documentation**

Document the new tools and recommended workflow: recipe recommendation, preview rendering, dataset scoring, report export, decision recording, pipeline export.

- [ ] **Step 2: Bump version to 0.7.0**

Update project metadata and lockfile.

- [ ] **Step 3: Run full verification**

Run: `uv run pytest`

Run: `uv run ruff check .`

Run: `uv run ruff format --check .`

Run: `uv run ty check`

Run: `uv run python scripts/run_golden_evals.py`

Run: `uv run python scripts/check_release_version.py v0.7.0`

Run: `uv build`

- [ ] **Step 4: Commit, tag, push, and publish**

Commit: `chore: release v0.7.0`

Tag: `v0.7.0`

Push `main` and tag. Watch CI, release, PyPI smoke, and MCP Registry publish.
