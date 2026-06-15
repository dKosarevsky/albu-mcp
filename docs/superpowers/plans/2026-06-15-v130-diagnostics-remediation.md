# v1.3 Diagnostics Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add machine-readable diagnostics severity and remediation actions, snapshot the representative outputs, and
release `v1.3.0`.

**Architecture:** Keep all runtime behavior inside `src/albumentationsx_mcp/diagnostics.py`. Extend
`scripts/export_output_contracts.py` with deterministic diagnostics fixtures and normalize local paths plus package
versions. Do not add a new MCP tool or resource.

**Tech Stack:** Python 3.10+, Pydantic strict models, pytest, ruff, ty, uv, FastMCP, GitHub Actions release automation.

---

## File Structure

- Modify: `src/albumentationsx_mcp/diagnostics.py`
  Add `DiagnosticSeverity`, `DiagnosticRemediationAction`, `severity` on checks, and structured remediation generation.
- Modify: `tests/test_diagnostics.py`
  Add RED assertions for severity and remediation action codes.
- Modify: `scripts/export_output_contracts.py`
  Add deterministic healthy and missing-root diagnostics outputs.
- Modify: `tests/test_output_contract_snapshots.py`
  Assert diagnostics snapshots exist and remain canonical.
- Modify: `tests/fixtures/snapshots/output_contracts.json`
  Include diagnostics output contract fixtures.
- Modify: docs and release metadata for `v1.3.0`.

## Task 1: Plan Commit

- [ ] **Step 1: Add design and plan docs**

Create:

```text
docs/superpowers/specs/2026-06-15-v130-diagnostics-remediation-design.md
docs/superpowers/plans/2026-06-15-v130-diagnostics-remediation.md
```

- [ ] **Step 2: Commit docs**

Run:

```bash
git add docs/superpowers/specs/2026-06-15-v130-diagnostics-remediation-design.md docs/superpowers/plans/2026-06-15-v130-diagnostics-remediation.md
git commit -m "docs: plan v1.3 diagnostics remediation"
```

## Task 2: RED Tests

- [ ] **Step 1: Add failing diagnostics assertions**

Update `tests/test_diagnostics.py` so:

```python
assert {check.severity for check in report.checks} == {"info"}
assert [action.code for action in report.remediation_actions] == ["proceed_with_preview_smoke"]
assert "fix_allowed_root" in {action.code for action in report.remediation_actions}
assert "allowed_root_missing" in action.check_codes
```

- [ ] **Step 2: Add failing output snapshot guards**

Update `tests/test_output_contract_snapshots.py`:

```python
assert "diagnose_environment_ok" in expected
assert "diagnose_environment_missing_allowed_root" in expected
assert "remediation_actions" in expected["diagnose_environment_missing_allowed_root"]
```

- [ ] **Step 3: Verify RED**

Run:

```bash
uv run pytest tests/test_diagnostics.py tests/test_output_contract_snapshots.py -q
```

Expected: fail because `severity`, `remediation_actions`, and diagnostics snapshots do not exist.

## Task 3: GREEN Runtime Contract

- [ ] **Step 1: Extend diagnostics models**

Add:

```python
DiagnosticSeverity = Literal["info", "medium", "high", "critical"]

class DiagnosticRemediationAction(StrictModel):
    code: str
    severity: DiagnosticSeverity
    check_codes: list[str] = Field(default_factory=list)
    summary: str
    command_hint: str | None = None
    docs_uri: str | None = None
```

Add `severity: DiagnosticSeverity = "info"` to `DiagnosticCheck` and
`remediation_actions: list[DiagnosticRemediationAction]` to `DiagnosticsReport`.

- [ ] **Step 2: Generate structured remediation**

Replace `_next_actions(checks)` internals with `_remediation_actions(checks)`, then derive `next_actions` from
`action.summary`. Map codes to command hints and `albumentationsx://diagnostics/guide`.

- [ ] **Step 3: Verify GREEN**

Run:

```bash
uv run pytest tests/test_diagnostics.py -q
```

Expected: diagnostics tests pass.

- [ ] **Step 4: Commit runtime contract**

Run:

```bash
git add src/albumentationsx_mcp/diagnostics.py tests/test_diagnostics.py
git commit -m "feat: add structured diagnostics remediation"
```

## Task 4: Output Snapshots and Docs

- [ ] **Step 1: Extend output contract exporter**

In `scripts/export_output_contracts.py`, add healthy and missing-root diagnostics reports. Normalize:

- paths under `<OUTPUT_CONTRACT_ROOT>`;
- `albumentationsx_version`;
- package/module versions inside check details.

- [ ] **Step 2: Regenerate snapshot**

Run:

```bash
uv run python scripts/export_output_contracts.py --output tests/fixtures/snapshots/output_contracts.json
```

- [ ] **Step 3: Update docs**

Document `severity` and `remediation_actions` in README, usage, install troubleshooting, and changelog.

- [ ] **Step 4: Verify snapshot/docs**

Run:

```bash
uv run pytest tests/test_output_contract_snapshots.py tests/test_project_scaffolding.py -q
uv run python scripts/run_golden_evals.py
```

- [ ] **Step 5: Commit snapshots/docs**

Run:

```bash
git add scripts/export_output_contracts.py tests/test_output_contract_snapshots.py tests/fixtures/snapshots/output_contracts.json README.md docs/INSTALL.md docs/USAGE.md CHANGELOG.md
git commit -m "test: snapshot diagnostics outputs"
```

## Task 5: Release v1.3.0

- [ ] **Step 1: Bump release metadata**

Update `pyproject.toml`, `server.json`, `uv.lock`, `docs/INSTALL.md`, and `CHANGELOG.md` for `1.3.0`.

- [ ] **Step 2: Full verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv run python scripts/check_release_version.py v1.3.0
uv build
```

- [ ] **Step 3: Commit, tag, push, and publish registry metadata**

Run:

```bash
git add pyproject.toml server.json uv.lock docs/INSTALL.md CHANGELOG.md
git commit -m "chore: release v1.3.0"
git tag v1.3.0
git push origin main
git push origin v1.3.0
```

Watch CI/release, dispatch `publish-mcp.yml`, then smoke the published package with:

```bash
uvx --from albumentationsx-mcp==1.3.0 albumentationsx-mcp --help
```

## Self-Review

- Spec coverage: severity, remediation codes, output snapshots, docs, and release are covered.
- Placeholder scan: no TBD/TODO/fill-in placeholders.
- Type consistency: names match between spec, tests, implementation, and snapshot plan.
