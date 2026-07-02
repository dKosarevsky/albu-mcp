# Real Use Unlock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current blocked evidence path into a shorter real-use operator workflow without fabricating host or beta evidence.

**Architecture:** Keep MCP/domain logic in focused modules and keep CLI handlers thin. Reuse existing host setup, evidence, beta, onboarding, trust, and RC builders; add only orchestration/report builders where the existing surface is too fragmented for an operator.

**Tech Stack:** Python 3.10+, Pydantic, argparse, pytest, ruff, ty, uv, existing Markdown/JSON generated docs.

---

### Task 1: Host Setup Probe v2

**Files:**
- Create: `src/albumentationsx_mcp/host_setup.py`
- Modify: `scripts/check_host_setup_probe.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_real_use_unlock_cli.py`

- [ ] Write a failing CLI test for `albu-mcp host setup-probe --format json`.
- [ ] Move the existing script builder into `host_setup.py` and extend it with `operator_command`, `host_filter`, `blocking_checks`, and host-specific `next_action`.
- [ ] Make the script import and delegate to the domain builder.
- [ ] Add the top-level `host` CLI namespace.
- [ ] Verify targeted tests and commit `feat: add host setup probe cli`.

### Task 2: Evidence Collect Wizard

**Files:**
- Modify: `src/albumentationsx_mcp/evidence.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_real_use_unlock_cli.py`

- [ ] Write a failing CLI test for `albu-mcp evidence collect --host Codex --format json`.
- [ ] Add a no-write collect wizard that combines current gate status, setup probe command, run-session command, session manifest command, validation/import commands, privacy checks, and next actions.
- [ ] Keep `writes_records=false` unless the existing import command is run separately with real reviewer-observed data.
- [ ] Verify targeted tests and commit `feat: add evidence collect wizard`.

### Task 3: First Preview Operator Pack

**Files:**
- Create: `src/albumentationsx_mcp/first_preview.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_real_use_unlock_cli.py`

- [ ] Write a failing CLI test for `albu-mcp preview first-pack --dataset-path ...`.
- [ ] Build a report-only first-preview pack that gives the shortest path from local folder to MCP host calls: smoke check, dataset onboarding, preview request validation, render, compare, feedback, export.
- [ ] Do not render images in the CLI pack; keep it as an operator handoff with bounded-root guidance.
- [ ] Verify targeted tests and commit `feat: add first preview operator pack`.

### Task 4: README Diet

**Files:**
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Test: `tests/test_project_scaffolding.py` or a focused docs test

- [ ] Write a failing docs test that rejects an oversized inline operator CLI list in README and requires links to USAGE/CHANGELOG.
- [ ] Replace the long `Operator CLI` paragraph with a short command cluster and links to detailed docs.
- [ ] Keep the first sentence, badges, quick start, host workflow, capabilities, and verification concise.
- [ ] Verify targeted docs tests and commit `docs: slim readme operator workflow`.

### Task 5: Beta Loop Package and Governed Follow-up

**Files:**
- Modify: `src/albumentationsx_mcp/beta_validation.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `scripts/export_governed_iteration_execution_report.py`
- Modify: `docs/GOVERNED_100_ITERATION_REPORT.md`
- Modify: `docs/USAGE.md`
- Test: `tests/test_real_use_unlock_cli.py`
- Test: `tests/test_governed_iteration_execution_report.py`

- [ ] Write a failing CLI test for `albu-mcp beta loop-pack --output-dir ...`.
- [ ] Build a beta loop pack that writes templates, invite copy, import instructions, privacy checklist, and status summary.
- [ ] Update the governed 100-iteration report with the sixth stopped loop at external real-host/beta gates.
- [ ] Verify full local gate and commit `feat: add beta loop pack`.

### Verification

- [ ] `uv run pytest -q`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check`
- [ ] `uv run python scripts/check_release_readiness.py`
- [ ] `uv build`
