# P0 Beta RC Gate Reopen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic operator packs and probes that move the project from merged execution packets toward reopening the RC gate without fabricating host or beta evidence.

**Architecture:** Each stage adds one focused exporter or probe script, one generated Markdown document, and tests. `scripts/check_release_readiness.py` owns generated-doc freshness so docs cannot drift from committed evidence.

**Tech Stack:** Python, uv, pytest, ruff, ty, generated Markdown docs.

---

### Task 1: P0 Host Evidence Recovery

**Files:**
- Create: `scripts/export_p0_host_evidence_recovery.py`
- Create: `docs/P0_HOST_EVIDENCE_RECOVERY.md`
- Create: `tests/test_p0_host_evidence_recovery.py`
- Modify: `scripts/check_release_readiness.py`
- Modify: `tests/test_release_readiness.py`

- [ ] Build a recovery packet from `build_host_evidence_runner()`, `build_codex_cancellation_triage()`, and `build_claude_code_setup_path()`.
- [ ] Keep status blocked until real Codex and Claude Code host evidence passes.
- [ ] Include exact passed/blocked record commands and source docs.
- [ ] Add generated-doc freshness guard.

### Task 2: Beta Validation Records

**Files:**
- Create: `scripts/export_beta_validation_recording_pack.py`
- Create: `docs/BETA_VALIDATION_RECORDING_PACK.md`
- Create: `tests/test_beta_validation_recording_pack.py`
- Modify: `scripts/check_release_readiness.py`
- Modify: `tests/test_release_readiness.py`

- [ ] Build recording lanes from `build_beta_validation_intake()` and `build_beta_validation_status()`.
- [ ] Preserve `manual_beta_required` while committed records are empty.
- [ ] Include exact `record_beta_validation.py` commands and privacy constraints.
- [ ] Add generated-doc freshness guard.

### Task 3: Host Setup Probe

**Files:**
- Create: `scripts/check_host_setup_probe.py`
- Create: `docs/HOST_SETUP_PROBE.md`
- Create: `tests/test_host_setup_probe.py`
- Modify: `scripts/check_release_readiness.py`
- Modify: `tests/test_release_readiness.py`

- [ ] Implement a CLI probe for host setup prerequisites: `uvx`, `claude`, allowed root, artifact root, package command, and source docs.
- [ ] Support deterministic test injection for executable checks.
- [ ] Render a host setup probe document with blocked/recoverable status.
- [ ] Add generated-doc freshness guard.

### Task 4: Beta-to-Backlog Triage

**Files:**
- Create: `scripts/export_beta_to_backlog_triage.py`
- Create: `docs/BETA_TO_BACKLOG_TRIAGE.md`
- Create: `tests/test_beta_to_backlog_triage.py`
- Modify: `scripts/check_release_readiness.py`
- Modify: `tests/test_release_readiness.py`

- [ ] Build a triage report from beta validation status, product depth gate, and existing depth plans.
- [ ] Keep implementation recommendations blocked while beta signal is missing.
- [ ] Map triage buckets to backlog targets without inventing beta findings.
- [ ] Add generated-doc freshness guard.

### Task 5: RC Gate Reopen Packet

**Files:**
- Create: `scripts/export_rc_gate_reopen_packet.py`
- Create: `docs/RC_GATE_REOPEN_PACKET.md`
- Create: `tests/test_rc_gate_reopen_packet.py`
- Modify: `scripts/check_release_readiness.py`
- Modify: `tests/test_release_readiness.py`
- Modify: `README.md`
- Modify: `docs/V1_READINESS.md`

- [ ] Build a final reopen packet from the RC dry run, hard cutover gate, P0 recovery, and beta recording pack.
- [ ] Show open criteria and blocked publish commands while the gate is closed.
- [ ] Link the new packets from lightweight docs without expanding README beyond its existing guard.
- [ ] Add generated-doc freshness guard.

### Final Verification

- [ ] Run `uv run ruff check .`
- [ ] Run `uv run ruff format --check .`
- [ ] Run `uv run ty check`
- [ ] Run `uv run pytest -q`
- [ ] Run `uv run python scripts/check_release_readiness.py`
- [ ] Run `uv build`
- [ ] Run `uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json` and expect exit 1 until real P0 evidence passes.
