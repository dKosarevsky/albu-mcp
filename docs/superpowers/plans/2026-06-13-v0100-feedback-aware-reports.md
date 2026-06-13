# v0.10 Feedback-Aware Preview Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Include concrete preview feedback records in exported Markdown and HTML preview reports, then release v0.10.0.

**Architecture:** Keep feedback storage in `review.py` and rendering in `reports.py`. `server.py` only joins matching
feedback records to report export inputs. Golden evals verify the behavior through the stdio MCP server.

**Tech Stack:** Python 3.10+, Pydantic, pytest, ruff, ty, uv, FastMCP stdio golden evals.

---

### Task 1: Report Rendering With Feedback Records

**Files:**
- Modify: `src/albumentationsx_mcp/reports.py`
- Modify: `tests/test_reports.py`

- [ ] **Step 1: Write failing report tests**

Add Markdown and HTML report tests that pass `PreviewFeedbackRecord` entries and assert note, tag, review target, and
recommended next tool appear in the rendered content.

Run: `uv run pytest tests/test_reports.py -q`

Expected: failure because `export_report` does not accept `feedback_records`.

- [ ] **Step 2: Implement report sections**

Add optional `feedback_records` to `PreviewReportService.export_report`, `_render_markdown_report`, and
`_render_html_report`. Render a "Concrete Preview Feedback" section in both formats.

- [ ] **Step 3: Verify and commit**

Run:

```bash
uv run pytest tests/test_reports.py tests/test_report_snapshots.py -q
uv run ruff check src/albumentationsx_mcp/reports.py tests/test_reports.py
uv run ty check src/albumentationsx_mcp/reports.py tests/test_reports.py
```

Commit: `feat: include preview feedback in reports`

### Task 2: MCP Report Export Integration

**Files:**
- Modify: `src/albumentationsx_mcp/server.py`
- Modify: `scripts/run_golden_evals.py`
- Modify: `evals/golden_mcp_scenarios.yaml`
- Modify: `tests/test_golden_evals.py`

- [ ] **Step 1: Write failing golden eval assertions**

Add `assert_preview_report_feedback: true` to the existing quality scenario and assert the runner checks for the recorded
note and tag in the exported preview report.

Run: `uv run pytest tests/test_golden_evals.py::test_golden_eval_assets_are_present -q`

Expected: failure until the runner asserts feedback content.

- [ ] **Step 2: Wire matching feedback into reports**

Add a helper in `server.py` that lists feedback for baseline and candidate run ids and passes the records to
`PreviewReportService.export_report`.

- [ ] **Step 3: Verify and commit**

Run:

```bash
uv run python scripts/run_golden_evals.py
uv run pytest tests/test_golden_evals.py tests/test_mcp_stdio.py tests/test_server.py -q
uv run ruff check src/albumentationsx_mcp/server.py scripts/run_golden_evals.py tests/test_golden_evals.py
uv run ty check src/albumentationsx_mcp/server.py scripts/run_golden_evals.py tests/test_golden_evals.py
```

Commit: `test: cover feedback-aware preview reports`

### Task 3: Docs And v0.10.0 Release

**Files:**
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `docs/RECIPES.md`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`
- Modify: `server.json`
- Modify: `uv.lock`

- [ ] **Step 1: Document feedback-aware reports and v1 criteria**

Update public docs to say preview reports include concrete feedback records and that v1 follows after a contract
stability pass.

- [ ] **Step 2: Bump version metadata**

Update package and server metadata to `0.10.0`.

- [ ] **Step 3: Full verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv run python scripts/check_release_version.py v0.10.0
uv build
```

- [ ] **Step 4: Commit, tag, push, and publish**

Commit: `chore: release v0.10.0`

Tag: `v0.10.0`

Push `main` and tag, watch CI/release workflows, dispatch MCP Registry publish, and verify PyPI, MCP Registry, Simple
index, and `uvx --from albumentationsx-mcp==0.10.0 albumentationsx-mcp --help`.
