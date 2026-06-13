# v0.6 Candidate Ranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-candidate preview ranking, task-aware quality profiles, and exportable tuning decision reports.

**Architecture:** Put profile thresholds in `quality.py`, ranking in a new `ranking.py`, report rendering in `tuning.py`, and keep `server.py` as a thin adapter over these services.

**Tech Stack:** Python 3.11+, Pydantic, NumPy, Pillow, FastMCP, pytest, ruff, ty, uv.

---

### Task 1: Plan And Design Commit

**Files:**
- Create: `docs/superpowers/specs/2026-06-13-v060-candidate-ranking-design.md`
- Create: `docs/superpowers/plans/2026-06-13-v060-candidate-ranking.md`

- [ ] Add design and implementation plan documents.
- [ ] Run `git add docs/superpowers/specs/2026-06-13-v060-candidate-ranking-design.md docs/superpowers/plans/2026-06-13-v060-candidate-ranking.md`.
- [ ] Run `git commit -m "docs: plan v0.6 candidate ranking improvements"`.

### Task 2: Quality Profiles

**Files:**
- Modify: `src/albumentationsx_mcp/models.py`
- Modify: `src/albumentationsx_mcp/quality.py`
- Modify: `tests/test_quality.py`

- [ ] Add failing tests for `list_quality_profiles` and OCR/detection/segmentation profile behavior.
- [ ] Run `uv run pytest tests/test_quality.py -q` and verify the new tests fail before implementation.
- [ ] Add typed profile metadata and profile-aware thresholds.
- [ ] Run `uv run pytest tests/test_quality.py -q`.
- [ ] Run `uv run ruff check src/albumentationsx_mcp/quality.py src/albumentationsx_mcp/models.py tests/test_quality.py`.
- [ ] Run `uv run ty check src/albumentationsx_mcp/quality.py src/albumentationsx_mcp/models.py tests/test_quality.py`.
- [ ] Commit with `git commit -m "feat: add task-aware quality profiles"`.

### Task 3: Candidate Ranking

**Files:**
- Create: `src/albumentationsx_mcp/ranking.py`
- Modify: `src/albumentationsx_mcp/models.py`
- Modify: `src/albumentationsx_mcp/preview.py`
- Modify: `src/albumentationsx_mcp/server.py`
- Create: `tests/test_ranking.py`
- Modify: `tests/test_server.py`
- Modify: `tests/test_mcp_stdio.py`

- [ ] Add failing ranking tests for deterministic ordering, top findings, and best candidate id.
- [ ] Run focused tests and verify failure before implementation.
- [ ] Implement ranking models and `rank_preview_candidates`.
- [ ] Add `quality_profile` to preview comparison flow and expose MCP tool `rank_preview_candidates`.
- [ ] Run focused ranking/server/stdio tests.
- [ ] Commit with `git commit -m "feat: rank preview candidates"`.

### Task 4: Tuning Reports

**Files:**
- Modify: `src/albumentationsx_mcp/models.py`
- Modify: `src/albumentationsx_mcp/tuning.py`
- Modify: `src/albumentationsx_mcp/server.py`
- Modify: `tests/test_tuning_store.py`
- Modify: `tests/test_server.py`
- Modify: `tests/test_mcp_stdio.py`

- [ ] Add failing tests for markdown and JSON report export from persisted tuning decisions.
- [ ] Run focused tests and verify failure before implementation.
- [ ] Implement `TuningDecisionReport` and `TuningDecisionStore.export_report`.
- [ ] Expose MCP tool `export_tuning_report`.
- [ ] Run focused tuning/server/stdio tests.
- [ ] Commit with `git commit -m "feat: export tuning decision reports"`.

### Task 5: Docs, Golden Evals, Release

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

- [ ] Extend golden evals to render and rank two candidates, record a decision, and export a report.
- [ ] Document new tools and quality profile behavior.
- [ ] Bump version to `0.6.0`.
- [ ] Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run python scripts/run_golden_evals.py`, `uv run python scripts/check_release_version.py v0.6.0`, and `uv build`.
- [ ] Commit with `git commit -m "chore: release v0.6.0"`.
- [ ] Tag and push `v0.6.0`.
- [ ] Watch CI/release/registry workflows and verify PyPI, Registry, and `uvx` smoke.
