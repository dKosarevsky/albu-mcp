# v0.12 Output Contract Snapshots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic representative output contract snapshots and release v0.12.0.

**Architecture:** Keep snapshot generation in `scripts/export_output_contracts.py`. The exporter builds representative
domain outputs with deterministic fixtures and normalizes unstable values before writing
`tests/fixtures/snapshots/output_contracts.json`. Tests compare regenerated output to the reviewed fixture.

**Tech Stack:** Python 3.10+, Pydantic model dumps, pytest, ruff, ty, uv, existing release workflows.

---

### Task 1: Output Snapshot Exporter

**Files:**
- Create: `scripts/export_output_contracts.py`
- Create: `tests/test_output_contract_snapshots.py`
- Create: `tests/fixtures/snapshots/output_contracts.json`

- [ ] **Step 1: Write failing snapshot test**

Add a test that imports `build_output_contract_snapshot` and `dump_output_contract_snapshot`, builds the snapshot in a
temporary directory, and compares it to `tests/fixtures/snapshots/output_contracts.json`.

Run: `uv run pytest tests/test_output_contract_snapshots.py -q`

Expected: fail because `scripts.export_output_contracts` does not exist.

- [ ] **Step 2: Implement exporter**

Implement deterministic builders for recipe recommendation, dataset scoring, preview feedback, and preview report export.
Normalize ids, timestamps, paths, URIs, hashes, and sizes before dumping canonical JSON.

- [ ] **Step 3: Generate fixture and verify**

Run:

```bash
uv run python scripts/export_output_contracts.py --output tests/fixtures/snapshots/output_contracts.json
uv run pytest tests/test_output_contract_snapshots.py -q
uv run ruff check scripts/export_output_contracts.py tests/test_output_contract_snapshots.py
uv run ty check scripts/export_output_contracts.py tests/test_output_contract_snapshots.py
```

Commit: `test: snapshot representative output contracts`

### Task 2: Compatibility Documentation

**Files:**
- Modify: `docs/COMPATIBILITY.md`
- Modify: `README.md`
- Modify: `docs/USAGE.md`

- [ ] **Step 1: Document output snapshots**

Update compatibility guidance to distinguish MCP surface snapshots from representative output contract snapshots.

- [ ] **Step 2: Link exporter command**

Add the output snapshot regeneration command near the existing contract snapshot guidance.

- [ ] **Step 3: Verify and commit**

Run:

```bash
uv run pytest tests/test_mcp_contract_snapshot.py tests/test_output_contract_snapshots.py tests/test_project_scaffolding.py -q
uv run ruff check scripts/export_mcp_contract.py scripts/export_output_contracts.py tests/test_mcp_contract_snapshot.py tests/test_output_contract_snapshots.py
uv run ty check scripts/export_mcp_contract.py scripts/export_output_contracts.py tests/test_mcp_contract_snapshot.py tests/test_output_contract_snapshots.py
```

Commit: `docs: document output contract snapshots`

### Task 3: v0.12.0 Release

**Files:**
- Modify: `pyproject.toml`
- Modify: `server.json`
- Modify: `uv.lock`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Document v0.12.0**

Add release notes for representative output contract snapshots.

- [ ] **Step 2: Bump version metadata**

Update package and server metadata to `0.12.0`.

- [ ] **Step 3: Full verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv run python scripts/check_release_version.py v0.12.0
uv build
```

- [ ] **Step 4: Commit, tag, push, and publish**

Commit: `chore: release v0.12.0`

Tag: `v0.12.0`

Push `main` and tag, watch CI/release workflows, dispatch MCP Registry publish, and verify PyPI, MCP Registry, Simple
index, and `uvx --from albumentationsx-mcp==0.12.0 albumentationsx-mcp --help`.
