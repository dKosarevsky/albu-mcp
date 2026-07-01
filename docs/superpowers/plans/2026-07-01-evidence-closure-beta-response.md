# Evidence Closure Beta Response Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the remaining RC blockers to one operator path for real-host evidence capture and privacy-safe beta response recording.

**Architecture:** Add pure report builders for activation, evidence closure, privacy checks, and beta response intake. Keep CLI code thin: argparse parses inputs, domain modules build reports or records, CLI renders JSON/Markdown/text.

**Tech Stack:** Python, argparse, Pydantic, pytest, uv, ruff, ty.

---

### Task 1: Activation Command Center

**Files:**
- Create: `src/albumentationsx_mcp/activation.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_closure_cli.py`

- [ ] Write a failing CLI test for `albu-mcp activation command-center --format json`.
- [ ] Implement `build_activation_command_center` as a report-only aggregator over trust dashboard, P0 evidence execution packets, beta intake wizards, and RC candidate packet.
- [ ] Wire `activation command-center` in CLI with text/json/markdown output.
- [ ] Verify targeted tests pass.

### Task 2: P0 Evidence Packet Bundle

**Files:**
- Modify: `src/albumentationsx_mcp/evidence.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_closure_cli.py`

- [ ] Write a failing CLI test for `albu-mcp evidence packet-bundle --output-dir <tmp> --format markdown`.
- [ ] Implement a pure P0 bundle renderer that uses existing host operator packet artifacts for `Codex` and `Claude Code`.
- [ ] Wire the CLI command and write a bundle index plus host packet files.
- [ ] Verify targeted tests pass.

### Task 3: Evidence Import Checklist

**Files:**
- Modify: `src/albumentationsx_mcp/evidence.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_closure_cli.py`

- [ ] Write a failing CLI test for `albu-mcp evidence import-checklist --host Codex --format json`.
- [ ] Implement a pure checklist builder with required fields, reviewer confirmation policy, validate command, and import command.
- [ ] Wire text/json/markdown output.
- [ ] Verify targeted tests pass.

### Task 4: Artifact Privacy Doctor

**Files:**
- Modify: `src/albumentationsx_mcp/evidence.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_closure_cli.py`

- [ ] Write a failing CLI test for `albu-mcp evidence privacy-doctor --format json`.
- [ ] Implement privacy checks for private local paths, file URLs, synthetic-only evidence, and missing replay artifact refs.
- [ ] Wire text/json output.
- [ ] Verify targeted tests pass.

### Task 5: Beta Response Validation and Import

**Files:**
- Modify: `src/albumentationsx_mcp/beta_validation.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `docs/GOVERNED_100_ITERATION_REPORT.md`
- Test: `tests/test_evidence_closure_cli.py`
- Test: `tests/test_cli_evidence_beta.py`
- Test: `tests/test_governed_iteration_execution_report.py`

- [ ] Write failing CLI tests for `albu-mcp beta response-validate --input <json>` and `albu-mcp beta response-import --input <json> --path <records>`.
- [ ] Add a privacy-safe beta response draft model and conversion to `BetaValidationRecord`.
- [ ] Wire validation/import commands.
- [ ] Update operator docs and governed iteration report to reflect this third blocked iteration.
- [ ] Run targeted and full verification.
