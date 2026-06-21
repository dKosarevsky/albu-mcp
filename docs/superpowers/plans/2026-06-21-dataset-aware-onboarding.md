# Dataset-Aware Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add read-only dataset structure profiling to `plan_dataset_onboarding`.

**Architecture:** Keep `onboarding.py` as the public orchestration boundary and add a focused dataset profiling helper for layout and annotation signals. The MCP report gets one optional `dataset_structure` model while existing preview and remediation contracts remain backward compatible.

**Tech Stack:** Python 3.10+, Pydantic strict models, pathlib, pytest fixtures, ruff, ty, existing snapshot/export scripts.

---

### Task 1: Add Dataset Structure Profile Tests

**Files:**
- Modify: `tests/test_onboarding.py`

- [ ] **Step 1: Write failing tests**

Add tests that create:

```text
dataset/
  train/cat/a.png
  train/dog/b.png
  val/cat/c.png
  labels/a.txt
  annotations/instances_train.json
```

The tests should assert that `build_dataset_onboarding_report(...).dataset_structure` includes:

- `class_directories`
- `split_directories`
- `yolo_labels`
- `coco_manifest`
- class counts for `cat` and `dog`
- split counts for `train` and `val`
- annotation format entries for YOLO and COCO

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
uv run pytest tests/test_onboarding.py -q
```

Expected: fails because `DatasetOnboardingReport` does not expose `dataset_structure`.

### Task 2: Implement Focused Dataset Profiling

**Files:**
- Create: `src/albumentationsx_mcp/dataset_profile.py`
- Modify: `src/albumentationsx_mcp/onboarding.py`

- [ ] **Step 1: Add strict profile models**

Create models for class directories, splits, annotation formats, and the aggregate profile.

- [ ] **Step 2: Implement read-only detection**

Implement a helper that accepts `dataset_path` and `image_paths`, then computes:

- likely class directory counts from image parent folders while ignoring split names;
- split image counts for `train`, `val`, `valid`, `validation`, and `test`;
- YOLO label files under `labels/**/*.txt`;
- COCO JSON files with `images`, `annotations`, and `categories` keys.

- [ ] **Step 3: Wire profile into onboarding report**

Call the helper only after path checks pass and image inventory is available. Add `dataset_structure` to the returned
report.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_onboarding.py -q
uv run ruff check src/albumentationsx_mcp/dataset_profile.py src/albumentationsx_mcp/onboarding.py tests/test_onboarding.py
```

Expected: tests pass and ruff passes.

### Task 3: Update MCP Contracts and Docs

**Files:**
- Modify: `scripts/export_output_contracts.py`
- Modify: `tests/fixtures/snapshots/output_contracts.json`
- Modify: `docs/USAGE.md`
- Modify: `docs/RECIPES.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Regenerate output contracts**

Run:

```bash
uv run python scripts/export_output_contracts.py
uv run python scripts/check_contract_snapshots.py
```

Expected: snapshots are fresh and include `dataset_structure`.

- [ ] **Step 2: Document host behavior**

Document that `plan_dataset_onboarding` now detects common dataset layouts and annotation signals. Keep README concise
and put detail in `docs/USAGE.md` and `docs/RECIPES.md`.

- [ ] **Step 3: Verify docs and contract tests**

Run:

```bash
uv run pytest tests/test_output_contract_snapshots.py tests/test_onboarding.py -q
uv run ruff check .
uv run ty check
```

Expected: all selected checks pass.

### Task 4: Commit and Push

**Files:**
- All modified files from Tasks 1-3.

- [ ] **Step 1: Full verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv build
git diff --check
```

Expected: all commands pass.

- [ ] **Step 2: Commit and push**

Run:

```bash
git add docs/superpowers/specs/2026-06-21-dataset-aware-onboarding-design.md docs/superpowers/plans/2026-06-21-dataset-aware-onboarding.md src/albumentationsx_mcp/dataset_profile.py src/albumentationsx_mcp/onboarding.py tests/test_onboarding.py scripts/export_output_contracts.py tests/fixtures/snapshots/output_contracts.json docs/USAGE.md docs/RECIPES.md README.md CHANGELOG.md
git commit -m "feat: add dataset-aware onboarding profile"
git push origin main
```
