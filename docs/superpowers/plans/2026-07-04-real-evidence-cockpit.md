# Real Evidence Cockpit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a no-write real evidence execution cockpit that guides one host run from setup probe through manifest import and post-import review.

**Architecture:** Add a focused `evidence_cockpit` domain module that composes existing evidence proof status, transcript template, manifest import, trust transition, and RC preview commands. Wire it as `albu-mcp activation evidence-cockpit` with JSON/markdown output and optional artifact folder writes. Update usage and governed iteration reporting to document that further blind product work remains blocked by external records.

**Tech Stack:** Python 3.10+, argparse CLI, pytest subprocess tests, ruff, ty, uv.

---

### Task 1: Evidence Cockpit JSON Control Surface

**Files:**
- Create: `src/albumentationsx_mcp/evidence_cockpit.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_real_evidence_cockpit_cli.py`

- [ ] **Step 1: Write the failing test**

Create a subprocess test that runs:

```bash
python -m albumentationsx_mcp activation evidence-cockpit --host Codex --host-records <tmp>/HOST_MANUAL_RUNS.json --beta-records <tmp>/BETA_VALIDATION_RECORDS.json --format json
```

Assert:

```python
assert payload["cockpit_status"] == "blocked"
assert payload["writes_records"] is False
assert payload["host"] == "Codex"
assert payload["phase_count"] == 4
assert [phase["id"] for phase in payload["phases"]] == [
    "setup_probe",
    "session_capture",
    "manifest_import",
    "post_import_review",
]
assert payload["phases"][0]["next_commands"][0].startswith("albu-mcp host setup-probe --host Codex")
assert "albu-mcp evidence transcript-template" in payload["phases"][1]["next_commands"]
assert "albu-mcp evidence proof-runner" in payload["phases"][2]["next_commands"]
assert payload["next_action"] == "run_setup_probe"
```

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_real_evidence_cockpit_cli.py::test_activation_evidence_cockpit_reports_four_no_write_phases -q
```

Expected: fail because `evidence-cockpit` command is missing.

- [ ] **Step 3: Implement minimal control surface**

Add `EvidenceCockpitRequest`, `build_evidence_cockpit`, and four phase builders. Add the activation parser and handler. The command must not write records unless `--output-dir` is explicitly used for generated artifacts in Task 2.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_real_evidence_cockpit_cli.py::test_activation_evidence_cockpit_reports_four_no_write_phases -q
uv run ruff check src/albumentationsx_mcp/evidence_cockpit.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_cockpit_cli.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/albumentationsx_mcp/evidence_cockpit.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_cockpit_cli.py
git commit -m "feat: add real evidence cockpit"
```

### Task 2: Evidence Cockpit Artifact Pack

**Files:**
- Modify: `src/albumentationsx_mcp/evidence_cockpit.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_real_evidence_cockpit_cli.py`

- [ ] **Step 1: Write the failing test**

Add a subprocess test for:

```bash
python -m albumentationsx_mcp activation evidence-cockpit --host Codex --host-records <host> --beta-records <beta> --output-dir <dir> --format markdown
```

Expected files:

```python
{
    "evidence-cockpit-index.md",
    "setup-probe.md",
    "session-capture.md",
    "manifest-import.md",
    "post-import-review.md",
}
```

Expected content includes `# Real Evidence Execution Cockpit`, `Writes records: `false``, `Reviewer-observed real MCP host UI`, `albu-mcp evidence import-manifest`, and `albu-mcp evidence transition-pack`.

- [ ] **Step 2: Verify RED**

Run the single artifact test. Expected: fail because output directory writing is missing.

- [ ] **Step 3: Implement artifact rendering**

Add `build_evidence_cockpit_artifacts`, markdown renderers, JSON rendering, and handler output-dir writes.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_real_evidence_cockpit_cli.py -q
uv run ruff check src/albumentationsx_mcp/evidence_cockpit.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_cockpit_cli.py
uv run ruff format --check src/albumentationsx_mcp/evidence_cockpit.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_cockpit_cli.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/albumentationsx_mcp/evidence_cockpit.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_cockpit_cli.py
git commit -m "feat: add evidence cockpit artifacts"
```

### Task 3: Usage Docs and Governed Stop

**Files:**
- Modify: `docs/USAGE.md`
- Modify: `scripts/export_governed_iteration_execution_report.py`
- Modify: `tests/test_cli_evidence_beta.py`
- Modify: `tests/test_governed_iteration_execution_report.py`
- Regenerate: `docs/GOVERNED_100_ITERATION_REPORT.md`

- [ ] **Step 1: Write the failing tests**

Update usage sync test to expect `albu-mcp activation evidence-cockpit`. Update governed report tests to expect iteration `14`, completed paths `70`, completed plan points `70`, and terms: `Evidence Cockpit Control path`, `Evidence Cockpit Artifact path`, `Post-Import Review path`, and `the fourteenth requested follow-up loop`.

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
```

Expected: fail on old counts and missing usage term.

- [ ] **Step 3: Implement docs/report updates**

Add `activation evidence-cockpit` to `docs/USAGE.md`, update report generator, regenerate `docs/GOVERNED_100_ITERATION_REPORT.md`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_real_evidence_cockpit_cli.py tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
uv run ruff check src/albumentationsx_mcp/evidence_cockpit.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_cockpit_cli.py tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py scripts/export_governed_iteration_execution_report.py
uv run ruff format --check src/albumentationsx_mcp/evidence_cockpit.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_cockpit_cli.py tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py scripts/export_governed_iteration_execution_report.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add docs/USAGE.md docs/GOVERNED_100_ITERATION_REPORT.md scripts/export_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py tests/test_governed_iteration_execution_report.py
git commit -m "docs: record evidence cockpit stop"
```

### Final Verification

- [ ] Run `uv run pytest -q`
- [ ] Run `uv run ruff check .`
- [ ] Run `uv run ruff format --check .`
- [ ] Run `uv run ty check`
- [ ] Run `uv run python scripts/check_release_readiness.py`
- [ ] Run `uv build`
- [ ] Push branch, open PR, wait for CI, merge, sync `main`.
