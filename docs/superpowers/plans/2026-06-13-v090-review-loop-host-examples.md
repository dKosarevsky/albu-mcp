# v0.9 Review Loop And Host Examples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add concrete-example preview feedback persistence, host example resources, golden eval coverage, and a v0.9.0 release.

**Architecture:** Keep feedback persistence in a new `review.py` domain module and strict contracts in `models.py`.
Keep `server.py` as a thin adapter that validates preview manifest bounds, then delegates to the store. Keep host examples
as read-only workflow metadata in `workflows.py`.

**Tech Stack:** Python 3.10+, Pydantic, pytest fixtures and parametrization, ruff, ty, uv, FastMCP stdio golden evals.

---

### Task 1: Preview Feedback Store

**Files:**
- Modify: `src/albumentationsx_mcp/models.py`
- Create: `src/albumentationsx_mcp/review.py`
- Create: `tests/test_review.py`

- [ ] **Step 1: Write failing store tests**

Add tests that record negative feedback for `image_index=7`, `variant_index=0`, assert newest-first listing, aggregate
feedback tags, accepted filtering, and the validation rule that negative feedback needs tags.

Run: `uv run pytest tests/test_review.py -q`

Expected: import failure for `albumentationsx_mcp.review`.

- [ ] **Step 2: Add strict models**

Add `PreviewFeedbackRecord`, `PreviewFeedbackList`, and `PreviewFeedbackInput` contracts in `models.py`.

- [ ] **Step 3: Implement store**

Implement `PreviewFeedbackStore.record_feedback(...)` and `PreviewFeedbackStore.list_feedback(...)` in `review.py`.

- [ ] **Step 4: Verify and commit**

Run:

```bash
uv run pytest tests/test_review.py -q
uv run ruff check src/albumentationsx_mcp/models.py src/albumentationsx_mcp/review.py tests/test_review.py
uv run ty check src/albumentationsx_mcp/models.py src/albumentationsx_mcp/review.py tests/test_review.py
```

Commit: `feat: persist preview example feedback`

### Task 2: MCP Tools And Host Example Resources

**Files:**
- Modify: `src/albumentationsx_mcp/server.py`
- Modify: `src/albumentationsx_mcp/workflows.py`
- Modify: `tests/test_server.py`
- Modify: `tests/test_workflows.py`

- [ ] **Step 1: Write failing server/resource tests**

Assert that tools include `record_preview_feedback` and `list_preview_feedback`, capabilities list those tools, and
resources include `albumentationsx://examples/review-loop` plus `albumentationsx://examples/report-handoff`.

Run:

```bash
uv run pytest tests/test_server.py tests/test_workflows.py -q
```

Expected: missing tools/resources.

- [ ] **Step 2: Add host example metadata**

Add `HostExample` and `HostExampleStep` models plus `list_host_examples()` and `get_host_example(name)` in `workflows.py`.

- [ ] **Step 3: Wire MCP resources and tools**

Instantiate `PreviewFeedbackStore` in `server.py`. Register:

- `record_preview_feedback(run_id, image_index, variant_index, feedback_tags, note, accepted)`
- `list_preview_feedback(run_id=None, limit=20, accepted_only=False)`
- `albumentationsx://examples/review-loop`
- `albumentationsx://examples/report-handoff`

Validate bounds from manifest `summary.input_count` and `summary.variants_per_image`.

- [ ] **Step 4: Verify and commit**

Run:

```bash
uv run pytest tests/test_server.py tests/test_workflows.py tests/test_review.py -q
uv run ruff check src/albumentationsx_mcp/server.py src/albumentationsx_mcp/workflows.py tests/test_server.py tests/test_workflows.py
uv run ty check src/albumentationsx_mcp/server.py src/albumentationsx_mcp/workflows.py tests/test_server.py tests/test_workflows.py
```

Commit: `feat: expose preview feedback tools`

### Task 3: Golden Eval And Documentation

**Files:**
- Modify: `scripts/run_golden_evals.py`
- Modify: `evals/golden_mcp_scenarios.yaml`
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `docs/RECIPES.md`

- [ ] **Step 1: Extend golden eval**

Add scenario flags that record feedback for example 8 variant 1 with `too_noisy:high`, list feedback by run id, and use
the returned tag to call `adjust_pipeline`.

Run: `uv run python scripts/run_golden_evals.py`

Expected before implementation: MCP tool not found.

- [ ] **Step 2: Document the review loop**

Document the two new tools and host example resources in README and usage docs.

- [ ] **Step 3: Verify and commit**

Run:

```bash
uv run python scripts/run_golden_evals.py
uv run pytest tests/test_golden_evals.py tests/test_mcp_stdio.py -q
uv run ruff check scripts/run_golden_evals.py
uv run ty check scripts/run_golden_evals.py
```

Commit: `test: cover concrete preview feedback loop`

### Task 4: v0.9.0 Release

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`
- Modify: `server.json`
- Modify: `uv.lock`

- [ ] **Step 1: Bump version metadata**

Update package and server metadata to `0.9.0` and add changelog notes.

- [ ] **Step 2: Full verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv run python scripts/check_release_version.py v0.9.0
uv build
```

- [ ] **Step 3: Commit, tag, push, and publish**

Commit: `chore: release v0.9.0`

Tag: `v0.9.0`

Push `main` and tag, watch CI and release workflows, dispatch MCP Registry publish, then verify PyPI JSON, MCP Registry
metadata, PyPI Simple index, and `uvx --from albumentationsx-mcp==0.9.0 albumentationsx-mcp --help`.
