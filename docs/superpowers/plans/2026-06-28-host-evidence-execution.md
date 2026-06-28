# Host Evidence Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current P0 evidence, beta validation, and RC blockers into executable operator packs that reduce manual ambiguity without fabricating passed evidence.

**Architecture:** Add five focused generated artifacts, each backed by a script, tests, and `check_release_readiness.py`. The scripts compose existing evidence builders instead of reading private host logs or running network-dependent actions.

**Tech Stack:** Python 3.10+, uv, pytest, ruff, ty, generated Markdown docs, existing release-readiness gates.

---

### Task 1: Host Evidence Runner

**Files:**
- Create: `scripts/export_host_evidence_runner.py`
- Create: `docs/HOST_EVIDENCE_RUNNER.md`
- Create: `tests/test_host_evidence_runner.py`
- Modify: `scripts/check_release_readiness.py`

- [ ] Build an operator runner pack from `build_p0_host_unblock_pack()`, `build_p0_host_run_preflight()`, and host evidence docs.
- [ ] Include per-host prompts, preflight commands, passed-record commands, blocked-record commands, and post-run regeneration commands.
- [ ] Keep `runner_status` blocked while any P0 recovery lane is blocked.

### Task 2: Codex Cancellation Triage

**Files:**
- Create: `scripts/export_codex_cancellation_triage.py`
- Create: `docs/CODEX_CANCELLATION_TRIAGE.md`
- Create: `tests/test_codex_cancellation_triage.py`
- Modify: `scripts/check_release_readiness.py`

- [ ] Build Codex-only cancellation lanes from P0 unblock evidence.
- [ ] Separate likely causes, safe diagnostics, evidence to capture, and non-goals.
- [ ] Keep the acceptance criterion tied to real MCP host UI completion.

### Task 3: Claude Code Setup Path

**Files:**
- Create: `scripts/export_claude_code_setup_path.py`
- Create: `docs/CLAUDE_CODE_SETUP_PATH.md`
- Create: `tests/test_claude_code_setup_path.py`
- Modify: `scripts/check_release_readiness.py`

- [ ] Build Claude Code setup checks from P0 unblock evidence.
- [ ] Include CLI visibility checks, same-shell version check, MCP command shape, and run-order constraints.
- [ ] Keep status blocked until Claude Code can start the configured MCP server.

### Task 4: Beta Validation Intake

**Files:**
- Create: `scripts/export_beta_validation_intake.py`
- Create: `docs/BETA_VALIDATION_INTAKE.md`
- Create: `tests/test_beta_validation_intake.py`
- Modify: `scripts/check_release_readiness.py`

- [ ] Build beta issue/intake lanes from beta execution and validation status.
- [ ] Include privacy checklist, issue-template mapping, minimum accepted fields, and record commands.
- [ ] Keep product-depth blocked until all beta workflows have validation attempts.

### Task 5: RC Dry Run

**Files:**
- Create: `scripts/export_rc_dry_run.py`
- Create: `docs/RC_DRY_RUN.md`
- Create: `tests/test_rc_dry_run.py`
- Modify: `scripts/check_release_readiness.py`

- [ ] Build a safe RC dry-run packet from RC rehearsal, RC recovery, distribution rollout, and v1 stabilization state.
- [ ] Allow preflight rehearsal while keeping tag/release/PyPI commands blocked.
- [ ] Include exact open-gate criteria and post-dry-run regeneration commands.

### Final Verification

- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check`
- [ ] `uv run pytest -q`
- [ ] `uv run python scripts/check_release_readiness.py`
- [ ] `uv build`
- [ ] `uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json` exits 1 while P0 evidence is blocked.
