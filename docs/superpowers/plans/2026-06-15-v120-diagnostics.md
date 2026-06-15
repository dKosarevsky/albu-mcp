# v1.2 Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an MCP diagnostics tool/resource pair and release it as `v1.2.0`.

**Architecture:** Put diagnostics contracts and checks in `src/albumentationsx_mcp/diagnostics.py`. Keep `server.py` as
a registration adapter that passes settings and the declared public MCP surface into the diagnostics service. Extend the
golden eval runner with one lightweight diagnostics scenario before preview-heavy scenarios.

**Tech Stack:** Python 3.10+, Pydantic, FastMCP, pytest fixtures/parametrization, ruff, ty, uv, GitHub Actions release
automation, MCP Registry publisher workflow.

---

## File Structure

- Create: `src/albumentationsx_mcp/diagnostics.py`
  Owns `DiagnosticsService`, `PublicSurface`, typed check models, diagnostics guide builder, and write-probe logic.
- Create: `tests/test_diagnostics.py`
  Unit tests for status aggregation, artifact root probe behavior, and missing allowed root warnings.
- Modify: `src/albumentationsx_mcp/server.py`
  Register `diagnose_environment`, `albumentationsx://diagnostics/guide`, and capabilities entries.
- Modify: `src/albumentationsx_mcp/workflows.py`
  Add a host example named `diagnostics`.
- Modify: `tests/test_server.py`, `tests/test_mcp_stdio.py`, `tests/test_golden_evals.py`
  Guard MCP surface and executable diagnostics scenario.
- Modify: `evals/golden_mcp_scenarios.yaml`, `scripts/run_golden_evals.py`
  Add and run `diagnostics_resource_flow`.
- Modify: `README.md`, `docs/INSTALL.md`, `docs/USAGE.md`, `docs/RECIPES.md`, `CHANGELOG.md`, `server.json`,
  `pyproject.toml`, `uv.lock`, and contract snapshot fixtures for `v1.2.0`.

## Task 1: Plan Commit

- [ ] **Step 1: Add design and plan docs**

Write `docs/superpowers/specs/2026-06-15-v120-diagnostics-design.md` and this plan file.

- [ ] **Step 2: Commit docs**

Run:

```bash
git add docs/superpowers/specs/2026-06-15-v120-diagnostics-design.md docs/superpowers/plans/2026-06-15-v120-diagnostics.md
git commit -m "docs: plan v1.2 diagnostics"
```

Expected: commit succeeds with only the two planning docs.

## Task 2: RED Diagnostics Tests

- [ ] **Step 1: Add failing unit tests**

Create `tests/test_diagnostics.py` with tests that import `DiagnosticsService`, `PublicSurface`, and
`build_diagnostics_guide`, then assert:

```python
def test_diagnostics_reports_ok_environment(tmp_path: Path) -> None:
    report = DiagnosticsService(...).diagnose(include_write_probe=True)
    assert report.status == "ok"
    assert "albumentationsx_import" in {check.code for check in report.checks}
    assert report.environment.write_probe == "passed"
    assert not (tmp_path / "artifacts" / ".albumentationsx-mcp-diagnostics-probe").exists()


def test_diagnostics_warns_for_missing_allowed_root(tmp_path: Path) -> None:
    report = DiagnosticsService(...missing root...).diagnose(include_write_probe=False)
    assert report.status == "warning"
    assert "allowed_root_missing" in {check.code for check in report.checks}
    assert any("--allowed-root" in action for action in report.next_actions)
```

- [ ] **Step 2: Add failing server/eval tests**

Update server and stdio tests to expect `diagnose_environment`, `albumentationsx://diagnostics/guide`, and the
diagnostics host example. Update golden eval tests to expect `diagnostics_resource_flow` and runner support.

- [ ] **Step 3: Verify RED**

Run:

```bash
uv run pytest tests/test_diagnostics.py tests/test_server.py tests/test_mcp_stdio.py tests/test_golden_evals.py -q
```

Expected: fails because `albumentationsx_mcp.diagnostics` and `diagnose_environment` do not exist yet.

## Task 3: GREEN Diagnostics Implementation

- [ ] **Step 1: Implement diagnostics module**

Create `src/albumentationsx_mcp/diagnostics.py` with:

```python
class PublicSurface(StrictModel):
    tools: list[str]
    prompts: list[str]
    workflow_resources: list[str]


class DiagnosticCheck(StrictModel):
    code: str
    status: Literal["ok", "warning", "error"]
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class DiagnosticsEnvironment(StrictModel):
    albumentationsx_version: str | None
    allowed_roots: list[str]
    artifact_root: str
    max_preview_runs: int
    write_probe: Literal["not_run", "passed", "failed"]


class DiagnosticsReport(StrictModel):
    status: Literal["ok", "warning", "error"]
    checks: list[DiagnosticCheck]
    warnings: list[str]
    next_actions: list[str]
    environment: DiagnosticsEnvironment
```

