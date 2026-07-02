# Combined Proof Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one report-only combined proof sprint that coordinates real host evidence, beta validation, and host onboarding depth without fabricating external evidence.

**Architecture:** Add a focused `proof_sprint.py` domain orchestrator that composes existing `activation`, `evidence`, `beta_validation`, and `host_setup` reports. Keep `cli.py` as an adapter that parses arguments, renders JSON/Markdown/text, and optionally writes artifact files. Update governed iteration reporting to record the eighth external-gate stop instead of running blind follow-up iterations.

**Tech Stack:** Python 3.10+, argparse CLI, Pydantic-backed domain models already present in the project, pytest, ruff, ty, uv.

---

### Task 1: Real Host Evidence Sprint Report

**Files:**
- Create: `src/albumentationsx_mcp/proof_sprint.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_combined_proof_sprint_cli.py`

- [ ] **Step 1: Write failing CLI test**

Add a test that runs:

```bash
python -m albumentationsx_mcp activation proof-sprint --host-records <empty-host-json> --beta-records <empty-beta-json> --format json
```

Expected failure before implementation: argparse rejects `proof-sprint`.

- [ ] **Step 2: Implement minimal report**

Add `build_combined_proof_sprint(...)` that returns:

- `sprint_status`;
- `writes_records=false`;
- `point_count=3`;
- one `real_host_evidence_sprint` point with `evidence session-folder`, `evidence import-manifest`, and `evidence close-host` next commands.

- [ ] **Step 3: Run targeted test and commit**

Run:

```bash
uv run pytest tests/test_combined_proof_sprint_cli.py -q
```

Commit: `feat: add combined proof sprint report`.

### Task 2: Beta Validation and Host Onboarding Pack

**Files:**
- Modify: `src/albumentationsx_mcp/proof_sprint.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `docs/USAGE.md`
- Test: `tests/test_combined_proof_sprint_cli.py`

- [ ] **Step 1: Write failing artifact test**

Add a test for:

```bash
python -m albumentationsx_mcp activation proof-sprint --output-dir <dir> --format markdown
```

Expected artifacts:

- `combined-proof-sprint-index.md`;
- `real-host-evidence-sprint.md`;
- `beta-validation-sprint.md`;
- `host-onboarding-depth-sprint.md`.

- [ ] **Step 2: Implement artifact rendering**

Add `build_combined_proof_sprint_artifacts(...)` and Markdown rendering helpers. The beta point must use the official docs URL, beta loop pack command, and response import commands. The host onboarding point must stay blocked until beta/P0 gates open and must point at setup-probe and blocked evidence recovery.

- [ ] **Step 3: Update usage docs and commit**

Document `albu-mcp activation proof-sprint --output-dir docs/proof-sprint --format markdown` as a report-only helper.

Run:

```bash
uv run pytest tests/test_combined_proof_sprint_cli.py -q
uv run ruff check src/albumentationsx_mcp/proof_sprint.py src/albumentationsx_mcp/cli.py tests/test_combined_proof_sprint_cli.py
```

Commit: `feat: add combined proof sprint artifacts`.

### Task 3: Governed 100-Iteration Stop

**Files:**
- Modify: `scripts/export_governed_iteration_execution_report.py`
- Modify: `docs/GOVERNED_100_ITERATION_REPORT.md`
- Modify: `tests/test_governed_iteration_execution_report.py`

- [ ] **Step 1: Write failing governed report expectations**

Update tests to expect:

- `executed_iteration_count == 8`;
- `stopped_at_iteration == 8`;
- `completed_path_count == 42`;
- `completed_plan_point_count == 42`;
- three proof sprint paths plus the eighth governed stop.

- [ ] **Step 2: Update report builder and regenerate Markdown**

Add the new proof sprint source file and tests to `source_docs`. Regenerate:

```bash
uv run python scripts/export_governed_iteration_execution_report.py --output docs/GOVERNED_100_ITERATION_REPORT.md
```

- [ ] **Step 3: Verify and commit**

Run:

```bash
uv run pytest tests/test_combined_proof_sprint_cli.py tests/test_governed_iteration_execution_report.py -q
uv run ruff check .
uv run ruff format --check .
```

Commit: `docs: record combined proof sprint stop`.

### Final Gate

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/check_release_readiness.py
uv build
```

Then push, open PR, wait for CI, merge, sync `main`, and report the completed three points plus the governed stop for the requested 100 follow-up iterations.
