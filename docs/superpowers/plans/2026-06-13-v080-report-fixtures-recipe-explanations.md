# v0.8 Report Fixtures And Recipe Explanations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic report snapshot coverage with real tiny image fixtures and richer structured recipe explanations for MCP hosts.

**Architecture:** Keep report rendering inside `src/albumentationsx_mcp/reports.py` and recipe advice inside `src/albumentationsx_mcp/recipes.py`. Add test-only fixture builders and checked-in text snapshots under `tests/fixtures/`.

**Tech Stack:** Python 3.10+, Pydantic, Pillow, pytest fixtures and parametrization, ruff, ty, uv.

---

### Task 1: Report Snapshot Fixtures

**Files:**
- Create: `tests/fixtures/report_case.py`
- Create: `tests/fixtures/snapshots/preview_report.md`
- Create: `tests/fixtures/snapshots/preview_report.html`
- Create: `tests/test_report_snapshots.py`
- Modify: `src/albumentationsx_mcp/reports.py`

- [ ] **Step 1: Write failing snapshot tests**

Add tests that create tiny PNG contact sheets, render Markdown and HTML reports, normalize dynamic paths, and compare against snapshot text files. Expected initial failure: Markdown lacks image syntax and HTML lacks `<img>` thumbnails.

- [ ] **Step 2: Run focused tests to confirm RED**

Run: `uv run pytest tests/test_report_snapshots.py -q`

- [ ] **Step 3: Implement richer report rendering**

Update Markdown contact sheet rendering to include image references and HTML rendering to include thumbnail images wrapped in links.

- [ ] **Step 4: Verify and commit**

Run: `uv run pytest tests/test_reports.py tests/test_report_snapshots.py -q`

Run: `uv run ruff check src/albumentationsx_mcp/reports.py tests/test_report_snapshots.py tests/fixtures/report_case.py`

Commit: `test: add report snapshot fixtures`

### Task 2: Structured Recipe Explanations

**Files:**
- Modify: `src/albumentationsx_mcp/models.py`
- Modify: `src/albumentationsx_mcp/recipes.py`
- Modify: `tests/test_recipes.py`

- [ ] **Step 1: Write failing recipe explanation tests**

Assert that `recommend_recipe` returns explanation records for `quality_profile`, `targets`, `feedback_tags`, and `workflow`, including a balanced fallback explanation for unknown tasks.

- [ ] **Step 2: Run focused tests to confirm RED**

Run: `uv run pytest tests/test_recipes.py -q`

- [ ] **Step 3: Add model and implementation**

Add `RecipeExplanation` and populate `RecipeRecommendation.explanations` deterministically.

- [ ] **Step 4: Verify and commit**

Run: `uv run pytest tests/test_recipes.py tests/test_server.py -q`

Run: `uv run ruff check src/albumentationsx_mcp/models.py src/albumentationsx_mcp/recipes.py tests/test_recipes.py`

Commit: `feat: explain recipe recommendations`

### Task 3: Docs, Golden Eval, And Release

**Files:**
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `docs/RECIPES.md`
- Modify: `CHANGELOG.md`
- Modify: `evals/golden_mcp_scenarios.yaml`
- Modify: `scripts/run_golden_evals.py`
- Modify: `pyproject.toml`
- Modify: `server.json`
- Modify: `uv.lock`

- [ ] **Step 1: Extend golden evals**

Verify `recommend_recipe` includes structured explanations and `export_preview_report` includes image references.

- [ ] **Step 2: Update public docs**

Document report thumbnails/snapshots and recipe explanations.

- [ ] **Step 3: Bump version to 0.8.0**

Update project metadata, lockfile, and server metadata.

- [ ] **Step 4: Full verification**

Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run python scripts/run_golden_evals.py`, `uv run python scripts/check_release_version.py v0.8.0`, and `uv build`.

- [ ] **Step 5: Commit, tag, push, publish**

Commit: `chore: release v0.8.0`. Tag `v0.8.0`, push `main` and tag, watch CI/release, dispatch MCP Registry publish, and run PyPI/Registry/uvx smoke checks.
