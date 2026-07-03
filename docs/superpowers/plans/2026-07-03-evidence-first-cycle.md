# Evidence First Cycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one governed no-write evidence-first product cycle that packages the next five development tracks without fabricating external host or beta evidence.

**Architecture:** Create a focused orchestration module, `src/albumentationsx_mcp/product_cycle.py`, that composes existing evidence, beta, trust, distribution, and proof-sprint builders. Keep `cli.py` as a thin argparse adapter under `activation evidence-first-cycle`. Update governed iteration reporting to record the eleventh stopped follow-up loop after these five tracks.

**Tech Stack:** Python 3.10+, argparse CLI, existing AlbumentationsX MCP domain builders, pytest, ruff, ty, uv.

---

### Task 1: Evidence-First Cycle Report

**Files:**
- Create: `src/albumentationsx_mcp/product_cycle.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_first_cycle_cli.py`

- [ ] **Step 1: Write failing JSON CLI test**

Test `python -m albumentationsx_mcp activation evidence-first-cycle --host Codex --host-records <empty-host-json> --beta-records <empty-beta-json> --format json`.

Expected payload:
- `cycle_status == "blocked"`;
- `writes_records is False`;
- `track_count == 5`;
- track ids are `evidence_first_result_pack`, `beta_acquisition_loop`, `gate_transition_release_readiness`, `p1_host_onboarding_gate`, `distribution_adoption_handoff`;
- `next_action == "run_evidence_first_result_pack"`;
- non-fabrication policy says generated cycle files do not count as evidence;
- host and beta record files remain byte-for-byte unchanged.

- [ ] **Step 2: Run RED test**

Run: `uv run pytest tests/test_evidence_first_cycle_cli.py::test_activation_evidence_first_cycle_reports_five_no_write_tracks -q`

Expected: FAIL because `activation evidence-first-cycle` is not registered.

- [ ] **Step 3: Implement report builder and CLI adapter**

Add `build_evidence_first_cycle(...)` in `product_cycle.py`. It should compose:
- `build_evidence_close_host_report(host=...)`;
- `build_beta_validation_report(validate_beta_validation_records(...))`;
- `build_trust_gate_transition_report(...)`;
- `build_distribution_readiness_report(...)`;
- `build_real_proof_run_1(...)`.

Register `activation evidence-first-cycle` in `cli.py` with `--host`, `--host-records`, `--beta-records`, optional `--before-host-records`, optional `--before-beta-records`, `--release-tag`, `--output-dir`, and `--format text|json|markdown`.

- [ ] **Step 4: Run GREEN test**

Run: `uv run pytest tests/test_evidence_first_cycle_cli.py::test_activation_evidence_first_cycle_reports_five_no_write_tracks -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add evidence first cycle report`

### Task 2: Five Handoff Artifacts

**Files:**
- Modify: `src/albumentationsx_mcp/product_cycle.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `docs/USAGE.md`
- Test: `tests/test_evidence_first_cycle_cli.py`

- [ ] **Step 1: Write failing artifact test**

Test `activation evidence-first-cycle --host Codex --output-dir <dir> --format markdown`.

Expected files:
- `evidence-first-cycle-index.md`;
- `evidence-first-result-pack.md`;
- `beta-acquisition-loop.md`;
- `gate-transition-release-readiness.md`;
- `p1-host-onboarding-gate.md`;
- `distribution-adoption-handoff.md`.

Expected content:
- index has `# Evidence First Cycle` and `Writes records: `false``;
- evidence file has `albu-mcp evidence validate-manifest`, `albu-mcp evidence import-manifest`, and `albu-mcp evidence close-host`;
- beta file has the official Albumentations MCP docs URL and `albu-mcp beta response-import-dir`;
- gate transition file has `albu-mcp trust gate-transition`, `albu-mcp rc go-check`, and `albu-mcp distribution readiness`;
- P1 file says `Implementation allowed: `false`` and `external gates`;
- adoption file mentions `MCP Registry`, `PyPI`, and upstream Albumentations docs.

