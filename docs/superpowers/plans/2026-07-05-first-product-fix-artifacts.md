# First Product Fix Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add artifact-only `--output-dir` support to `activation first-product-fix`.

**Architecture:** Keep selector logic in `first_product_fix_selector.py`; add artifact builder helpers there and keep
`cli.py` as a thin adapter. Tests exercise the public CLI and temporary host/beta records.

**Tech Stack:** Python, argparse, pytest, ruff, ty, uv.

---

### Task 1: Markdown Artifact Pack

**Files:**
- Modify: `src/albumentationsx_mcp/first_product_fix_selector.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_first_product_fix_selector_cli.py`

- [ ] Add a failing CLI test for blocked records with `--output-dir` and `--format markdown`.
- [ ] Verify RED with `uv run pytest tests/test_first_product_fix_selector_cli.py::test_activation_first_product_fix_writes_blocked_markdown_artifacts -q`.
- [ ] Add `build_first_product_fix_selector_artifacts` and Markdown artifact renderers.
- [ ] Add `--output-dir` parser and CLI write loop.
- [ ] Verify GREEN with the same test.

### Task 2: JSON Ready Artifact Pack

**Files:**
- Modify: `src/albumentationsx_mcp/first_product_fix_selector.py`
- Test: `tests/test_first_product_fix_selector_cli.py`

- [ ] Add a failing CLI test for ready records with `--output-dir` and `--format json`.
- [ ] Verify RED with `uv run pytest tests/test_first_product_fix_selector_cli.py::test_activation_first_product_fix_writes_ready_json_artifacts -q`.
- [ ] Make artifact builder output equivalent JSON payloads.
- [ ] Verify GREEN with `uv run pytest tests/test_first_product_fix_selector_cli.py -q`.

### Task 3: Docs And Verification

**Files:**
- Modify: `docs/USAGE.md`
- Modify: `docs/REAL_EVIDENCE_INPUT_CHECKLIST.md`
- Test: `tests/test_cli_evidence_beta.py`

- [ ] Document `--output-dir docs/first-product-fix`.
- [ ] Add artifact output to the real evidence checklist after the selector command.
- [ ] Run:

```bash
uv run pytest tests/test_first_product_fix_selector_cli.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
uv run ruff check src/albumentationsx_mcp/first_product_fix_selector.py src/albumentationsx_mcp/cli.py tests/test_first_product_fix_selector_cli.py tests/test_cli_evidence_beta.py
uv run ruff format --check src/albumentationsx_mcp/first_product_fix_selector.py src/albumentationsx_mcp/cli.py tests/test_first_product_fix_selector_cli.py tests/test_cli_evidence_beta.py
uv run ty check
uv run python scripts/check_release_readiness.py
git diff --check
```

