# MCP SDK v1 Dependency Bound Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish `1.17.1` with an explicit MCP Python SDK v1 upper bound so fresh installs cannot silently resolve the breaking v2 release.

**Architecture:** Keep `pyproject.toml` as the dependency source of truth and guard the requirement through a metadata-level test. Synchronize existing release manifests without changing runtime or public MCP contracts.

**Tech Stack:** Python 3.10-3.13, uv, pytest, Ruff, ty, Hatch, MCPB CLI, GitHub Actions trusted publishing.

---

### Task 1: Guard the dependency contract

**Files:**
- Modify: `tests/test_project_scaffolding.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add a failing metadata test**

Add a test that parses `pyproject.toml`, extracts the `mcp[cli]` requirement, and asserts it equals
`mcp[cli]>=1.24.0,<2`.

- [ ] **Step 2: Verify the test fails for the missing upper bound**

Run: `uv run pytest tests/test_project_scaffolding.py -k mcp_sdk -v`

Expected: failure showing `mcp[cli]>=1.24.0` does not match the bounded requirement.

- [ ] **Step 3: Add the v1 upper bound**

Change the runtime requirement to:

```toml
"mcp[cli]>=1.24.0,<2",
```

- [ ] **Step 4: Verify the focused test passes**

Run: `uv run pytest tests/test_project_scaffolding.py -k mcp_sdk -v`

Expected: the dependency contract test passes.

- [ ] **Step 5: Commit the dependency fix**

```bash
git add pyproject.toml tests/test_project_scaffolding.py
git commit -m "fix: pin MCP Python SDK to v1"
```

### Task 2: Prepare release metadata

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `server.json`
- Modify: `.mcp.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `desktop-extension/manifest.json`
- Modify: `desktop-extension/pyproject.toml`
- Modify: `CHANGELOG.md`
- Modify: current generated release/status documents and their assertions as identified by release readiness

- [ ] **Step 1: Set every active distribution version to 1.17.1**

Update package, Registry, Codex plugin, MCP config, MCPB manifest, MCPB wrapper package, and exact wrapper dependency
versions. Run `uv lock` so the local package entry and requirement specifier are regenerated.

- [ ] **Step 2: Add the 1.17.1 changelog section**

Record only the MCP SDK v1 bound and its fresh-install compatibility purpose.

- [ ] **Step 3: Regenerate current version-bearing status documents**

Use the repository exporters referenced by failing freshness checks. Do not rewrite historical specs, receipts, or old
release sections.

- [ ] **Step 4: Verify synchronized release metadata**

Run: `uv run python scripts/check_release_readiness.py --tag v1.17.1`

Expected: every aggregate release readiness check passes.

- [ ] **Step 5: Commit release preparation**

```bash
git add pyproject.toml uv.lock server.json .mcp.json .codex-plugin/plugin.json desktop-extension CHANGELOG.md docs tests
git commit -m "release: prepare v1.17.1"
```

### Task 3: Verify package and desktop artifacts

**Files:**
- Verify only unless a failing check identifies release-specific drift.

- [ ] **Step 1: Run the full quality gate**

Run: `uv run pytest`

Expected: all tests pass.

- [ ] **Step 2: Run static checks**

Run: `uv run ruff check .`

Run: `uv run ruff format --check .`

Run: `uv run ty check`

Expected: all commands exit successfully.

- [ ] **Step 3: Run golden MCP scenarios**

Run: `uv run python scripts/run_golden_evals.py --work-dir /private/tmp/albu-v1.17.1-golden`

Expected: every scenario reports `ok`.

- [ ] **Step 4: Build Python and MCPB artifacts**

Run: `uv build`

Run the repository MCPB build script under Node 20 or newer and inspect the resulting archive.

Expected: wheel, sdist, MCPB, and checksum are produced for `1.17.1`.

### Task 4: Integrate and publish

**Files:**
- No additional source changes expected.

- [ ] **Step 1: Push the branch and open a PR**

Create a focused PR explaining the upstream SDK v2 risk and the unchanged public MCP contract.

- [ ] **Step 2: Wait for the Python 3.10-3.13 CI matrix**

Expected: all jobs pass before merge.

- [ ] **Step 3: Merge, synchronize main, and tag**

Create annotated tag `v1.17.1` on the merged commit and push it.

- [ ] **Step 4: Verify public publication**

Confirm GitHub Release assets, PyPI `1.17.1`, published-package `uvx` smoke, and MCP Registry `active/latest` metadata.
