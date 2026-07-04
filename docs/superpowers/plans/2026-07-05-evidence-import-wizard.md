# Evidence Import Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a no-write-by-default evidence import wizard that validates real host manifests and beta drafts, then imports records only with an explicit flag.

**Architecture:** Implement a focused orchestration module and keep CLI parsing thin. Reuse existing evidence and beta validators/importers instead of duplicating schema rules. The command returns structured JSON, compact text, and Markdown.

**Tech Stack:** Python, argparse CLI, pydantic validators already in the project, pytest, ruff, ty, uv.

---

### Task 1: Domain Contract And No-Write Readiness

**Files:**
- Create: `src/albumentationsx_mcp/evidence_import_wizard.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_import_wizard_cli.py`

- [ ] **Step 1: Write failing CLI tests for no-write mode**

Add tests that call:

```bash
python -m albumentationsx_mcp evidence import-wizard \
  --host-records <tmp HOST_MANUAL_RUNS.json> \
  --beta-records <tmp BETA_VALIDATION_RECORDS.json> \
  --host-manifest <missing manifest> \
  --beta-dir <missing dir> \
  --format json
```

Expected JSON:

- `wizard_status == "blocked"`
- `writes_records is False`
- `blocked_reasons` contains `host_manifest_missing` and `beta_dir_missing`
- host and beta records are unchanged

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_evidence_import_wizard_cli.py::test_evidence_import_wizard_no_write_reports_missing_inputs -q
```

Expected: fail because `import-wizard` is not registered.

- [ ] **Step 3: Implement minimal no-write module and CLI**

Create request dataclass, `build_evidence_import_wizard`, text/markdown render helpers, and CLI parser/handler.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_evidence_import_wizard_cli.py::test_evidence_import_wizard_no_write_reports_missing_inputs -q
```

Expected: pass.

### Task 2: Valid Inputs And Explicit Import

**Files:**
- Modify: `src/albumentationsx_mcp/evidence_import_wizard.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_evidence_import_wizard_cli.py`

- [ ] **Step 1: Write failing import-mode tests**

Add fixtures for two filled host manifests (`Codex`, `Claude Code`) and three beta response drafts. Test:

```bash
python -m albumentationsx_mcp evidence import-wizard \
  --host-records <tmp HOST_MANUAL_RUNS.json> \
  --beta-records <tmp BETA_VALIDATION_RECORDS.json> \
  --host-manifest <codex manifest> \
  --host-manifest <claude code manifest> \
  --beta-dir <draft dir> \
  --import-ready \
  --format json
```

Expected JSON:

- `wizard_status == "imported"`
- `writes_records is True`
- `host_manifest_count == 2`
- `beta_draft_count == 3`
- post-import host records contain both P0 hosts in both gates
- post-import beta records contain all three workflows

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_evidence_import_wizard_cli.py::test_evidence_import_wizard_imports_ready_inputs -q
```

Expected: fail because import mode is not implemented.

- [ ] **Step 3: Implement explicit import path**

Use `import_evidence_session_manifest` for each validated manifest and `import_beta_response_draft_dir` for the beta
directory. Rebuild the real adoption cycle after import and include `post_import_cycle_status`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_evidence_import_wizard_cli.py -q
```

Expected: pass.

### Task 3: Docs And Release Verification

**Files:**
- Modify: `docs/USAGE.md`
- Modify: `docs/REAL_EVIDENCE_INPUT_CHECKLIST.md`
- Test: `tests/test_cli_evidence_beta.py`

- [ ] **Step 1: Add usage references**

Document the new command in operator CLI docs and the real evidence checklist.

- [ ] **Step 2: Update docs test if needed**

Ensure the usage/docs test expects `albu-mcp evidence import-wizard`.

- [ ] **Step 3: Run verification**

Run:

```bash
uv run pytest tests/test_evidence_import_wizard_cli.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
uv run ruff check src/albumentationsx_mcp/evidence_import_wizard.py src/albumentationsx_mcp/cli.py tests/test_evidence_import_wizard_cli.py
uv run ruff format --check src/albumentationsx_mcp/evidence_import_wizard.py src/albumentationsx_mcp/cli.py tests/test_evidence_import_wizard_cli.py
uv run ty check
uv run python scripts/check_release_readiness.py
git diff --check
```

Expected: all commands pass.
