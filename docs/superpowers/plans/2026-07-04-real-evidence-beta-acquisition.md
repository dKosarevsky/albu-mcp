# Real Evidence Beta Acquisition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one no-write product cycle that helps operators acquire real P0 host evidence and external beta validation, then keeps product-depth work gated until those records exist.

**Architecture:** Add a focused `acquisition_cycle` domain module that composes existing evidence, beta, trust, and RC helpers. Wire it through `albu-mcp activation acquisition-cycle` so operators can emit JSON or a markdown artifact folder. Update usage and the governed iteration report to document that the next 100 blind iterations stop at external gates.

**Tech Stack:** Python 3.10+, argparse CLI, pytest subprocess CLI tests, ruff, ty, uv.

---

### Task 1: Real Evidence Acquisition Sprint Pack

**Files:**
- Create: `src/albumentationsx_mcp/acquisition_cycle.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_real_evidence_beta_acquisition_cli.py`

- [ ] **Step 1: Write the failing test**

Add `test_activation_acquisition_cycle_reports_real_evidence_lane` that creates empty host and beta records, runs:

```bash
python -m albumentationsx_mcp activation acquisition-cycle --host Codex --host-records <tmp>/HOST_MANUAL_RUNS.json --beta-records <tmp>/BETA_VALIDATION_RECORDS.json --format json
```

Expected assertions:

```python
assert payload["cycle_status"] == "blocked"
assert payload["writes_records"] is False
assert payload["lane_count"] == 3
assert payload["lanes"][0]["id"] == "real_evidence_acquisition"
assert payload["lanes"][0]["status"] == "blocked_until_real_host_evidence"
assert "albu-mcp evidence transcript-template" in payload["lanes"][0]["next_commands"]
assert "albu-mcp evidence proof-runner" in payload["lanes"][0]["next_commands"]
assert "albu-mcp evidence import-manifest" in payload["lanes"][0]["next_commands"]
```

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_real_evidence_beta_acquisition_cli.py::test_activation_acquisition_cycle_reports_real_evidence_lane -q
```

Expected: fail with missing `acquisition-cycle` command or missing module import.

- [ ] **Step 3: Implement minimal real-evidence lane**

Create `AcquisitionCycleRequest`, `build_acquisition_cycle`, and a real-evidence lane that reads `build_evidence_proof_status`. Add CLI parser and handler under activation. The handler returns JSON for `--format json` and text summary for `--format text`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_real_evidence_beta_acquisition_cli.py::test_activation_acquisition_cycle_reports_real_evidence_lane -q
uv run ruff check src/albumentationsx_mcp/acquisition_cycle.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_beta_acquisition_cli.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/albumentationsx_mcp/acquisition_cycle.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_beta_acquisition_cli.py
git commit -m "feat: add real evidence acquisition cycle"
```

### Task 2: Beta Acquisition Sprint Pack

**Files:**
- Modify: `src/albumentationsx_mcp/acquisition_cycle.py`
- Modify: `src/albumentationsx_mcp/cli.py`
- Test: `tests/test_real_evidence_beta_acquisition_cli.py`

- [ ] **Step 1: Write the failing test**

Add `test_activation_acquisition_cycle_writes_three_acquisition_artifacts`. It runs:

```bash
python -m albumentationsx_mcp activation acquisition-cycle --host Codex --host-records <host> --beta-records <beta> --output-dir <dir> --format markdown
```

Expected files:

```python
{
    "acquisition-cycle-index.md",
    "real-evidence-acquisition.md",
    "beta-acquisition.md",
    "product-depth-gate.md",
}
```

Expected content includes:

```python
assert "# Real Evidence Beta Acquisition Cycle" in index
assert "Writes records: `false`" in index
assert "albu-mcp beta loop-pack" in beta
assert "albu-mcp beta response-template" in beta
assert "albu-mcp beta response-import-dir" in beta
assert "Official Albumentations MCP docs" in beta
```

- [ ] **Step 2: Verify RED**

Run the single new test. Expected: fail because artifacts are not implemented.

- [ ] **Step 3: Implement artifact rendering**

Add `build_acquisition_cycle_artifacts`, markdown renderers, JSON rendering, and CLI output directory writes. Use existing beta report data from `build_beta_validation_report(validate_beta_validation_records(...))`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_real_evidence_beta_acquisition_cli.py -q
uv run ruff check src/albumentationsx_mcp/acquisition_cycle.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_beta_acquisition_cli.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/albumentationsx_mcp/acquisition_cycle.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_beta_acquisition_cli.py
git commit -m "feat: add beta acquisition artifacts"
```

### Task 3: Product Depth Gate and Governed Stop

**Files:**
- Modify: `src/albumentationsx_mcp/acquisition_cycle.py`
- Modify: `docs/USAGE.md`
- Modify: `scripts/export_governed_iteration_execution_report.py`
- Modify: `tests/test_real_evidence_beta_acquisition_cli.py`
- Modify: `tests/test_governed_iteration_execution_report.py`
- Modify: `tests/test_cli_evidence_beta.py`
- Regenerate: `docs/GOVERNED_100_ITERATION_REPORT.md`

- [ ] **Step 1: Write the failing tests**

Extend CLI tests so the product-depth lane reports:

```python
assert payload["lanes"][2]["id"] == "product_depth_gate"
assert payload["lanes"][2]["implementation_allowed"] is False
assert payload["lanes"][2]["blocked_reasons"] == [
    "p0_host_evidence_missing_or_blocked",
    "beta_validation_incomplete",
]
assert payload["next_action"] == "run_real_evidence_acquisition"
```

Update governed report tests to expect iteration `13`, completed paths `66`, completed plan points `66`, and the three new cycle paths plus the 100-iteration stop.

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_real_evidence_beta_acquisition_cli.py tests/test_governed_iteration_execution_report.py -q
```

Expected: fail on product-depth gate fields and governed counts.

- [ ] **Step 3: Implement product-depth gate and docs**

Add product-depth lane with explicit `implementation_allowed` and `blocked_reasons` composed from proof status and beta report. Update `docs/USAGE.md` operator CLI list and report-only list. Update governed report generator and regenerate the committed markdown.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_real_evidence_beta_acquisition_cli.py tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py::test_readme_and_usage_document_operator_cli -q
uv run ruff check src/albumentationsx_mcp/acquisition_cycle.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_beta_acquisition_cli.py tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py scripts/export_governed_iteration_execution_report.py
uv run ruff format --check src/albumentationsx_mcp/acquisition_cycle.py src/albumentationsx_mcp/cli.py tests/test_real_evidence_beta_acquisition_cli.py tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py scripts/export_governed_iteration_execution_report.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/albumentationsx_mcp/acquisition_cycle.py src/albumentationsx_mcp/cli.py docs/USAGE.md docs/GOVERNED_100_ITERATION_REPORT.md scripts/export_governed_iteration_execution_report.py tests/test_real_evidence_beta_acquisition_cli.py tests/test_governed_iteration_execution_report.py tests/test_cli_evidence_beta.py
git commit -m "docs: record acquisition cycle stop"
```

### Final Verification

- [ ] Run `uv run pytest -q`
- [ ] Run `uv run ruff check .`
- [ ] Run `uv run ruff format --check .`
- [ ] Run `uv run ty check`
- [ ] Run `uv run python scripts/check_release_readiness.py`
- [ ] Run `uv build`
- [ ] Push branch, open PR, wait for CI, merge, sync `main`.
