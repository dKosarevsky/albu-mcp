# Product Fix Implementation Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a report-only `activation product-fix-implementation-plan` command that converts the first product fix selector output into a concrete TDD plan.

**Architecture:** Create `product_fix_implementation_plan.py` as a pure builder/render module that depends on the first product fix selector. Keep `cli.py` as a thin adapter for argument parsing, stdout formatting, and optional artifact writes.

**Tech Stack:** Python, argparse, pytest, ruff, ty, uv.

---

### Task 1: Blocked Plan Contract

**Files:**
- Create: `src/albumentationsx_mcp/product_fix_implementation_plan.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_product_fix_implementation_plan_cli.py`

- [ ] Write a failing CLI test for empty host and beta records.
- [ ] Verify RED with `uv run pytest tests/test_product_fix_implementation_plan_cli.py::test_activation_product_fix_implementation_plan_blocks_without_selected_fix -q`.
- [ ] Implement the request dataclass, blocked report builder, JSON/Markdown renderers, and CLI registration.
- [ ] Verify GREEN with the same test.

### Task 2: Ready TDD Plan Contract

**Files:**
- Modify: `src/albumentationsx_mcp/product_fix_implementation_plan.py`
- Test: `tests/test_product_fix_implementation_plan_cli.py`

- [ ] Write a failing CLI test with ready host records and three non-blocked beta workflow records.
- [ ] Verify RED with `uv run pytest tests/test_product_fix_implementation_plan_cli.py::test_activation_product_fix_implementation_plan_builds_ready_tdd_plan -q`.
- [ ] Add deterministic phase cards for RED tests, implementation, verification, and merge.
- [ ] Verify GREEN with `uv run pytest tests/test_product_fix_implementation_plan_cli.py -q`.

### Task 3: Artifact Pack And Docs

**Files:**
- Modify: `src/albumentationsx_mcp/product_fix_implementation_plan.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `docs/USAGE.md`
- Modify: `docs/REAL_EVIDENCE_INPUT_CHECKLIST.md`
- Test: `tests/test_product_fix_implementation_plan_cli.py`
- Test: `tests/test_cli_evidence_beta.py`

- [ ] Add a failing CLI test for `--output-dir --format markdown`.
- [ ] Implement `build_product_fix_implementation_plan_artifacts`.
- [ ] Document the new command in usage and real evidence checklist.
- [ ] Run:

```bash
uv run pytest tests/test_product_fix_implementation_plan_cli.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
uv run ruff check src/albumentationsx_mcp/product_fix_implementation_plan.py src/albumentationsx_mcp/cli.py tests/test_product_fix_implementation_plan_cli.py tests/test_cli_evidence_beta.py
uv run ruff format --check src/albumentationsx_mcp/product_fix_implementation_plan.py src/albumentationsx_mcp/cli.py tests/test_product_fix_implementation_plan_cli.py tests/test_cli_evidence_beta.py
uv run ty check
uv run python scripts/check_release_readiness.py
git diff --check
```

