# v0.11 Contract Snapshots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic MCP contract snapshot checks and compatibility policy, then release v0.11.0.

**Architecture:** Keep contract export in `scripts/export_mcp_contract.py` as development tooling. Tests compare the
exported public FastMCP surface against `tests/fixtures/snapshots/mcp_contract.json`. Runtime server behavior does not
change.

**Tech Stack:** Python 3.10+, FastMCP registration objects, pytest, ruff, ty, uv, GitHub Actions release workflows.

---

### Task 1: Contract Snapshot Exporter

**Files:**
- Create: `scripts/export_mcp_contract.py`
- Create: `tests/test_mcp_contract_snapshot.py`
- Create: `tests/fixtures/snapshots/mcp_contract.json`

- [ ] **Step 1: Write failing snapshot test**

Add a test that imports `build_contract_snapshot` from `scripts.export_mcp_contract`, builds the snapshot from
`create_mcp_server()`, and compares it to `tests/fixtures/snapshots/mcp_contract.json`.

Run: `uv run pytest tests/test_mcp_contract_snapshot.py -q`

Expected: fail because `scripts.export_mcp_contract` does not exist.

- [ ] **Step 2: Implement exporter**

Implement `build_contract_snapshot()` and a CLI that writes canonical JSON with sorted keys and a trailing newline.
Include server name, sorted tool entries, sorted resource entries, and sorted prompt entries.

- [ ] **Step 3: Generate fixture and verify**

Run:

```bash
uv run python scripts/export_mcp_contract.py --output tests/fixtures/snapshots/mcp_contract.json
uv run pytest tests/test_mcp_contract_snapshot.py -q
uv run ruff check scripts/export_mcp_contract.py tests/test_mcp_contract_snapshot.py
uv run ty check scripts/export_mcp_contract.py tests/test_mcp_contract_snapshot.py
```

Commit: `test: snapshot mcp contract surface`

### Task 2: Compatibility Policy

**Files:**
- Create: `docs/COMPATIBILITY.md`
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Document compatibility policy**

Add a concise policy covering compatible minor additions, major-release breaking changes, deprecations, and required test
coverage for contract changes.

- [ ] **Step 2: Link policy from public docs**

Add links from README and usage docs so maintainers and MCP host users can find the policy.

- [ ] **Step 3: Verify and commit**

Run:

```bash
uv run pytest tests/test_mcp_contract_snapshot.py tests/test_project_scaffolding.py -q
uv run ruff check scripts/export_mcp_contract.py tests/test_mcp_contract_snapshot.py
uv run ty check scripts/export_mcp_contract.py tests/test_mcp_contract_snapshot.py
```

Commit: `docs: add mcp compatibility policy`

### Task 3: v0.11.0 Release

**Files:**
- Modify: `pyproject.toml`
- Modify: `server.json`
- Modify: `uv.lock`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Document v0.11.0**

Add release notes for contract snapshots and compatibility policy.

- [ ] **Step 2: Bump version metadata**

Update package and server metadata to `0.11.0`.

- [ ] **Step 3: Full verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv run python scripts/check_release_version.py v0.11.0
uv build
```

- [ ] **Step 4: Commit, tag, push, and publish**

Commit: `chore: release v0.11.0`

Tag: `v0.11.0`

Push `main` and tag, watch CI/release workflows, dispatch MCP Registry publish, and verify PyPI, MCP Registry, Simple
index, and `uvx --from albumentationsx-mcp==0.11.0 albumentationsx-mcp --help`.
