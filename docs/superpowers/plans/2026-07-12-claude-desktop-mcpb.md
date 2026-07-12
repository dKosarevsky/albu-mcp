# Claude Desktop MCPB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, validate, install, and release a bounded AlbumentationsX MCP desktop extension for Claude Desktop.

**Architecture:** A small UV MCPB wrapper delegates to the published Python package. A project validator owns version and
security invariants, while the official MCPB CLI owns schema validation and archive creation. Release artifacts remain
separate so PyPI receives only wheel and sdist files.

**Tech Stack:** Python 3.10+, pytest, Ruff, ty, UV, MCPB manifest v0.4, `@anthropic-ai/mcpb@2.1.2`, GitHub Actions.

---

### Task 1: Define The Desktop Extension Contract

**Files:**
- Create: `tests/test_desktop_extension.py`
- Create: `scripts/check_desktop_extension.py`
- Create: `desktop-extension/manifest.json`
- Create: `desktop-extension/pyproject.toml`
- Create: `desktop-extension/src/server.py`
- Create: `desktop-extension/.mcpbignore`
- Create: `desktop-extension/README.md`
- Create: `desktop-extension/icon.png`

- [ ] Write failing tests that require matching project/manifest/dependency versions, UV runtime, explicit directory
  configuration, bounded retention, wrapper delegation, icon presence, and forbidden secret/cache files.
- [ ] Run `uv run pytest -q tests/test_desktop_extension.py` and confirm failure because the contract implementation and
  bundle files do not exist.
- [ ] Implement `validate_desktop_extension()` with structured TOML/JSON parsing and actionable errors.
- [ ] Add the minimal UV wrapper bundle and generated-file exclusions.
- [ ] Run the focused tests and `uv run python scripts/check_desktop_extension.py`; confirm both pass.
- [ ] Commit as `feat: add Claude Desktop MCP bundle`.

### Task 2: Validate And Pack With The Official Toolchain

**Files:**
- Modify: `tests/test_desktop_extension.py`
- Create: `scripts/build_desktop_extension.py`
- Modify: `docs/INSTALL.md`

- [ ] Write failing tests for deterministic output naming, clean output replacement, and subprocess argument
  construction using `@anthropic-ai/mcpb@2.1.2`.
- [ ] Run the focused test and confirm it fails because the build orchestration is absent.
- [ ] Implement the build script so project validation runs before official `mcpb validate` and `mcpb pack`.
- [ ] Run `uv run python scripts/build_desktop_extension.py --output-dir /tmp/albu-mcpb-dist`.
- [ ] Run official `mcpb info` and inspect the archive file list for only expected bundle content.
- [ ] Document one-click installation and required directory selections.
- [ ] Commit as `build: package Claude Desktop extension`.

### Task 3: Complete Real Claude Desktop Free Acceptance

**Files:**
- Create after observed success: `docs/host-evidence/claude-desktop-2026-07-12.md`
- Create after observed success: `docs/assets/host-evidence/claude-desktop-2026-07-12-baseline.png`
- Create after observed success: `docs/assets/host-evidence/claude-desktop-2026-07-12-accepted.png`
- Modify after observed success: `docs/HOST_MANUAL_RUNS.json`
- Modify: generated host evidence/status documents selected by the repository exporters
- Test: host evidence and release-readiness tests affected by the new host

- [ ] Remove the unsuccessful legacy JSON entry without touching unrelated Desktop settings.
- [ ] Install the built `.mcpb` through Claude Desktop's extension installer and select the two bounded `/tmp` roots.
- [ ] Perform the reviewer-observed smoke, review-packet, baseline, feedback, candidate, decision, and export workflow.
- [ ] Verify contact sheets differ at pixel level and retain readable fixture geometry.
- [ ] Write tests for the additional `Claude Desktop` host without changing the blocked `Claude Code` record.
- [ ] Record sanitized evidence and regenerate derived reports only after the UI workflow succeeds.
- [ ] Run focused host-evidence tests and commit as `docs: record Claude Desktop host acceptance`.

### Task 4: Add Release Artifact Automation

**Files:**
- Modify: `tests/test_project_scaffolding.py`
- Modify: `.github/workflows/release.yml`
- Modify: `scripts/check_release_readiness.py`
- Modify: `docs/RELEASE.md`

- [ ] Write failing workflow-contract tests requiring MCPB validation, a separate `mcpb` artifact, PyPI artifact
  isolation, and GitHub Release attachment.
- [ ] Run the focused tests and confirm the workflow lacks those stages.
- [ ] Add the pinned official MCPB validate/pack commands and separate upload/download steps.
- [ ] Add the desktop-extension validator to release readiness and document the artifact flow.
- [ ] Run focused release tests and a local bundle build.
- [ ] Commit as `ci: publish MCPB release artifact`.

### Task 5: Prepare And Publish The Release

**Files:**
- Modify: `pyproject.toml`
- Modify: `server.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `.mcp.json`
- Modify: `desktop-extension/manifest.json`
- Modify: `desktop-extension/pyproject.toml`
- Modify: `uv.lock`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: versioned generated readiness documents

- [ ] Update all package and extension pins to `1.17.0` and move user-facing changes into the dated changelog section.
- [ ] Run `uv lock` and regenerate versioned readiness documents using their existing exporters.
- [ ] Run full pytest, Ruff lint/format, `ty`, release readiness for `v1.17.0`, golden evals, Python build, MCPB build,
  plugin validation, and skill validation.
- [ ] Commit as `release: prepare v1.17.0`.
- [ ] Push the branch, open a PR, wait for Python 3.10-3.13 CI, and merge while preserving logical commits.
- [ ] Tag merged `main` as `v1.17.0`, watch the release workflow, then verify PyPI, GitHub Release MCPB attachment,
  MCP Registry metadata, and a clean install of the published Desktop extension.
