# Real Adoption Cycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a no-write Real Adoption Cycle that makes the next product step explicit: collect real host evidence, collect beta signal, then select the first product fix only after external gates open.

**Architecture:** Add a focused `real_adoption_cycle` module that composes existing evidence proof, beta validation, and product-depth backlog concepts. The CLI stays a thin `activation real-adoption-cycle` adapter with JSON/Markdown/text output and optional artifact writing. Governance updates remain generated through the existing governed iteration report.

**Tech Stack:** Python 3.10-3.13, argparse CLI, dataclasses, pytest subprocess tests, ruff, ty, uv.

---

### Task 1: Real Adoption Cycle Summary

**Files:**
- Create: `src/albumentationsx_mcp/real_adoption_cycle.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_real_adoption_cycle_cli.py`

- [ ] **Step 1: Write the failing CLI JSON test**

Add `test_activation_real_adoption_cycle_reports_three_no_write_lanes` with empty host and beta records. Assert the command is report-only, returns three lanes (`real_evidence_intake`, `beta_signal_sprint`, `first_product_fix_gate`), blocks implementation until both external gates open, and does not modify record files.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
uv run pytest tests/test_real_adoption_cycle_cli.py::test_activation_real_adoption_cycle_reports_three_no_write_lanes -q
```

Expected: fail because `activation real-adoption-cycle` is not registered.

- [ ] **Step 3: Implement the minimal summary module and CLI route**

Create `RealAdoptionCycleRequest`, `build_real_adoption_cycle`, and Markdown rendering. Reuse `build_evidence_proof_status`, `validate_beta_validation_records`, and `build_beta_validation_report`.

- [ ] **Step 4: Run focused tests, ruff, and commit**

Run:

```bash
uv run pytest tests/test_real_adoption_cycle_cli.py::test_activation_real_adoption_cycle_reports_three_no_write_lanes -q
uv run ruff check src/albumentationsx_mcp/real_adoption_cycle.py src/albumentationsx_mcp/cli.py tests/test_real_adoption_cycle_cli.py
uv run ruff format --check src/albumentationsx_mcp/real_adoption_cycle.py src/albumentationsx_mcp/cli.py tests/test_real_adoption_cycle_cli.py
git diff --check
```

Commit:

```bash
git add src/albumentationsx_mcp/real_adoption_cycle.py src/albumentationsx_mcp/cli.py tests/test_real_adoption_cycle_cli.py docs/superpowers/plans/2026-07-05-real-adoption-cycle.md
git commit -m "feat: add real adoption cycle"
```

### Task 2: Real Adoption Artifact Pack

**Files:**
- Modify: `src/albumentationsx_mcp/real_adoption_cycle.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_real_adoption_cycle_cli.py`

- [ ] **Step 1: Write the failing artifact test**

Add `test_activation_real_adoption_cycle_writes_operator_artifacts`. Assert `--output-dir --format markdown` writes `real-adoption-cycle-index.md`, `real-evidence-intake.md`, `beta-signal-sprint.md`, and `first-product-fix-gate.md`.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
uv run pytest tests/test_real_adoption_cycle_cli.py::test_activation_real_adoption_cycle_writes_operator_artifacts -q
```

Expected: fail because artifact writing for this command is not implemented.

- [ ] **Step 3: Implement artifacts**

Add `build_real_adoption_cycle_artifacts`, lane renderers, JSON/Markdown extension validation, and `--output-dir` handling in the CLI.

- [ ] **Step 4: Run focused tests, ruff, and commit**

Run:

```bash
uv run pytest tests/test_real_adoption_cycle_cli.py -q
uv run ruff check src/albumentationsx_mcp/real_adoption_cycle.py src/albumentationsx_mcp/cli.py tests/test_real_adoption_cycle_cli.py
uv run ruff format --check src/albumentationsx_mcp/real_adoption_cycle.py src/albumentationsx_mcp/cli.py tests/test_real_adoption_cycle_cli.py
git diff --check
```

Commit:

```bash
git add src/albumentationsx_mcp/real_adoption_cycle.py src/albumentationsx_mcp/cli.py tests/test_real_adoption_cycle_cli.py
git commit -m "feat: add real adoption artifacts"
```

### Task 3: Governance and Usage

**Files:**
- Modify: `docs/USAGE.md`
- Modify: `scripts/export_governed_iteration_execution_report.py`
- Modify: `docs/GOVERNED_100_ITERATION_REPORT.md`
- Modify: `tests/test_governed_iteration_execution_report.py`
- Modify: `tests/test_cli_evidence_beta.py`

- [ ] **Step 1: Write failing docs/governance tests**

Update tests to expect iteration 16, 76 completed paths/points, `activation real-adoption-cycle` in operator usage, and new governed report terms for Real Adoption Summary, Artifact Pack, and the sixteenth stopped 100-iteration loop.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
uv run pytest tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
```

Expected: fail on old counts and missing command mention.

- [ ] **Step 3: Update usage docs and governed report generator**

Add the command to `docs/USAGE.md`, append three completed paths/points, increment counts to 16/76, include `src/albumentationsx_mcp/real_adoption_cycle.py` and `tests/test_real_adoption_cycle_cli.py` in source docs, then regenerate `docs/GOVERNED_100_ITERATION_REPORT.md`.

- [ ] **Step 4: Run focused and full verification, commit**

Run:

```bash
uv run pytest tests/test_real_adoption_cycle_cli.py tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
uv run pytest -q
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
git commit -m "docs: record real adoption stop"
```

## Self-Review

- Spec coverage: the plan covers the three requested development points: real evidence intake, beta signal collection, and a first product fix gate.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: request, builder, artifacts, renderer, CLI command, and tests consistently use `real-adoption-cycle`.
