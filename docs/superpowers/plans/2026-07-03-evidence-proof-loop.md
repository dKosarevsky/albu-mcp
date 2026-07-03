# Evidence Proof Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a controlled evidence proof loop that shortens the path from a real reviewer-observed host session to gate status, release preview, and transcript handoff without fabricating evidence.

**Architecture:** Add `src/albumentationsx_mcp/evidence_proof.py` as a focused orchestration module over existing evidence, trust, and RC builders. Keep actual record mutation limited to the existing `evidence import-manifest` command; new proof-loop commands are no-write/report-only artifact builders. Wire the new surface through thin `evidence` CLI adapters and update governed iteration reporting to record the next external-gate stop.

**Tech Stack:** Python 3.10+, argparse CLI, existing evidence/trust/rc modules, pytest, ruff, ty, uv.

---

### Task 1: Evidence Proof-Runner

**Files:**
- Create: `src/albumentationsx_mcp/evidence_proof.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_proof_loop_cli.py`

- [ ] **Step 1: Write failing CLI test**

Test `python -m albumentationsx_mcp evidence proof-runner --input <manifest> --path <records> --format json` with a filled passed manifest.

Expected payload:
- `runner_status == "ready_to_import"`;
- `writes_records is False`;
- `host == "Codex"`;
- `manifest_validation.validation_status == "ready_to_import"`;
- `next_commands` include `evidence validate-manifest`, `evidence import-manifest`, `evidence close-host`, `trust gate-transition`;
- records file remains unchanged.

- [ ] **Step 2: Run RED test**

Run: `uv run pytest tests/test_evidence_proof_loop_cli.py::test_evidence_proof_runner_reports_no_write_import_flow -q`

Expected: FAIL because `evidence proof-runner` is not registered.

- [ ] **Step 3: Implement builder and CLI**

Add `EvidenceProofRequest`, `build_evidence_proof_runner(...)`, and `evidence proof-runner`. The builder loads and validates the manifest through existing evidence validation only. It must not import records.

- [ ] **Step 4: Run GREEN test**

Run: `uv run pytest tests/test_evidence_proof_loop_cli.py::test_evidence_proof_runner_reports_no_write_import_flow -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add evidence proof runner`

### Task 2: Evidence Proof-Status

**Files:**
- Modify: `src/albumentationsx_mcp/evidence_proof.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_proof_loop_cli.py`

- [ ] **Step 1: Write failing status test**

Test `evidence proof-status --path <records> --format json`.

Expected payload:
- `status == "blocked"`;
- `writes_records is False`;
- `required_hosts == ["Codex", "Claude Code"]`;
- `host_count == 2`;
- every host item has `host`, `closure_status`, `missing_gates`, `next_commands`;
- `next_action == "run_proof_runner_for_first_blocked_host"`.

- [ ] **Step 2: Run RED test**

Expected: FAIL because `proof-status` is missing.

- [ ] **Step 3: Implement proof-status builder and CLI**

Compose `build_evidence_close_host_report` for required P0 hosts only.

- [ ] **Step 4: Run GREEN test**

Run: `uv run pytest tests/test_evidence_proof_loop_cli.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add evidence proof status`

### Task 3: Trust Transition Auto-Pack

**Files:**
- Modify: `src/albumentationsx_mcp/evidence_proof.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_proof_loop_cli.py`

- [ ] **Step 1: Write failing artifact test**

Test `evidence transition-pack --before-host-records <before> --after-host-records <after> --beta-records <beta> --output-dir <dir> --format markdown`.

Expected files:
- `trust-transition-pack-index.md`;
- `trust-gate-transition.md`;
- `rc-go-check-preview.md`.

Expected content includes trust gate transition, before/after trust score, `albu-mcp trust gate-transition`, and `albu-mcp rc go-check`.

- [ ] **Step 2: Run RED test**

Expected: FAIL because `transition-pack` is missing.

- [ ] **Step 3: Implement artifact builder and CLI**

Build artifacts from `build_trust_gate_transition_report` and `build_rc_go_check_report`; no writes except artifact files.

- [ ] **Step 4: Run GREEN test**

Run: `uv run pytest tests/test_evidence_proof_loop_cli.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add evidence transition pack`

### Task 4: RC Unblock Preview

**Files:**
- Modify: `src/albumentationsx_mcp/evidence_proof.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_proof_loop_cli.py`

- [ ] **Step 1: Write failing preview test**

Test `evidence rc-unblock-preview --host-records <records> --beta-records <beta> --format json`.

Expected payload:
- `preview_status == "blocked"`;
- `publish_allowed is False`;
- includes `blocked_reasons`, `next_unlock_commands`, and `release_readiness_command`;
- `next_unlock_commands` include `evidence proof-status`, `beta loop-pack`, and `rc go-check`.

- [ ] **Step 2: Run RED test**

Expected: FAIL because `rc-unblock-preview` is missing.

- [ ] **Step 3: Implement builder and CLI**

Compose existing RC reopen/go-check reports and proof-status.

- [ ] **Step 4: Run GREEN test**

Run: `uv run pytest tests/test_evidence_proof_loop_cli.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add rc unblock preview`

### Task 5: Operator Transcript Template And Governed Stop

**Files:**
- Modify: `src/albumentationsx_mcp/evidence_proof.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `docs/USAGE.md`
- Modify: `scripts/export_governed_iteration_execution_report.py`
- Modify: `tests/test_governed_iteration_execution_report.py`
- Test: `tests/test_evidence_proof_loop_cli.py`

- [ ] **Step 1: Write failing transcript test**

Test `evidence transcript-template --host Codex --output-dir <dir> --format markdown`.

Expected file `codex-operator-transcript-template.md` includes reviewer, host, commands used, privacy note, and non-fabrication policy.

- [ ] **Step 2: Implement transcript template**

Add artifact builder and CLI command. Update `docs/USAGE.md`.

- [ ] **Step 3: Update governed report**

Expect:
- `executed_iteration_count == 12`;
- `stopped_at_iteration == 12`;
- `completed_path_count == 62`;
- `completed_plan_point_count == 62`;
- five proof-loop paths plus the twelfth governed stop.

Regenerate `docs/GOVERNED_100_ITERATION_REPORT.md`.

- [ ] **Step 4: Run targeted gate**

Run: `uv run pytest tests/test_evidence_proof_loop_cli.py tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q`

- [ ] **Step 5: Commit**

Commit: `docs: record evidence proof loop stop`

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

Push `codex/evidence-proof-loop`, open PR, wait for GitHub CI, merge, sync `main`, and report the five implemented points plus the governed stop for the requested 100 follow-up iterations.
