# Product Development Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add gated product-development artifacts that unblock P0 host evidence, run beta validation, prepare the first P1 host-onboarding depth item, recover the RC cutover path, and define the v1 stabilization scope without fabricating evidence.

**Architecture:** Keep the release train evidence-driven: every new document is generated from committed evidence, current gates, or existing workflow definitions. Each roadmap stage gets one focused exporter script, one committed Markdown output, release-readiness coverage, and tests that assert blocked/manual states remain blocked until real evidence changes.

**Tech Stack:** Python 3.10+, uv, pytest, ruff, ty, generated Markdown docs, existing release-readiness scripts.

---

### Task 1: P0 Host Evidence Unblock Pack

**Files:**
- Create: `scripts/export_p0_host_unblock_pack.py`
- Create: `docs/P0_HOST_UNBLOCK_PACK.md`
- Create: `tests/test_p0_host_unblock_pack.py`
- Modify: `scripts/check_release_readiness.py`

- [ ] **Step 1: Write failing tests**

Run: `uv run pytest -q tests/test_p0_host_unblock_pack.py`
Expected: fails because the exporter does not exist.

- [ ] **Step 2: Implement exporter**

Build from `build_p0_blocker_triage()` and emit host-specific unblock actions:
- Codex blocked gates map to `codex_tool_call_cancelled`.
- Claude Code blocked gates map to `claude_cli_missing`.
- Missing non-P0 gates stay outside this P0 pack.

- [ ] **Step 3: Generate docs and wire release readiness**

Run: `uv run python scripts/export_p0_host_unblock_pack.py --output docs/P0_HOST_UNBLOCK_PACK.md`
Expected: committed Markdown includes acceptance criteria and record commands.

- [ ] **Step 4: Verify**

Run: `uv run pytest -q tests/test_p0_host_unblock_pack.py`
Expected: pass.

### Task 2: Beta Campaign Execution Pack

**Files:**
- Create: `scripts/export_beta_campaign_execution.py`
- Create: `docs/BETA_CAMPAIGN_EXECUTION.md`
- Create: `tests/test_beta_campaign_execution.py`
- Modify: `scripts/check_release_readiness.py`

- [ ] **Step 1: Write failing tests**

Run: `uv run pytest -q tests/test_beta_campaign_execution.py`
Expected: fails because the exporter does not exist.

- [ ] **Step 2: Implement exporter**

Build from beta campaign, workflow, validation, and feedback status. Keep status `ready_to_invite` while validation remains `manual_beta_required`.

- [ ] **Step 3: Generate docs and wire release readiness**

Run: `uv run python scripts/export_beta_campaign_execution.py --output docs/BETA_CAMPAIGN_EXECUTION.md`
Expected: committed Markdown includes workflow invite lanes, record commands, privacy guard, and completion rule.

- [ ] **Step 4: Verify**

Run: `uv run pytest -q tests/test_beta_campaign_execution.py`
Expected: pass.

### Task 3: Host Onboarding Depth Plan

**Files:**
- Create: `scripts/export_host_onboarding_depth_plan.py`
- Create: `docs/HOST_ONBOARDING_DEPTH_PLAN.md`
- Create: `tests/test_host_onboarding_depth_plan.py`
- Modify: `scripts/check_release_readiness.py`

- [ ] **Step 1: Write failing tests**

Run: `uv run pytest -q tests/test_host_onboarding_depth_plan.py`
Expected: fails because the exporter does not exist.

- [ ] **Step 2: Implement exporter**

Build from product-depth selection, P0 blocker triage, and host failure cookbook. Keep implementation blocked until product-depth gate opens, but provide a concrete P1 backlog breakdown.

- [ ] **Step 3: Generate docs and wire release readiness**

Run: `uv run python scripts/export_host_onboarding_depth_plan.py --output docs/HOST_ONBOARDING_DEPTH_PLAN.md`
Expected: committed Markdown includes diagnostics, recovery copy, tests to add, and success signals.

- [ ] **Step 4: Verify**

Run: `uv run pytest -q tests/test_host_onboarding_depth_plan.py`
Expected: pass.

### Task 4: RC Cutover Recovery Plan

**Files:**
- Create: `scripts/export_rc_cutover_recovery_plan.py`
- Create: `docs/RC_CUTOVER_RECOVERY_PLAN.md`
- Create: `tests/test_rc_cutover_recovery_plan.py`
- Modify: `scripts/check_release_readiness.py`

- [ ] **Step 1: Write failing tests**

Run: `uv run pytest -q tests/test_rc_cutover_recovery_plan.py`
Expected: fails because the exporter does not exist.

- [ ] **Step 2: Implement exporter**

Build from RC cutover gate, RC rehearsal plan, and distribution rollout packet. Keep release commands blocked while P0 evidence is blocked.

- [ ] **Step 3: Generate docs and wire release readiness**

Run: `uv run python scripts/export_rc_cutover_recovery_plan.py --output docs/RC_CUTOVER_RECOVERY_PLAN.md`
Expected: committed Markdown shows preflight sequence, blocked publish commands, and exact reopen criteria.

- [ ] **Step 4: Verify**

Run: `uv run pytest -q tests/test_rc_cutover_recovery_plan.py`
Expected: pass.

### Task 5: V1 Stabilization Plan

**Files:**
- Create: `scripts/export_v1_stabilization_plan.py`
- Create: `docs/V1_STABILIZATION_PLAN.md`
- Create: `tests/test_v1_stabilization_plan.py`
- Modify: `scripts/check_release_readiness.py`

- [ ] **Step 1: Write failing tests**

Run: `uv run pytest -q tests/test_v1_stabilization_plan.py`
Expected: fails because the exporter does not exist.

- [ ] **Step 2: Implement exporter**

Build from v1 decision, trust gates, growth cutover, and product-depth selection. Keep v1 blocked and freeze large feature work until P0, beta, and RC gates open.

- [ ] **Step 3: Generate docs and wire release readiness**

Run: `uv run python scripts/export_v1_stabilization_plan.py --output docs/V1_STABILIZATION_PLAN.md`
Expected: committed Markdown defines v1 scope, non-goals, exit criteria, and post-v1 backlog.

- [ ] **Step 4: Verify**

Run: `uv run pytest -q tests/test_v1_stabilization_plan.py`
Expected: pass.

### Final Verification

- [ ] Run `uv run ruff check .`
- [ ] Run `uv run ruff format --check .`
- [ ] Run `uv run ty check`
- [ ] Run `uv run pytest -q`
- [ ] Run `uv run python scripts/check_release_readiness.py`
- [ ] Run `uv build`
- [ ] Run `uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json` and confirm it still exits 1 while P0 evidence is blocked.
