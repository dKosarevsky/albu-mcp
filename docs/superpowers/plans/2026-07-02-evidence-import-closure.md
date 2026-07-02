# Evidence Import Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gap between validated reviewer-observed evidence manifests and committed host evidence records without weakening the non-fabrication policy.

**Architecture:** Keep the evidence domain in `src/albumentationsx_mcp/evidence.py` and keep `src/albumentationsx_mcp/cli.py` as a thin argparse adapter. The new commands reuse existing manifest validation and host gate summaries; generated folders remain no-write until explicit import commands run.

**Tech Stack:** Python 3.10+, Pydantic, argparse, pytest, ruff, ty, uv, generated Markdown/JSON docs.

---

### Task 1: Import Manifest

**Files:**
- Modify: `src/albumentationsx_mcp/evidence.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_import_closure_cli.py`

- [ ] Write a failing CLI test for `albu-mcp evidence import-manifest --input ... --path ... --format json`.
- [ ] Implement `import_evidence_session_manifest()` by validating the manifest through `validate_evidence_session_manifest()` and then writing both P0 gates through `import_evidence_artifacts()`.
- [ ] Add parser and handler for `evidence import-manifest`.
- [ ] Verify targeted tests and commit `feat: add evidence import manifest`.

### Task 2: Session Folder

**Files:**
- Modify: `src/albumentationsx_mcp/evidence.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_import_closure_cli.py`

- [ ] Write a failing CLI test for `albu-mcp evidence session-folder --host ... --output-dir ...`.
- [ ] Implement a no-write artifact bundle with index, manifest template, import checklist, collect wizard, and close-host report.
- [ ] Add parser and handler for `evidence session-folder`.
- [ ] Verify targeted tests and commit `feat: add evidence session folder`.

### Task 3: Close Host

**Files:**
- Modify: `src/albumentationsx_mcp/evidence.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Modify: `docs/USAGE.md`
- Modify: `scripts/export_governed_iteration_execution_report.py`
- Modify: `docs/GOVERNED_100_ITERATION_REPORT.md`
- Test: `tests/test_evidence_import_closure_cli.py`
- Test: `tests/test_governed_iteration_execution_report.py`

- [ ] Write a failing CLI test for `albu-mcp evidence close-host --host ... --format json`.
- [ ] Implement a no-write host closure report with missing gates, exact next commands, and ready state once both P0 gates pass.
- [ ] Add parser and handler for `evidence close-host`.
- [ ] Update USAGE and governed 100-iteration report with the seventh external-gate stop.
- [ ] Verify full local gate and commit `feat: add evidence close host`.

### Verification

- [ ] `uv run pytest -q`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check`
- [ ] `uv run python scripts/check_release_readiness.py`
- [ ] `uv build`
