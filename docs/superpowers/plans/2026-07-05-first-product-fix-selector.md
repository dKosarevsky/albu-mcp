# First Product Fix Selector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a no-write, records-driven selector that chooses the first product fix only after real adoption gates are green.

**Architecture:** Create a focused package module for selector logic and a thin `activation first-product-fix` CLI adapter. Reuse `build_real_adoption_cycle` and `build_beta_validation_report`; keep product fix packet mapping local and deterministic.

**Tech Stack:** Python, argparse, pytest, ruff, ty, uv.

---

### Task 1: Blocked Selector Contract

**Files:**
- Create: `src/albumentationsx_mcp/first_product_fix_selector.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_first_product_fix_selector_cli.py`

- [ ] Write a failing CLI test for empty host and beta records.
- [ ] Verify RED with `uv run pytest tests/test_first_product_fix_selector_cli.py::test_activation_first_product_fix_blocks_without_external_evidence -q`.
- [ ] Implement minimal selector module and CLI registration.
- [ ] Verify GREEN with the same test.

### Task 2: Ready Selector And Packet

**Files:**
- Modify: `src/albumentationsx_mcp/first_product_fix_selector.py`
- Test: `tests/test_first_product_fix_selector_cli.py`

- [ ] Write a failing CLI test with closed `Codex` and `Claude Code` host records plus three beta workflow records.
- [ ] Verify RED with `uv run pytest tests/test_first_product_fix_selector_cli.py::test_activation_first_product_fix_selects_ready_beta_fix -q`.
- [ ] Implement deterministic decision ordering and product fix packet mapping.
- [ ] Verify GREEN with `uv run pytest tests/test_first_product_fix_selector_cli.py -q`.

### Task 3: Docs And Verification

**Files:**
- Modify: `docs/USAGE.md`
- Modify: `docs/REAL_EVIDENCE_INPUT_CHECKLIST.md`
- Test: `tests/test_cli_evidence_beta.py`

- [ ] Add `albu-mcp activation first-product-fix` to operator usage.
- [ ] Add it as the final command after green gate in the real evidence checklist.
- [ ] Update docs expectations.
- [ ] Run:

```bash
uv run pytest tests/test_first_product_fix_selector_cli.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
uv run ruff check src/albumentationsx_mcp/first_product_fix_selector.py src/albumentationsx_mcp/cli.py tests/test_first_product_fix_selector_cli.py
uv run ruff format --check src/albumentationsx_mcp/first_product_fix_selector.py src/albumentationsx_mcp/cli.py tests/test_first_product_fix_selector_cli.py
uv run ty check
uv run python scripts/check_release_readiness.py
git diff --check
```