`DiagnosticsService.diagnose()` checks imports, path existence, artifact root creation/writeability, and required public
surface entries.

- [ ] **Step 2: Wire server**

In `server.py`, define one shared public-surface tuple/list block, reuse it in `capabilities_resource`, register:

```python
@mcp.resource("albumentationsx://diagnostics/guide")
def diagnostics_guide_resource() -> str:
    return build_diagnostics_guide().model_dump_json()


@mcp.tool(name="diagnose_environment")
def diagnose_environment_tool(include_write_probe: bool = True) -> dict[str, Any]:
    return diagnostics_service.diagnose(include_write_probe=include_write_probe).model_dump(mode="json")
```

- [ ] **Step 3: Verify GREEN**

Run:

```bash
uv run pytest tests/test_diagnostics.py tests/test_server.py tests/test_mcp_stdio.py tests/test_golden_evals.py -q
```

Expected: all selected tests pass.

- [ ] **Step 4: Commit implementation**

Run:

```bash
git add src/albumentationsx_mcp/diagnostics.py src/albumentationsx_mcp/server.py src/albumentationsx_mcp/workflows.py tests/test_diagnostics.py tests/test_server.py tests/test_mcp_stdio.py tests/test_golden_evals.py
git commit -m "feat: add environment diagnostics"
```

Expected: commit succeeds.

## Task 4: Golden Eval and Docs

- [ ] **Step 1: Extend golden eval runner**

Add `diagnostics_resource_flow` to `evals/golden_mcp_scenarios.yaml`. Add `_run_diagnostics_smoke()` to
`scripts/run_golden_evals.py` so it reads `albumentationsx://diagnostics/guide`, calls `diagnose_environment`, and
asserts structured `status`, `checks`, `environment`, and `next_actions`.

- [ ] **Step 2: Update public docs**

Document the new tool/resource in README, install troubleshooting, usage, and recipes. Add a changelog entry under
Unreleased.

- [ ] **Step 3: Update snapshots**

Run:

```bash
uv run python scripts/export_mcp_contract.py --output tests/fixtures/snapshots/mcp_contract.json
```

Expected: snapshot includes `diagnose_environment`, `albumentationsx://diagnostics/guide`, and diagnostics host example.

- [ ] **Step 4: Verify docs/eval**

Run:

```bash
uv run pytest tests/test_golden_evals.py tests/test_project_scaffolding.py tests/test_mcp_contract_snapshot.py -q
uv run python scripts/run_golden_evals.py
```

Expected: tests and golden evals pass.

- [ ] **Step 5: Commit eval/docs**

Run:

```bash
git add README.md docs/INSTALL.md docs/USAGE.md docs/RECIPES.md CHANGELOG.md evals/golden_mcp_scenarios.yaml scripts/run_golden_evals.py tests/fixtures/snapshots/mcp_contract.json tests/test_project_scaffolding.py
git commit -m "test: cover diagnostics golden eval"
```

Expected: commit succeeds.

## Task 5: Release v1.2.0

- [ ] **Step 1: Bump release metadata**

Update `pyproject.toml`, `server.json`, `uv.lock`, README release notes, and CHANGELOG for `1.2.0`.

- [ ] **Step 2: Run full verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv run python scripts/check_release_version.py v1.2.0
uv build
```

Expected: every command exits 0.

- [ ] **Step 3: Commit release**

Run:

```bash
git add pyproject.toml server.json uv.lock README.md CHANGELOG.md
git commit -m "chore: release v1.2.0"
```

Expected: commit succeeds.

- [ ] **Step 4: Tag and push**

Run:

```bash
git tag v1.2.0
git push origin main
git push origin v1.2.0
```

Expected: branch and tag push succeed.

- [ ] **Step 5: Watch CI and release**

Run:

```bash
gh run list --limit 5
gh run watch <latest-release-run-id> --exit-status
```

Expected: CI/release workflow succeeds. If publication needs time, poll PyPI JSON and MCP Registry after the workflow.

## Self-Review

- Spec coverage: diagnostics tool, guide resource, public surface entries, docs, golden eval, and release are covered.
- Placeholder scan: no TBD/TODO/fill-in placeholders.
- Type consistency: `diagnose_environment`, `DiagnosticsReport`, `DiagnosticCheck`, and `PublicSurface` names match across
  tasks.
