# Host Trust Guided Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `albu-mcp host next-action` with an optional guided evidence session payload that gives one operator all commands needed to collect, validate, import, and re-check real host evidence.

**Architecture:** Keep `src/albumentationsx_mcp/host_trust.py` as the read-only projection layer and reuse the existing evidence command vocabulary instead of adding a second evidence writer. The CLI only toggles inclusion of session guidance; evidence writes remain exclusively under explicit `evidence import-*` commands.

**Tech Stack:** Python 3.10+, argparse CLI, pytest subprocess tests, Markdown generated docs, existing evidence JSON records.

---

### Task 1: Guided Session Projection

**Files:**
- Modify: `src/albumentationsx_mcp/host_trust.py`
- Modify: `tests/test_host_trust_next_action.py`

- [x] **Step 1: Write failing projection test**

Add a test that calls `build_host_trust_dashboard(path=host_records, host="Codex", include_session=True)` and asserts the report includes `guided_session` with `collect_command`, `manifest_path`, `validate_manifest_command`, `import_artifacts_command`, `privacy_doctor_command`, `artifact_doctor_command`, `regenerate_dashboard_command`, and explicit stop conditions.

- [x] **Step 2: Verify RED**

Run: `uv run pytest tests/test_host_trust_next_action.py::test_host_trust_dashboard_can_include_guided_session_payload -q`

Expected: failure because `include_session` is not supported yet.

- [x] **Step 3: Implement minimal projection**

Add an `include_session: bool = False` parameter to `build_host_trust_dashboard`; when enabled and a next lane exists, attach a guided session payload for that lane. The payload must be report-only and use existing command names.

- [x] **Step 4: Verify GREEN**

Run: `uv run pytest tests/test_host_trust_next_action.py::test_host_trust_dashboard_can_include_guided_session_payload -q`

Expected: pass.

### Task 2: CLI Flag and Markdown

**Files:**
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `src/albumentationsx_mcp/host_trust.py`
- Modify: `tests/test_host_trust_next_action.py`

- [x] **Step 1: Write failing CLI tests**

Add subprocess tests for `albu-mcp host next-action --host Codex --include-session --format json` and markdown output containing `## Guided Session`.

- [x] **Step 2: Verify RED**

Run: `uv run pytest tests/test_host_trust_next_action.py -q`

Expected: CLI rejects `--include-session`.

- [x] **Step 3: Implement CLI and renderer**

Add `--include-session` to the `host next-action` parser and pass it into `build_host_trust_dashboard`. Render guided session commands and stop conditions in Markdown only when present.

- [x] **Step 4: Verify GREEN**

Run: `uv run pytest tests/test_host_trust_next_action.py -q`

Expected: all host trust tests pass.

### Task 3: Docs and Verification

**Files:**
- Modify: `docs/HOST_TRUST_DASHBOARD.md`
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `docs/superpowers/plans/2026-07-09-host-trust-guided-session.md`

- [x] **Step 1: Regenerate dashboard**

Run: `uv run albumentationsx-mcp host next-action --include-session --format markdown --output docs/HOST_TRUST_DASHBOARD.md`

- [x] **Step 2: Update concise docs links**

Document `--include-session` in README and USAGE without expanding the long runbooks.

- [x] **Step 3: Run gates**

Run focused tests, full pytest, ruff, format check, ty, release readiness, and build.

- [x] **Step 4: Commit and open PR**

Commit as `feat: add host trust guided session`, push `codex/host-trust-guided-session`, open a PR, wait for CI, merge, and clean the worktree.
