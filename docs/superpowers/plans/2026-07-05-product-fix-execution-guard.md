# Product Fix Execution Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a no-write execution guard that converts a ready product-fix TDD plan into a scoped branch handoff.

**Architecture:** Add one focused domain module on top of `product_fix_implementation_plan`, wire it into `activation` CLI, and document the new command. Keep evidence gates and selected-fix logic in the existing modules.

**Tech Stack:** Python 3.10+, argparse CLI, dataclasses, pytest, ruff, ty, uv.

---

### Task 1: CLI Contract Tests

**Files:**
- Create: `tests/test_product_fix_execution_guard_cli.py`

- [ ] **Step 1: Write blocked CLI test**

Add a test that writes empty host and beta records, runs:

```bash
python -m albumentationsx_mcp activation product-fix-execution-guard --host Codex --host-records <path> --beta-records <path> --format json
```

Assert `guard_status == "blocked_until_tdd_plan"`, `execution_allowed is False`, `branch_scaffold is None`, and both input files are unchanged.

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_product_fix_execution_guard_cli.py::test_activation_product_fix_execution_guard_blocks_without_tdd_plan -q
```

Expected: fail because the command does not exist.

- [ ] **Step 3: Write ready CLI test**

Add a test with passing host evidence and beta records containing a `review_agent_v3_gap` signal. Assert the JSON output contains `guard_status == "ready_for_branch_scaffold"`, a branch name, allowed source/test files, red/green/verification commands, and checklist items.

- [ ] **Step 4: Write artifact CLI test**

Run the command with `--output-dir <tmp>/product-fix-execution-guard --format markdown`. Assert exactly three files are written and host/beta records are unchanged.

### Task 2: Domain Module

**Files:**
- Create: `src/albumentationsx_mcp/product_fix_execution_guard.py`

- [ ] **Step 1: Add request dataclass and builder**

Create `ProductFixExecutionGuardRequest` with host, host records path, beta records path, and release tag. Implement `build_product_fix_execution_guard()` by calling `build_product_fix_implementation_plan()`.

- [ ] **Step 2: Implement blocked response**

When `implementation_allowed` is false, return a report with `guard_status`, `execution_allowed`, `branch_scaffold: None`, `execution_checklist: []`, copied blocked reasons, source plan, and next commands.

- [ ] **Step 3: Implement ready response**

When implementation is allowed, derive a deterministic branch name:

```text
codex/product-fix-<product_area>-<triage_bucket>
```

Split `suggested_files` into `allowed_source_files` and `allowed_test_files`, copy phase commands into red/green/verification groups, and create checklist items for branch, red tests, implementation, verification, PR, and merge.

- [ ] **Step 4: Add JSON and Markdown renderers**

Provide `render_product_fix_execution_guard_json()` and `render_product_fix_execution_guard_markdown()` following the existing product-fix module style.

- [ ] **Step 5: Add artifact pack builder**

Provide `build_product_fix_execution_guard_artifacts()` with index, branch scaffold, and execution checklist artifact payloads.

### Task 3: CLI Wiring And Docs

**Files:**
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `docs/USAGE.md`
- Modify: `docs/REAL_EVIDENCE_INPUT_CHECKLIST.md`
- Modify: `tests/test_cli_evidence_beta.py`

- [ ] **Step 1: Import the guard module functions in `cli.py`**

- [ ] **Step 2: Add `product-fix-execution-guard` activation parser**

Use the same arguments as `product-fix-implementation-plan`.

- [ ] **Step 3: Add handler**

For `--output-dir`, write artifact files. For `--format json/markdown`, render via the module. For text, print guard status and execution flag.

- [ ] **Step 4: Document usage**

Add the plain JSON command and artifact command to usage docs and the documentation assertion test.

### Task 4: Verification And Shipping

**Files:**
- All touched files

- [ ] **Step 1: Focused tests**

Run:

```bash
uv run pytest tests/test_product_fix_execution_guard_cli.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
```

- [ ] **Step 2: Quality gates**

Run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/check_release_readiness.py
```

- [ ] **Step 3: Build and full tests**

Run:

```bash
uv build
uv run pytest -q
```

- [ ] **Step 4: Commit, push, PR, CI, merge**

Commit docs separately from implementation if practical. Push the branch, open a PR, wait for CI, merge, fast-forward local `main`, and rerun focused post-merge checks.
