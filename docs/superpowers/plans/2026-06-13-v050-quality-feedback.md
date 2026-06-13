# v0.5 Quality Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add richer local quality scoring, annotation-aware preview comparison, and a persisted tuning decision journal.

**Architecture:** Keep FastMCP tools as thin adapters. Put metric logic in `quality.py`, preview observation collection in `preview.py`, typed contracts in `models.py`, and persisted tuning decisions in `tuning.py`.

**Tech Stack:** Python 3.11+, Pydantic, NumPy, Pillow, FastMCP, pytest, ruff, ty, uv.

---

### Task 1: Plan And Design Commit

**Files:**
- Create: `docs/superpowers/specs/2026-06-13-v050-quality-feedback-design.md`
- Create: `docs/superpowers/plans/2026-06-13-v050-quality-feedback.md`

- [ ] Add design and implementation plan documents.
- [ ] Run `git add docs/superpowers/specs/2026-06-13-v050-quality-feedback-design.md docs/superpowers/plans/2026-06-13-v050-quality-feedback.md`.
- [ ] Run `git commit -m "docs: plan v0.5 quality feedback improvements"`.

### Task 2: Richer Quality Metrics

**Files:**
- Modify: `src/albumentationsx_mcp/models.py`
- Modify: `src/albumentationsx_mcp/quality.py`
- Modify: `tests/test_quality.py`

- [ ] Add failing tests for saturation, colorfulness, entropy, clipping, and quality findings.
- [ ] Run `uv run pytest tests/test_quality.py -q` and verify the new tests fail before implementation.
- [ ] Add typed quality finding models and aggregate fields.
- [ ] Implement metric collection and deterministic findings without new runtime dependencies.
- [ ] Run `uv run pytest tests/test_quality.py -q`.
- [ ] Run `uv run ruff check src/albumentationsx_mcp/quality.py tests/test_quality.py`.
- [ ] Run `git commit -m "feat: add richer quality scoring"`.

### Task 3: Annotation-Aware Preview Comparison

**Files:**
- Modify: `src/albumentationsx_mcp/models.py`
- Modify: `src/albumentationsx_mcp/preview.py`
- Modify: `src/albumentationsx_mcp/quality.py`
- Modify: `tests/test_annotation_preview.py`
- Modify: `tests/test_quality.py`

- [ ] Add failing tests for persisted annotation observations and comparison annotation deltas.
- [ ] Run the focused tests and verify they fail before implementation.
- [ ] Record per-variant bbox, keypoint, and mask observations in preview manifests.
- [ ] Aggregate baseline/candidate annotation observations in `compare_manifest_quality`.
- [ ] Run focused preview and quality tests.
- [ ] Commit with `git commit -m "feat: add annotation-aware preview quality"`.

### Task 4: Persisted Tuning Decision Journal

**Files:**
- Modify: `src/albumentationsx_mcp/models.py`
- Modify: `src/albumentationsx_mcp/tuning.py`
- Modify: `src/albumentationsx_mcp/server.py`
- Create: `tests/test_tuning_store.py`
- Modify: `tests/test_server.py`
- Modify: `tests/test_mcp_stdio.py`

- [ ] Add failing tests for recording, listing, and score-ranked tuning decisions.
- [ ] Run focused tests and verify the new store/tool expectations fail before implementation.
- [ ] Implement `TuningDecisionStore`, decision models, and quality score derivation.
- [ ] Expose `record_tuning_decision` and `list_tuning_decisions` MCP tools.
- [ ] Run focused tuning/server/stdio tests.
- [ ] Commit with `git commit -m "feat: persist tuning decisions"`.

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

- [ ] Add golden eval coverage for `record_tuning_decision` and `list_tuning_decisions`.
- [ ] Document new fields and tools in user-facing docs.
- [ ] Bump version to `0.5.0`.
- [ ] Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run python scripts/run_golden_evals.py`, and `uv build`.
- [ ] Commit with `git commit -m "chore: release v0.5.0"`.
- [ ] Tag and push `v0.5.0`.
- [ ] Watch CI/release/registry workflows and verify PyPI, Registry, and `uvx` smoke.
