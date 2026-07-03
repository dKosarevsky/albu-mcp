# Real Proof Run 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a no-write `real-proof-run-1` operator surface that moves the project from reusable proof workspaces toward one concrete real-host and beta acquisition run without fabricating evidence.

**Architecture:** Extend the existing `proof_sprint.py` orchestration layer with a focused `real_proof_run_1` report and artifact builder that reuses current proof execution data. Keep `cli.py` as an argparse adapter under `activation real-proof-run`. Update governed iteration reporting to record the tenth external-gate stop after the three requested implementation points.

**Tech Stack:** Python 3.10+, argparse CLI, existing proof/evidence/beta orchestration modules, pytest, ruff, ty, uv.

---

### Task 1: Real Host Proof Run Handoff

**Files:**
- Modify: `src/albumentationsx_mcp/proof_sprint.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_real_proof_run_cli.py`

- [ ] **Step 1: Write the failing test**

Create a test for:

```bash
python -m albumentationsx_mcp activation real-proof-run --host-records <empty-host-json> --beta-records <empty-beta-json> --format json
```

Expected before implementation: argparse exits with status `2`.

- [ ] **Step 2: Implement minimal no-write report**

Add `build_real_proof_run_1(...)` returning:

- `run_status`;
- `writes_records=false`;
- `point_count=3`;
- points `real_host_proof_run`, `beta_acquisition_loop`, `p1_host_onboarding_gate`;
- `next_action=run_real_host_handoff`.

- [ ] **Step 3: Verify and commit**

Run:

```bash
uv run pytest tests/test_real_proof_run_cli.py -q
```

Commit: `feat: add real proof run report`.

### Task 2: Beta Acquisition And P1 Gate Artifacts

**Files:**
- Modify: `src/albumentationsx_mcp/proof_sprint.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `docs/USAGE.md`
- Test: `tests/test_real_proof_run_cli.py`

- [ ] **Step 1: Write the failing artifact test**

Run:

```bash
python -m albumentationsx_mcp activation real-proof-run --output-dir <dir> --format markdown
```

Expected artifacts:

- `real-proof-run-1-index.md`;
- `real-host-proof-run.md`;
- `beta-acquisition-loop.md`;
- `p1-host-onboarding-gate.md`.

- [ ] **Step 2: Implement artifact rendering**

Add `build_real_proof_run_1_artifacts(...)` and Markdown renderers. The host artifact must include `activation execution-workspace`, `evidence session-folder`, and `evidence import-manifest`. The beta artifact must include the official Albumentations MCP docs URL and `beta response-import-dir`. The P1 artifact must keep `implementation_allowed=false` while external gates remain blocked.

- [ ] **Step 3: Update docs and commit**

Document:

```bash
albu-mcp activation real-proof-run --output-dir docs/real-proof-run-1 --format markdown
```

Run:

```bash
uv run pytest tests/test_real_proof_run_cli.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
uv run ruff check src/albumentationsx_mcp/proof_sprint.py src/albumentationsx_mcp/cli.py tests/test_real_proof_run_cli.py
```

Commit: `feat: add real proof run artifacts`.

### Task 3: Governed 100-Iteration Stop

**Files:**
- Modify: `scripts/export_governed_iteration_execution_report.py`
- Modify: `docs/GOVERNED_100_ITERATION_REPORT.md`
- Modify: `tests/test_governed_iteration_execution_report.py`

- [ ] **Step 1: Write failing governed expectations**

Expect:

- `executed_iteration_count == 10`;
- `stopped_at_iteration == 10`;
- `completed_path_count == 50`;
- `completed_plan_point_count == 50`;
- three real-proof-run paths plus the tenth governed stop.

- [ ] **Step 2: Update report builder and regenerate Markdown**

Run:

```bash
uv run python scripts/export_governed_iteration_execution_report.py --output docs/GOVERNED_100_ITERATION_REPORT.md
```

- [ ] **Step 3: Verify and commit**

Run:

```bash
uv run pytest tests/test_real_proof_run_cli.py tests/test_governed_iteration_execution_report.py -q
uv run ruff check .
uv run ruff format --check .
```

Commit: `docs: record real proof run stop`.

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

Push the branch, open a PR, wait for CI, merge, sync `main`, and report the three implemented points plus the governed stop for the requested 100 follow-up iterations.
