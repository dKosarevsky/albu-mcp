# Proof Execution Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing combined proof sprint into an execution workspace that guides real host evidence, external beta validation, and gated host-onboarding depth without fabricating records.

**Architecture:** Extend the existing `proof_sprint.py` orchestration module with a second no-write workspace builder that composes the current proof sprint report into operator-facing execution artifacts. Keep `cli.py` as a thin argparse adapter for `activation execution-workspace`. Update governed iteration reporting to record the ninth external-gate stop after the three requested implementation points.

**Tech Stack:** Python 3.10+, argparse CLI, existing proof/evidence/beta domain modules, pytest, ruff, ty, uv.

---

### Task 1: Execution Workspace Command

**Files:**
- Modify: `src/albumentationsx_mcp/proof_sprint.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_proof_execution_workspace_cli.py`

- [ ] **Step 1: Write the failing test**

Create a test that runs:

```bash
python -m albumentationsx_mcp activation execution-workspace --host-records <empty-host-json> --beta-records <empty-beta-json> --format json
```

Expected before implementation: argparse exits with status `2`.

- [ ] **Step 2: Implement the minimal report**

Add `build_proof_execution_workspace(...)` with:

- `workspace_status`;
- `writes_records=false`;
- `step_count=3`;
- steps `execution_workspace`, `real_host_execution`, `beta_execution`;
- `next_action=run_workspace_artifacts`.

- [ ] **Step 3: Verify and commit**

Run:

```bash
uv run pytest tests/test_proof_execution_workspace_cli.py -q
```

Commit: `feat: add proof execution workspace report`.

### Task 2: Real Host And Beta Execution Artifacts

**Files:**
- Modify: `src/albumentationsx_mcp/proof_sprint.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `docs/USAGE.md`
- Test: `tests/test_proof_execution_workspace_cli.py`

- [ ] **Step 1: Write the failing artifact test**

Run:

```bash
python -m albumentationsx_mcp activation execution-workspace --output-dir <dir> --format markdown
```

Expected artifacts:

- `proof-execution-workspace-index.md`;
- `real-host-execution-handoff.md`;
- `beta-execution-handoff.md`;
- `host-onboarding-depth-gate.md`.

- [ ] **Step 2: Implement artifact rendering**

Add `build_proof_execution_workspace_artifacts(...)` and Markdown renderers. The real host artifact must include `activation proof-sprint`, `evidence session-folder`, and `evidence import-manifest`. The beta artifact must include the official Albumentations MCP docs URL and `beta response-import-dir`. The host onboarding artifact must keep `implementation_allowed=false` while external gates remain blocked.

- [ ] **Step 3: Update docs and commit**

Document:

```bash
albu-mcp activation execution-workspace --output-dir docs/proof-execution --format markdown
```

Run:

```bash
uv run pytest tests/test_proof_execution_workspace_cli.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
uv run ruff check src/albumentationsx_mcp/proof_sprint.py src/albumentationsx_mcp/cli.py tests/test_proof_execution_workspace_cli.py
```

Commit: `feat: add proof execution workspace artifacts`.

### Task 3: Governed 100-Iteration Stop

**Files:**
- Modify: `scripts/export_governed_iteration_execution_report.py`
- Modify: `docs/GOVERNED_100_ITERATION_REPORT.md`
- Modify: `tests/test_governed_iteration_execution_report.py`

- [ ] **Step 1: Write failing governed expectations**

Expect:

- `executed_iteration_count == 9`;
- `stopped_at_iteration == 9`;
- `completed_path_count == 46`;
- `completed_plan_point_count == 46`;
- three proof execution paths plus the ninth governed stop.

- [ ] **Step 2: Update report builder and regenerate Markdown**

Run:

```bash
uv run python scripts/export_governed_iteration_execution_report.py --output docs/GOVERNED_100_ITERATION_REPORT.md
```

- [ ] **Step 3: Verify and commit**

Run:

```bash
uv run pytest tests/test_proof_execution_workspace_cli.py tests/test_governed_iteration_execution_report.py -q
uv run ruff check .
uv run ruff format --check .
```

Commit: `docs: record proof execution workspace stop`.

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
