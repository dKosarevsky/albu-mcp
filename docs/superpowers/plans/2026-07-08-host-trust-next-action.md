# Host Trust Next Action Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a host-level trust operator command and compact dashboard so release owners can see the next real evidence action per MCP host.

**Architecture:** Keep evidence parsing in the existing `evidence` model layer, add a focused host-trust projection for read-only operator decisions, and expose it through the existing `host` CLI group. Generated docs should come from the same projection as the CLI to avoid stale hand-written status tables.

**Tech Stack:** Python 3.10+, argparse CLI, pydantic evidence records, pytest subprocess CLI tests, Markdown docs.

---

### Task 1: Host Trust Projection

**Files:**
- Create: `src/albumentationsx_mcp/host_trust.py`
- Test: `tests/test_host_trust_next_action.py`

- [x] **Step 1: Write failing tests**

Add tests that create temporary `HOST_MANUAL_RUNS.json` fixtures, call the desired projection, and assert that blocked P0 hosts return a single evidence-collection next command without writing records.

- [x] **Step 2: Verify RED**

Run: `uv run pytest tests/test_host_trust_next_action.py -q`

Expected: import or assertion failure because `host_trust.py` does not exist yet.

- [x] **Step 3: Implement minimal projection**

Implement `build_host_trust_dashboard`, `render_host_trust_dashboard_markdown`, and small helpers for gate status, priority, command quoting, and next action selection.

- [x] **Step 4: Verify GREEN**

Run: `uv run pytest tests/test_host_trust_next_action.py -q`

Expected: all tests pass.

### Task 2: Host CLI Surface

**Files:**
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_host_trust_next_action.py`

- [x] **Step 1: Write failing CLI tests**

Add subprocess tests for `albu-mcp host next-action --format json` and `--format markdown --output docs/HOST_TRUST_DASHBOARD.md`.

- [x] **Step 2: Verify RED**

Run: `uv run pytest tests/test_host_trust_next_action.py -q`

Expected: CLI fails with unsupported `host next-action`.

- [x] **Step 3: Implement CLI**

Add `host next-action` under `_run_host_cli`, with `--path`, optional `--host`, `--format`, and `--output`.

- [x] **Step 4: Verify GREEN**

Run: `uv run pytest tests/test_host_trust_next_action.py -q`

Expected: all tests pass.

### Task 3: Docs Wiring

**Files:**
- Create: `docs/HOST_TRUST_DASHBOARD.md`
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Test: `tests/test_host_trust_next_action.py`

- [x] **Step 1: Write failing docs tests**

Assert the committed dashboard includes the host table, report-only policy, and `host next-action` regeneration command.

- [x] **Step 2: Generate docs**

Run: `uv run albumentationsx-mcp host next-action --format markdown --output docs/HOST_TRUST_DASHBOARD.md`.

- [x] **Step 3: Update README and USAGE**

Add concise links and command examples for the new host trust dashboard.

- [x] **Step 4: Run focused and release gates**

Run focused tests, lint/type checks, release readiness, and build before commit.
