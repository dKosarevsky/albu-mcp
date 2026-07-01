# Intake Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add release-safe intake automation around the existing real evidence, beta validation, trust, and RC gates.

**Architecture:** Keep mutation paths explicit and narrow. New bundle/review commands write artifacts only; record writes remain limited to existing evidence import and beta import commands. Cross-cutting artifact assembly lives in small orchestration modules instead of pushing more logic into CLI handlers.

**Tech Stack:** Python 3.10-3.13, argparse CLI, Pydantic models, pytest, ruff, ty, uv.

---

### Task 1: Intake Bundle

**Files:**
- Create: `src/albumentationsx_mcp/intake.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_intake_automation_cli.py`

- [ ] Write a failing CLI test for `albu-mcp intake bundle`.
- [ ] Implement artifact assembly from existing runbook, fixture pack, import checklist, beta templates, and release owner packet builders.
- [ ] Add top-level `intake` CLI dispatch and write artifacts to `--output-dir`.
- [ ] Run the focused test and commit.

### Task 2: Evidence Session Manifest

**Files:**
- Modify: `src/albumentationsx_mcp/evidence.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_intake_automation_cli.py`

- [ ] Write a failing CLI test for session manifest template and validation.
- [ ] Add Pydantic manifest schema plus no-write validation through existing artifact import validation.
- [ ] Add `evidence session-manifest` and `evidence validate-manifest`.
- [ ] Run the focused test and commit.

### Task 3: Beta Response Directory Import

**Files:**
- Modify: `src/albumentationsx_mcp/beta_validation.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_intake_automation_cli.py`

- [ ] Write a failing CLI test for importing all `*-beta-response.json` files in a directory.
- [ ] Add directory loading, privacy validation, and canonical record import.
- [ ] Add `beta response-import-dir`.
- [ ] Run the focused test and commit.

### Task 4: Release Owner Review Pack

**Files:**
- Create: `src/albumentationsx_mcp/release_review.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_intake_automation_cli.py`

- [ ] Write a failing CLI test for `rc review-pack`.
- [ ] Assemble trust dashboard, gate transition, RC candidate packet, release owner packet, and index artifacts.
- [ ] Add the CLI writer.
- [ ] Run the focused test and commit.

### Task 5: RC Go Check and Governed Loop

**Files:**
- Modify: `src/albumentationsx_mcp/rc_reopen.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `scripts/export_governed_iteration_execution_report.py`
- Test: `tests/test_intake_automation_cli.py`, `tests/test_cli_evidence_beta.py`, `tests/test_governed_iteration_execution_report.py`

- [ ] Write a failing CLI test for `rc go-check`.
- [ ] Add a report-only RC go/no-go report.
- [ ] Document the new commands and update governed 100-iteration state.
- [ ] Run full verification and publish the PR.
