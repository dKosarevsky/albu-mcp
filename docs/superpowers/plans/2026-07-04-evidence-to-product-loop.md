# Evidence-to-Product Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a no-write Evidence-to-Product Loop that turns real-host and beta records into one product friction summary, operator artifact pack, and governed stop record.

**Architecture:** Keep the feature in a focused `evidence_product_loop` module that composes existing proof and beta validators instead of duplicating record parsing. The CLI remains a thin adapter that builds request objects, serializes JSON/Markdown/text, and writes optional handoff artifacts. Governance stays in the existing generated 100-iteration report.

**Tech Stack:** Python 3.10-3.13, argparse CLI, dataclasses, pytest subprocess CLI tests, ruff, ty, uv.

---

### Task 1: Product Loop Summary

**Files:**
- Create: `src/albumentationsx_mcp/evidence_product_loop.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_to_product_loop_cli.py`

- [ ] **Step 1: Write the failing CLI JSON test**

Add `test_activation_evidence_product_loop_reports_no_write_friction_summary` with empty host and beta records. Assert the new command is report-only, returns three sections (`real_host_evidence`, `beta_validation`, `product_backlog`), includes blockers for both external gates, and leaves both files unchanged.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
uv run pytest tests/test_evidence_to_product_loop_cli.py::test_activation_evidence_product_loop_reports_no_write_friction_summary -q
```

Expected: fail because `activation evidence-product-loop` is not registered.

- [ ] **Step 3: Implement the minimal summary module and CLI route**

Create `EvidenceProductLoopRequest`, `build_evidence_product_loop`, and Markdown rendering. Add an activation parser and handler for `evidence-product-loop`. Reuse `build_evidence_proof_status`, `validate_beta_validation_records`, and `build_beta_validation_report`.

- [ ] **Step 4: Run focused tests, ruff, and commit**

Run:

```bash
uv run pytest tests/test_evidence_to_product_loop_cli.py::test_activation_evidence_product_loop_reports_no_write_friction_summary -q
uv run ruff check src/albumentationsx_mcp/evidence_product_loop.py src/albumentationsx_mcp/cli.py tests/test_evidence_to_product_loop_cli.py
uv run ruff format --check src/albumentationsx_mcp/evidence_product_loop.py src/albumentationsx_mcp/cli.py tests/test_evidence_to_product_loop_cli.py
git diff --check
```

Commit:

```bash
git add src/albumentationsx_mcp/evidence_product_loop.py src/albumentationsx_mcp/cli.py tests/test_evidence_to_product_loop_cli.py docs/superpowers/plans/2026-07-04-evidence-to-product-loop.md
git commit -m "feat: add evidence product loop"
```

### Task 2: Artifact Pack

**Files:**
- Modify: `src/albumentationsx_mcp/evidence_product_loop.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_to_product_loop_cli.py`

- [ ] **Step 1: Write the failing artifact pack test**

Add `test_activation_evidence_product_loop_writes_operator_artifacts`. Assert `--output-dir --format markdown` writes `evidence-product-loop-index.md`, `real-host-evidence.md`, `beta-validation.md`, and `product-backlog.md`.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
uv run pytest tests/test_evidence_to_product_loop_cli.py::test_activation_evidence_product_loop_writes_operator_artifacts -q
```

Expected: fail because artifact writing for this command is not implemented.

- [ ] **Step 3: Implement artifacts**

Add `build_evidence_product_loop_artifacts`, section renderers, JSON/Markdown extension validation, and `--output-dir` handling in the CLI.

- [ ] **Step 4: Run focused tests, ruff, and commit**

Run:

```bash
uv run pytest tests/test_evidence_to_product_loop_cli.py -q
uv run ruff check src/albumentationsx_mcp/evidence_product_loop.py src/albumentationsx_mcp/cli.py tests/test_evidence_to_product_loop_cli.py
uv run ruff format --check src/albumentationsx_mcp/evidence_product_loop.py src/albumentationsx_mcp/cli.py tests/test_evidence_to_product_loop_cli.py
git diff --check
```

Commit:

```bash
git add src/albumentationsx_mcp/evidence_product_loop.py src/albumentationsx_mcp/cli.py tests/test_evidence_to_product_loop_cli.py
git commit -m "feat: add evidence product artifacts"
```

### Task 3: Governance and Usage

**Files:**
- Modify: `docs/USAGE.md`
- Modify: `scripts/export_governed_iteration_execution_report.py`
- Modify: `docs/GOVERNED_100_ITERATION_REPORT.md`
- Modify: `tests/test_governed_iteration_execution_report.py`
- Modify: `tests/test_cli_evidence_beta.py`

- [ ] **Step 1: Write failing docs/governance tests**

Update tests to expect iteration 15, 73 completed paths/points, `activation evidence-product-loop` in operator usage, and new governed report terms for Evidence-to-Product Summary, Artifact Pack, and the fifteenth stopped 100-iteration loop.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
uv run pytest tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
```

Expected: fail on old counts and missing command mention.

- [ ] **Step 3: Update usage docs and governed report generator**

Add the command to `docs/USAGE.md`, append three completed paths/points, increment counts to 15/73, include `src/albumentationsx_mcp/evidence_product_loop.py` and `tests/test_evidence_to_product_loop_cli.py` in source docs, then regenerate `docs/GOVERNED_100_ITERATION_REPORT.md`.

- [ ] **Step 4: Run focused and full verification, commit**

Run:

```bash
uv run pytest tests/test_evidence_to_product_loop_cli.py tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/check_release_readiness.py
uv build
git diff --check
```

Commit:

```bash
git add docs/USAGE.md scripts/export_governed_iteration_execution_report.py docs/GOVERNED_100_ITERATION_REPORT.md tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py
git commit -m "docs: record evidence product loop stop"
```

## Self-Review

- Spec coverage: the plan covers the three requested product-development points: real host proof closure routing, beta evidence routing, and product simplification into one no-write evidence-to-product loop.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: request, builder, artifact, renderer, CLI command, and tests consistently use `evidence-product-loop`.
