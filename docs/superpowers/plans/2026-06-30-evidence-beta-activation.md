# Evidence Beta Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the existing blocked RC evidence and beta gates into operator-ready activation workflows without fabricating real-host evidence.

**Architecture:** Keep pure report builders in domain modules (`evidence.py`, `beta_validation.py`, `trust.py`, `rc_reopen.py`) and wire them through thin CLI adapters in `cli.py`. Generated packets remain report-only unless an explicit recording command is used with reviewer-observed evidence.

**Tech Stack:** Python, argparse, Pydantic, pytest, uv, ruff, ty.

---

### Task 1: Host Operator Packet Export

**Files:**
- Modify: `src/albumentationsx_mcp/evidence.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_activation_cli.py`

- [ ] Write a failing CLI test for `albu-mcp evidence operator-packet --host Codex --output-dir <tmp> --format markdown`.
- [ ] Implement a pure packet renderer that writes no evidence records and includes host setup, smoke call, artifact checklist, and recording command.
- [ ] Add the CLI command and keep JSON output available.
- [ ] Verify the targeted test passes.

### Task 2: Evidence Import Validation

**Files:**
- Modify: `src/albumentationsx_mcp/evidence.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_activation_cli.py`

- [ ] Write a failing test for `albu-mcp evidence validate-import` rejecting passed evidence without reviewer confirmation or replay artifacts.
- [ ] Add a pure validation function that never writes records.
- [ ] Wire CLI text/json output.
- [ ] Verify import validation tests pass.

### Task 3: Beta Intake Wizard

**Files:**
- Modify: `src/albumentationsx_mcp/beta_validation.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_activation_cli.py`

- [ ] Write a failing test for `albu-mcp beta intake-wizard --workflow-id noisy_preview_tuning`.
- [ ] Build a privacy-safe intake wizard payload with participant prompt, redaction checklist, acceptance rubric, and recording command.
- [ ] Wire CLI text/json output.
- [ ] Verify beta intake tests pass.

### Task 4: Trust Gate Dashboard

**Files:**
- Modify: `src/albumentationsx_mcp/trust.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_activation_cli.py`

- [ ] Write a failing test for `albu-mcp trust dashboard --format markdown`.
- [ ] Add a unified dashboard builder with gate cards, blocked reasons, and next operator command.
- [ ] Wire text/json/markdown output without mutating release state.
- [ ] Verify trust dashboard tests pass.

### Task 5: RC Candidate Packet

**Files:**
- Modify: `src/albumentationsx_mcp/rc_reopen.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `docs/GOVERNED_100_ITERATION_REPORT.md`
- Test: `tests/test_activation_cli.py`

- [ ] Write a failing test for `albu-mcp rc candidate-packet --format json`.
- [ ] Add a pure candidate packet builder that explains whether publish commands are allowed and which gates still block.
- [ ] Wire CLI text/json/markdown output.
- [ ] Update the governed iteration report to show the 100 requested follow-up iterations stop at the same real evidence and beta gates until external records exist.
- [ ] Run targeted and full verification before reporting completion.