- [ ] **Step 2: Run RED test**

Run: `uv run pytest tests/test_evidence_first_cycle_cli.py::test_activation_evidence_first_cycle_writes_five_handoff_artifacts -q`

Expected: FAIL because artifact builder is missing.

- [ ] **Step 3: Implement artifact builder**

Add `build_evidence_first_cycle_artifacts(...)`, `render_evidence_first_cycle_markdown(...)`, and focused markdown helpers in `product_cycle.py`. The artifact builder must not write records; it only returns filenames and content.

- [ ] **Step 4: Update usage docs**

Add:

```bash
albu-mcp activation evidence-first-cycle --host Codex --output-dir docs/evidence-first-cycle --format markdown
```

Mark it as report-only/artifact-only.

- [ ] **Step 5: Run GREEN tests**

Run: `uv run pytest tests/test_evidence_first_cycle_cli.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q`

Expected: PASS.

- [ ] **Step 6: Commit**

Commit: `feat: add evidence first cycle artifacts`

### Task 3: Gate Readiness And Distribution State

**Files:**
- Modify: `src/albumentationsx_mcp/product_cycle.py`
- Test: `tests/test_evidence_first_cycle_cli.py`

- [ ] **Step 1: Write focused readiness assertions**

Extend JSON test to assert:
- `tracks[2]["status"] == "blocked_until_gate_transition"`;
- `tracks[2]["next_commands"]` includes trust gate transition, rc go-check, and distribution readiness;
- `tracks[4]["publish_allowed"] is False`;
- `tracks[4]["status"] == "blocked_until_release_gates"`.

- [ ] **Step 2: Run RED/GREEN as needed**

Run: `uv run pytest tests/test_evidence_first_cycle_cli.py -q`.

Expected after implementation: PASS.

- [ ] **Step 3: Commit**

Commit: `feat: expose evidence cycle readiness gates`

### Task 4: Governed 100-Iteration Stop

**Files:**
- Modify: `scripts/export_governed_iteration_execution_report.py`
- Modify: `tests/test_governed_iteration_execution_report.py`
- Modify: `docs/GOVERNED_100_ITERATION_REPORT.md`

- [ ] **Step 1: Write failing governed expectations**

Update tests to expect:
- `executed_iteration_count == 11`;
- `stopped_at_iteration == 11`;
- `completed_path_count == 56`;
- `completed_plan_point_count == 56`;
- five new completed paths plus the eleventh governed stop.

- [ ] **Step 2: Run RED test**

Run: `uv run pytest tests/test_governed_iteration_execution_report.py -q`

Expected: FAIL on the previous tenth-iteration values.

- [ ] **Step 3: Update exporter and regenerate markdown**

Add five completed paths for evidence-first cycle, beta acquisition, gate transition, P1 gate, and distribution adoption. Add the eleventh stopped loop statement. Regenerate:

```bash
uv run python scripts/export_governed_iteration_execution_report.py --output docs/GOVERNED_100_ITERATION_REPORT.md
```

- [ ] **Step 4: Run GREEN tests**

Run: `uv run pytest tests/test_evidence_first_cycle_cli.py tests/test_governed_iteration_execution_report.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `docs: record evidence first cycle stop`

### Task 5: Final Verification, Push, PR, Merge

**Files:**
- No additional source changes unless verification finds a bug.

- [ ] **Step 1: Run full local gate**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/check_release_readiness.py
uv build
```

- [ ] **Step 2: Push and open PR**

Push `codex/evidence-first-cycle`, open a PR, wait for CI.

- [ ] **Step 3: Merge and sync main**

Merge after GitHub checks pass, sync local `main`, delete remote branch if needed.

- [ ] **Step 4: Report outcome**

Report the five implemented points, the governed stop for the requested 100 follow-up iterations, PR URL, merge commit, and verification evidence.
