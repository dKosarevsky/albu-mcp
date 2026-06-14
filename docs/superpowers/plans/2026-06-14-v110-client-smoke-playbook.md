# V1.1 Client Smoke Playbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only client smoke playbook resource for MCP hosts.

**Architecture:** Keep workflow data in `src/albumentationsx_mcp/workflows.py` and FastMCP registration in `server.py`.
Tests assert domain catalog behavior before server wiring, then snapshot the public MCP surface.

**Tech Stack:** Python 3.10+, Pydantic strict models, FastMCP resources, pytest, ruff, ty, uv.

---

### Task 1: RED Tests

**Files:**
- Modify: `tests/test_workflows.py`
- Modify: `tests/test_server.py`
- Modify: `tests/test_project_scaffolding.py`

- [ ] Add a workflow test that expects `client-smoke` from `list_host_examples()` and checks the first tools/resources are `albumentationsx://capabilities`, `albumentationsx://recipes/catalog`, `recommend_recipe`, and `validate_pipeline`.
- [ ] Add a server test that expects `albumentationsx://examples/client-smoke` to be registered and listed in capabilities.
- [ ] Add a docs scaffolding test that expects `docs/INSTALL.md`, `docs/USAGE.md`, and `docs/RECIPES.md` to mention `albumentationsx://examples/client-smoke`.
- [ ] Run `uv run pytest tests/test_workflows.py tests/test_server.py tests/test_project_scaffolding.py -q` and confirm failure is caused by the missing example/resource/docs.

### Task 2: Domain And MCP Resource

**Files:**
- Modify: `src/albumentationsx_mcp/workflows.py`
- Modify: `src/albumentationsx_mcp/server.py`

- [ ] Add `_HOST_EXAMPLES["client-smoke"]` with deterministic steps and success criteria.
- [ ] Register `albumentationsx://examples/client-smoke` in `create_mcp_server()`.
- [ ] Add the resource URI to `capabilities_resource()["workflow_resources"]`.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Docs And Contract Snapshot

**Files:**
- Modify: `docs/INSTALL.md`
- Modify: `docs/USAGE.md`
- Modify: `docs/RECIPES.md`
- Modify: `tests/fixtures/snapshots/mcp_contract.json`

- [ ] Document the client smoke playbook in install, usage, and recipes docs.
- [ ] Run `uv run python scripts/export_mcp_contract.py --output tests/fixtures/snapshots/mcp_contract.json`.
- [ ] Run `uv run pytest tests/test_mcp_contract_snapshot.py tests/test_workflows.py tests/test_server.py tests/test_project_scaffolding.py -q`.

### Task 4: Verify And Commit

**Files:**
- All modified project files.

- [ ] Run `uv run pytest`.
- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run ruff format --check .`.
- [ ] Run `uv run ty check`.
- [ ] Run `uv run python scripts/run_golden_evals.py`.
- [ ] Commit as `feat: add client smoke playbook`.
- [ ] Push `main`. If the package version is bumped later, release as a separate commit and tag.
