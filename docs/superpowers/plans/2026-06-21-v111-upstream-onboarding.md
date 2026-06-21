# v1.11 Release, Upstream Packet, and Dataset Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the accumulated `v1.11.0` work, prepare an upstream AlbumentationsX docs packet, and add a safe dataset onboarding wizard for MCP hosts.

**Architecture:** Keep release metadata, outreach docs, and runtime behavior separated. The new onboarding feature lives in a focused domain module that scans only configured local roots, returns typed agent-legible guidance, and reuses existing recipe, validation, and preview request contracts instead of rendering images directly.

**Tech Stack:** Python 3.10+, Pydantic strict models, FastMCP, pytest, ruff, ty, uv, golden MCP stdio evals.

---

### Task 1: Prepare v1.11.0 Release Metadata

**Files:**
- Modify: `pyproject.toml`
- Modify: `server.json`
- Modify: `uv.lock`
- Modify: `CHANGELOG.md`
- Modify: `docs/HOST_ACCEPTANCE_EVIDENCE.md`
- Modify: `docs/INSTALL.md`
- Modify: `.github/ISSUE_TEMPLATE/host-acceptance.yml`
- Modify: `tests/test_release_readiness.py`
- Modify: `tests/test_mcp_registry_status.py`
- Modify: `tests/test_manual_host_acceptance_packet.py`

- [ ] **Step 1: Update versions and changelog**

Set package and registry metadata to `1.11.0`, move the existing `Unreleased` entries under `## 1.11.0 - 2026-06-21`, and leave `## Unreleased` empty.

- [ ] **Step 2: Regenerate lock and host evidence**

Run:

```bash
uv lock
uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md
```

Expected: `uv.lock` and host evidence match project metadata.

- [ ] **Step 3: Verify release guards**

Run:

```bash
uv run pytest tests/test_release_readiness.py tests/test_mcp_registry_status.py tests/test_manual_host_acceptance_packet.py -q
uv run python scripts/check_release_readiness.py --tag v1.11.0 --format json
uv run python scripts/check_release_version.py v1.11.0
```

Expected: all commands pass and report version `1.11.0`.

- [ ] **Step 4: Commit release preparation**

```bash
git add pyproject.toml server.json uv.lock CHANGELOG.md docs/HOST_ACCEPTANCE_EVIDENCE.md docs/INSTALL.md .github/ISSUE_TEMPLATE/host-acceptance.yml tests/test_release_readiness.py tests/test_mcp_registry_status.py tests/test_manual_host_acceptance_packet.py docs/superpowers/plans/2026-06-21-v111-upstream-onboarding.md
git commit -m "chore: prepare v1.11.0 release"
```

### Task 2: Add Upstream AlbumentationsX Docs PR Packet

**Files:**
- Create: `docs/UPSTREAM_PR_PACKET.md`
- Modify: `docs/NETWORK_GROWTH.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Test: `tests/test_project_scaffolding.py`

- [ ] **Step 1: Write failing documentation contract**

Add a test asserting that `docs/UPSTREAM_PR_PACKET.md` exists, links to `AlbumentationsX#285`, includes a copyable docs snippet, avoids official-affiliation claims, and is linked from `README.md` and `docs/NETWORK_GROWTH.md`.

- [ ] **Step 2: Run the test to verify RED**

Run:

```bash
uv run pytest tests/test_project_scaffolding.py::test_upstream_pr_packet_is_available -q
```

Expected: fails because `docs/UPSTREAM_PR_PACKET.md` does not exist.

- [ ] **Step 3: Add the packet and links**

Create a concise packet with purpose, suggested upstream placement, exact Markdown snippet, validation checklist, and non-affiliation language.

- [ ] **Step 4: Verify and commit**

Run:

```bash
uv run pytest tests/test_project_scaffolding.py::test_upstream_pr_packet_is_available -q
uv run ruff check tests/test_project_scaffolding.py
```

Expected: tests and lint pass.

Commit:

```bash
git add docs/UPSTREAM_PR_PACKET.md docs/NETWORK_GROWTH.md README.md CHANGELOG.md tests/test_project_scaffolding.py
git commit -m "docs: add upstream integration pr packet"
```

