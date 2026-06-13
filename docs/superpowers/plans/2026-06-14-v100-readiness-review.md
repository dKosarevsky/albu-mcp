# v1.0 Readiness Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete a documented v1 compatibility review and release `v1.0.0` only if contract and publication checks pass.

**Architecture:** Keep runtime behavior unchanged. Add a v1 audit document and documentation tests, update maturity/release
metadata, verify existing contract snapshots are unchanged, then publish a major release through the existing release
automation.

**Tech Stack:** Markdown docs, `pytest`, `ruff`, `ty`, snapshot export scripts, `uv`, GitHub Actions, PyPI Trusted
Publishing, MCP Registry publishing.

---

## File Structure

- Create: `docs/V1_READINESS.md`
  - Human-readable audit gate for v1 compatibility, packaging, docs, and release automation.
- Modify: `docs/RELEASE.md`
  - Replace old `v0.1.0` examples with version-neutral `vX.Y.Z` examples and include current release files.
- Modify: `tests/test_project_scaffolding.py`
  - Add tests for the v1 audit, stable classifier, and release guide hygiene.
- Modify later in release task: `pyproject.toml`, `server.json`, `uv.lock`, `README.md`, `CHANGELOG.md`, `docs/INSTALL.md`
  - Bump version metadata and release notes to `1.0.0`.

## Task 1: V1 Audit Contract Test

**Files:**
- Modify: `tests/test_project_scaffolding.py`

- [ ] **Step 1: Write the failing tests**

Add two tests:

```python
def test_v1_readiness_audit_is_present_and_complete() -> None:
    audit = Path("docs/V1_READINESS.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    required_terms = [
        "Public Contract Freeze",
        "Snapshot Guards",
        "Golden Evals",
        "Release Automation",
        "Install Flow",
        "Compatibility Policy",
        "No runtime API changes",
        "v1.0.0",
    ]

    for term in required_terms:
        assert term in audit
    assert "[docs/V1_READINESS.md](docs/V1_READINESS.md)" in readme


def test_release_docs_and_package_metadata_are_v1_ready() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    release_docs = Path("docs/RELEASE.md").read_text(encoding="utf-8")

    assert '"Development Status :: 5 - Production/Stable"' in pyproject
    assert '"Development Status :: 3 - Alpha"' not in pyproject
    assert "v0.1.0" not in release_docs
    assert "vX.Y.Z" in release_docs
    assert "CHANGELOG.md" in release_docs
    assert "README.md" in release_docs
    assert "server.json" in release_docs
    assert "uv.lock" in release_docs
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
uv run pytest tests/test_project_scaffolding.py::test_v1_readiness_audit_is_present_and_complete tests/test_project_scaffolding.py::test_release_docs_and_package_metadata_are_v1_ready -q
```

Expected: fail because `docs/V1_READINESS.md` does not exist and the classifier is still alpha.

## Task 2: Audit Docs And Metadata Readiness

**Files:**
- Create: `docs/V1_READINESS.md`
- Modify: `README.md`
- Modify: `docs/RELEASE.md`
- Modify: `pyproject.toml`
- Modify: `tests/test_project_scaffolding.py`

- [ ] **Step 1: Add `docs/V1_READINESS.md`**

Include sections:

```markdown
# V1 Readiness Audit

## Public Contract Freeze
## Snapshot Guards
## Golden Evals
## Release Automation
## Install Flow
## Compatibility Policy
## Decision
```

State explicitly that this pass introduces no runtime API changes.

- [ ] **Step 2: Link audit from README**

In the `V1 Readiness` section, link `[docs/V1_READINESS.md](docs/V1_READINESS.md)`.

- [ ] **Step 3: Update release docs**

Replace `v0.1.0` examples with `vX.Y.Z`, include `README.md`, `CHANGELOG.md`, `docs/INSTALL.md`, `docs/V1_READINESS.md`,
`server.json`, and `uv.lock` in the release commit example, and document that tags are `vX.Y.Z`.

- [ ] **Step 4: Update maturity classifier**

In `pyproject.toml`, replace:

```toml
"Development Status :: 3 - Alpha",
```

with:

```toml
"Development Status :: 5 - Production/Stable",
```

- [ ] **Step 5: Run focused checks**

Run:

```bash
uv run pytest tests/test_project_scaffolding.py -q
uv run ruff check tests/test_project_scaffolding.py
uv run ty check tests/test_project_scaffolding.py
```

Expected: all pass.

- [ ] **Step 6: Commit audit docs**

Commit:

```bash
git add docs/V1_READINESS.md README.md docs/RELEASE.md pyproject.toml tests/test_project_scaffolding.py
git commit -m "docs: add v1 readiness audit"
```

## Task 3: Snapshot Drift Check

**Files:**
- Read: `tests/fixtures/snapshots/mcp_contract.json`
- Read: `tests/fixtures/snapshots/output_contracts.json`

- [ ] **Step 1: Regenerate snapshots to temporary files**

Run:

```bash
uv run python scripts/export_mcp_contract.py --output /tmp/albu-mcp-contract-v1.json
uv run python scripts/export_output_contracts.py --output /tmp/albu-output-contract-v1.json
```

- [ ] **Step 2: Compare with committed fixtures**

Run:

```bash
diff -u tests/fixtures/snapshots/mcp_contract.json /tmp/albu-mcp-contract-v1.json
diff -u tests/fixtures/snapshots/output_contracts.json /tmp/albu-output-contract-v1.json
```

Expected: no diff. If there is any diff, stop and either update the contract intentionally with docs or do not cut v1.

## Task 4: Release v1.0.0

**Files:**
- Modify: `pyproject.toml`
- Modify: `server.json`
- Modify: `uv.lock`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/INSTALL.md`

- [ ] **Step 1: Bump release metadata**

Change version metadata to `1.0.0`, add README `What Changed In 1.0`, update pinned install examples, and add
`1.0.0 - 2026-06-14` to the changelog.

- [ ] **Step 2: Refresh lockfile**

Run:

```bash
uv lock
```

- [ ] **Step 3: Full local verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv run python scripts/check_release_version.py v1.0.0
uv build
```

- [ ] **Step 4: Commit release metadata**

Commit:

```bash
git add pyproject.toml server.json uv.lock README.md CHANGELOG.md docs/INSTALL.md
git commit -m "chore: release v1.0.0"
```

- [ ] **Step 5: Tag and push**

Run:

```bash
git tag v1.0.0
git push origin main
git push origin v1.0.0
```

- [ ] **Step 6: Publish and verify externally**

Watch CI and Release, dispatch MCP Registry publishing, then verify GitHub Release, PyPI JSON, PyPI Simple, MCP Registry
latest metadata, and `uvx --from albumentationsx-mcp==1.0.0 albumentationsx-mcp --help`.
