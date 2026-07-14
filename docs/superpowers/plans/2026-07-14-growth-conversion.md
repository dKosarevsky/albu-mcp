# Growth Conversion Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve qualified discovery and first-install conversion while adding a privacy-safe aggregate growth report.

**Architecture:** Keep runtime behavior untouched. Treat README and release aliases as delivery adapters, put metric
calculation in a pure domain module, isolate network access in one script, and keep community publication manual.

**Tech Stack:** Python 3.10+, pytest, uv, Ruff, ty, GitHub Actions, Markdown.

---

### Task 1: Public conversion surface

**Files:**
- Modify: `README.md`
- Create: `docs/INDEX.md`
- Modify: `tests/test_project_scaffolding.py`

- [ ] Add failing contract assertions for the demo image, stable MCPB URL, documentation index, maximum README length,
  and removal of the internal operator command block.
- [ ] Run `uv run pytest tests/test_project_scaffolding.py -q` and confirm the new assertions fail.
- [ ] Rewrite README around install and first preview, then add a curated documentation index.
- [ ] Run the focused tests and `uv run ruff check tests/test_project_scaffolding.py`.
- [ ] Commit as `docs: streamline the install funnel`.

### Task 2: Stable Claude Desktop download

**Files:**
- Modify: `.github/workflows/release.yml`
- Modify: `docs/INSTALL.md`
- Modify: `docs/RELEASE.md`
- Modify: `tests/test_project_scaffolding.py`

- [ ] Add a failing workflow test requiring a byte-identical `albumentationsx-mcp.mcpb` alias before checksums.
- [ ] Run the focused test and confirm it fails on the missing alias command.
- [ ] Add the alias step and document direct and versioned download paths.
- [ ] Run focused workflow and extension-build tests.
- [ ] Commit as `ci: publish a stable MCPB download`.

### Task 3: Aggregate growth report

**Files:**
- Create: `src/albumentationsx_mcp/growth.py`
- Create: `scripts/export_growth_report.py`
- Create: `tests/fixtures/growth_report_input.json`
- Create: `tests/test_growth_report.py`
- Create: `docs/GROWTH.md`

- [ ] Write failing parameterized tests for weekly totals, release-window exclusion, median baseline, zero change,
  MCPB counts, missing Traffic authorization, and invalid data.
- [ ] Run `uv run pytest tests/test_growth_report.py -q` and confirm import or assertion failures.
- [ ] Implement typed parsing, pure analysis, and Markdown rendering in the domain module.
- [ ] Add a live/offline CLI adapter with optional GitHub authentication and explicit partial-source reporting.
- [ ] Run focused tests, Ruff, formatting, and ty.
- [ ] Commit as `feat: add aggregate growth reporting`.

### Task 4: Campaign-ready launch packet

**Files:**
- Modify: `docs/LAUNCH_KIT.md`
- Modify: `docs/NETWORK_GROWTH.md`
- Modify: `tests/test_network_growth_tracker.py`

- [ ] Add failing assertions for three audience-specific campaigns, official docs links, attribution parameters, and
  manual-only publication policy.
- [ ] Run focused tests and confirm the launch packet lacks the new contracts.
- [ ] Add classification robustness, detection, and segmentation campaign cards with prompts and success signals.
- [ ] Link the aggregate report and define a weekly release-independent review cadence.
- [ ] Run focused documentation tests.
- [ ] Commit as `docs: add measurable growth campaigns`.

### Task 5: Verification and integration

- [ ] Run `uv run pytest`.
- [ ] Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run ty check`.
- [ ] Run `uv run python scripts/check_release_readiness.py` and `uv build`.
- [ ] Build the MCPB and verify versioned and stable release-workflow contracts.
- [ ] Request an independent diff review and resolve every important finding.
- [ ] Push a PR, wait for required checks, merge it, and report the human-only outreach actions that remain.