### Task 3: Add Dataset Onboarding Wizard

**Files:**
- Create: `src/albumentationsx_mcp/onboarding.py`
- Modify: `src/albumentationsx_mcp/models.py`
- Modify: `src/albumentationsx_mcp/server.py`
- Modify: `src/albumentationsx_mcp/workflows.py`
- Modify: `docs/USAGE.md`
- Modify: `docs/RECIPES.md`
- Modify: `CHANGELOG.md`
- Modify: `evals/golden_mcp_scenarios.yaml`
- Modify: `scripts/run_golden_evals.py`
- Modify: `tests/fixtures/snapshots/mcp_contract.json`
- Modify: `tests/fixtures/snapshots/output_contracts.json`
- Test: `tests/test_onboarding.py`
- Test: `tests/test_server.py`
- Test: `tests/test_golden_evals.py`

- [ ] **Step 1: Write failing domain tests**

Add tests for a local folder scan that counts images, bounds samples, selects a recipe, emits a safe `preview_request_template`, and returns remediation actions for empty folders.

- [ ] **Step 2: Run the domain tests to verify RED**

Run:

```bash
uv run pytest tests/test_onboarding.py -q
```

Expected: fails because the onboarding module and public function do not exist.

- [ ] **Step 3: Implement focused onboarding module**

Implement typed models and `build_dataset_onboarding_report` with local path policy enforcement, image extension filtering, bounded sampling, recipe reuse, validation reuse, and no rendering side effects.

- [ ] **Step 4: Expose MCP tool and resource**

Register `plan_dataset_onboarding` and `albumentationsx://examples/dataset-onboarding`, update capabilities and workflow examples, then refresh contract snapshots.

- [ ] **Step 5: Add golden eval coverage and docs**

Add an executable stdio scenario that reads the onboarding example and calls the tool on deterministic sample images.

- [ ] **Step 6: Verify and commit**

Run:

```bash
uv run pytest tests/test_onboarding.py tests/test_server.py tests/test_golden_evals.py -q
uv run python scripts/run_golden_evals.py
uv run python scripts/check_contract_snapshots.py
uv run python scripts/check_release_readiness.py --tag v1.11.0 --format json
uv run ruff check src/albumentationsx_mcp/onboarding.py src/albumentationsx_mcp/server.py tests/test_onboarding.py tests/test_server.py tests/test_golden_evals.py
uv run ty check
```

Expected: all checks pass.

Commit:

```bash
git add src/albumentationsx_mcp/onboarding.py src/albumentationsx_mcp/models.py src/albumentationsx_mcp/server.py src/albumentationsx_mcp/workflows.py docs/USAGE.md docs/RECIPES.md CHANGELOG.md evals/golden_mcp_scenarios.yaml scripts/run_golden_evals.py tests/fixtures/snapshots/mcp_contract.json tests/fixtures/snapshots/output_contracts.json tests/test_onboarding.py tests/test_server.py tests/test_golden_evals.py
git commit -m "feat: add dataset onboarding wizard"
```

### Task 4: Final Verification, Tag, and Push

**Files:**
- Verify only unless a generated snapshot is stale.

- [ ] **Step 1: Run full local gate**

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/validate_host_manual_runs.py
uv run python scripts/check_host_acceptance_report.py
uv run python scripts/check_contract_snapshots.py
uv run python scripts/check_demo_assets.py --output-dir docs/assets/demo --check
uv run python scripts/check_release_readiness.py --tag v1.11.0 --format json
uv run python scripts/run_golden_evals.py
uv build
git diff --check
```

Expected: all commands pass.

- [ ] **Step 2: Create release tag and push**

```bash
git tag v1.11.0
git push origin main
git push origin v1.11.0
```

Expected: remote `main` and tag are updated.

- [ ] **Step 3: Watch CI and release workflows**

Use GitHub Actions to confirm `main` CI and tag release workflow complete successfully. If the release workflow publishes PyPI and registry metadata, verify those checks after publication.
