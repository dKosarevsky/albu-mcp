# V1.4 Host Smoke Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only `run_host_smoke_check` MCP tool that tells hosts whether they can safely proceed to a small preview and gives them the next request shape.

**Architecture:** Keep diagnostics, recipes, pipeline validation, and FastMCP registration separated. Add `host_smoke.py` as a pure report builder that consumes typed diagnostics, recipe, and validation results; `server.py` only wires dependencies.

**Tech Stack:** Python 3.10+, Pydantic strict models, FastMCP, pytest, ruff, ty, uv.

---

## File Structure

- Create `src/albumentationsx_mcp/host_smoke.py`: typed `HostSmokeReport` models and `build_host_smoke_report()`.
- Create `tests/test_host_smoke.py`: unit coverage for preview-ready and diagnostics-blocked reports.
- Modify `src/albumentationsx_mcp/server.py`: add `_PUBLIC_TOOLS` entry and FastMCP tool wrapper.
- Modify `tests/test_server.py` and `tests/test_mcp_stdio.py`: assert public tool registration.
- Modify `scripts/run_golden_evals.py`, `evals/golden_mcp_scenarios.yaml`, and `tests/test_golden_evals.py`: add executable stdio smoke coverage.
- Modify `scripts/export_mcp_contract.py` output fixture via script and `tests/fixtures/snapshots/mcp_contract.json`.
- Modify `scripts/export_output_contracts.py`, `tests/test_output_contract_snapshots.py`, and `tests/fixtures/snapshots/output_contracts.json`.
- Modify `README.md`, `docs/INSTALL.md`, `docs/USAGE.md`, and `docs/RECIPES.md` to document the new preflight.

## Task 1: RED Unit Tests

**Files:**
- Create: `tests/test_host_smoke.py`

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path

from albumentationsx_mcp.diagnostics import DiagnosticsService
from albumentationsx_mcp.host_smoke import build_host_smoke_report
from albumentationsx_mcp.pipeline import PipelineService
from albumentationsx_mcp.recipes import recommend_recipe
from albumentationsx_mcp.catalog import TransformCatalog

def test_host_smoke_report_is_preview_ready_when_diagnostics_and_validation_pass(tmp_path: Path) -> None:
    catalog = TransformCatalog()
    pipeline_service = PipelineService(catalog)
    recipe = recommend_recipe("classification", intensity="low", targets=["image"])
    validation = pipeline_service.validate_pipeline(recipe.pipeline)
    diagnostics = DiagnosticsService(
        allowed_roots=[tmp_path],
        artifact_root=tmp_path / "artifacts",
        max_preview_runs=100,
        public_surface=complete_public_surface_with_host_smoke(),
    ).diagnose(include_write_probe=True)

    report = build_host_smoke_report(diagnostics=diagnostics, recipe=recipe, validation=validation)

    assert report.status == "ok"
    assert report.preview_ready is True
    assert [check.code for check in report.checks] == [
        "diagnostics",
        "recipe_recommendation",
        "pipeline_validation",
        "preview_request_template",
    ]
    assert report.preview_request_template is not None
    assert report.preview_request_template.tool == "render_preview_batch"
    assert report.preview_request_template.request["variants_per_image"] == 1
    assert report.preview_request_template.request["seed"] == 0
    assert report.preview_request_template.request["input_paths"] == [str(tmp_path.resolve() / "example.jpg")]

def test_host_smoke_report_blocks_preview_when_diagnostics_warn(tmp_path: Path) -> None:
    catalog = TransformCatalog()
    pipeline_service = PipelineService(catalog)
    recipe = recommend_recipe("classification", intensity="low", targets=["image"])
    validation = pipeline_service.validate_pipeline(recipe.pipeline)
    diagnostics = DiagnosticsService(
        allowed_roots=[tmp_path / "missing"],
        artifact_root=tmp_path / "artifacts",
        max_preview_runs=100,
        public_surface=complete_public_surface_with_host_smoke(),
    ).diagnose(include_write_probe=False)

    report = build_host_smoke_report(diagnostics=diagnostics, recipe=recipe, validation=validation)

    assert report.status == "warning"
    assert report.preview_ready is False
    assert report.preview_request_template is None
    assert [action.code for action in report.remediation_actions] == ["fix_allowed_root"]
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/test_host_smoke.py -q`

Expected: FAIL because `albumentationsx_mcp.host_smoke` does not exist.

## Task 2: GREEN Host Smoke Builder

**Files:**
- Create: `src/albumentationsx_mcp/host_smoke.py`
- Modify: `tests/test_host_smoke.py`

- [ ] **Step 1: Implement strict models and builder**

Add `HostSmokeCheck`, `HostPreviewRequestTemplate`, `HostSmokeReport`, and `build_host_smoke_report()`. Use diagnostics
status as the aggregate status unless validation fails, in which case the report is `error`. Set `preview_ready` only when
diagnostics status is `ok` and validation is valid.

- [ ] **Step 2: Add local test helper**

Add `complete_public_surface_with_host_smoke()` in `tests/test_host_smoke.py` with `run_host_smoke_check` in tools and the
same prompts/resources as diagnostics tests.

- [ ] **Step 3: Verify GREEN**

Run: `uv run pytest tests/test_host_smoke.py -q`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/albumentationsx_mcp/host_smoke.py tests/test_host_smoke.py
git commit -m "feat: add host smoke report builder"
```

## Task 3: Public MCP Tool

**Files:**
- Modify: `src/albumentationsx_mcp/server.py`
- Modify: `tests/test_server.py`
- Modify: `tests/test_mcp_stdio.py`

- [ ] **Step 1: Write RED assertions**

Add `run_host_smoke_check` to server and stdio expected tool sets before changing `server.py`.

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/test_server.py tests/test_mcp_stdio.py -q`

Expected: FAIL because the new tool is not registered.

- [ ] **Step 3: Register tool**

Import `build_host_smoke_report`, add `run_host_smoke_check` to `_PUBLIC_TOOLS`, and register a FastMCP tool that calls
diagnostics, recipe recommendation, validation, and the builder.

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/test_server.py tests/test_mcp_stdio.py tests/test_host_smoke.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/albumentationsx_mcp/server.py tests/test_server.py tests/test_mcp_stdio.py
git commit -m "feat: expose host smoke check tool"
```

## Task 4: Golden Evals And Snapshots

**Files:**
- Modify: `evals/golden_mcp_scenarios.yaml`
- Modify: `scripts/run_golden_evals.py`
- Modify: `tests/test_golden_evals.py`
- Modify: `scripts/export_mcp_contract.py` output fixture
- Modify: `scripts/export_output_contracts.py`
- Modify: `tests/test_output_contract_snapshots.py`
- Modify: `tests/fixtures/snapshots/mcp_contract.json`
- Modify: `tests/fixtures/snapshots/output_contracts.json`

- [ ] **Step 1: Add RED golden assertions**

Add `host_smoke: true` to `client_smoke_resource_flow`, update tests to expect runner support, and assert
`run_host_smoke_check` returns `preview_ready: true` and a `render_preview_batch` template.

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/test_golden_evals.py -q`

Expected: FAIL until runner support is added.

- [ ] **Step 3: Implement runner support and regenerate snapshots**

Call `run_host_smoke_check` in `_run_client_smoke()`. Regenerate snapshots:

```bash
uv run python scripts/export_mcp_contract.py --output tests/fixtures/snapshots/mcp_contract.json
uv run python scripts/export_output_contracts.py --output tests/fixtures/snapshots/output_contracts.json
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/test_golden_evals.py tests/test_mcp_contract_snapshot.py tests/test_output_contract_snapshots.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add evals/golden_mcp_scenarios.yaml scripts/run_golden_evals.py scripts/export_output_contracts.py tests/test_golden_evals.py tests/test_output_contract_snapshots.py tests/fixtures/snapshots/mcp_contract.json tests/fixtures/snapshots/output_contracts.json
git commit -m "test: cover host smoke output contracts"
```

## Task 5: Docs And Release

**Files:**
- Modify: `README.md`, `docs/INSTALL.md`, `docs/USAGE.md`, `docs/RECIPES.md`, `tests/test_project_scaffolding.py`
- Modify: `CHANGELOG.md`, `pyproject.toml`, `server.json`, `uv.lock`, `docs/INSTALL.md`

- [ ] **Step 1: Document host smoke workflow and add scaffolding assertions**

Mention `run_host_smoke_check`, `preview_ready`, and `preview_request_template` in README/install/usage/recipes. Add a
docs scaffolding assertion that those docs mention the new tool.

- [ ] **Step 2: Verify docs**

Run: `uv run pytest tests/test_project_scaffolding.py -q`

Expected: PASS.

- [ ] **Step 3: Bump release**

Set package and `server.json` versions to `1.4.0`, move changelog entries under `## 1.4.0 - 2026-06-15`, and run
`uv lock`.

- [ ] **Step 4: Full verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv run python scripts/check_release_version.py v1.4.0
uv build
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit, tag, push, and publish metadata**

```bash
git add README.md docs/INSTALL.md docs/USAGE.md docs/RECIPES.md tests/test_project_scaffolding.py CHANGELOG.md pyproject.toml server.json uv.lock
git commit -m "chore: release v1.4.0"
git tag v1.4.0
git push origin main
git push origin v1.4.0
```

Watch CI and Release, dispatch `publish-mcp.yml`, and verify the published package with:

```bash
uvx --from albumentationsx-mcp==1.4.0 --refresh-package albumentationsx-mcp albumentationsx-mcp --help
```

## Self-Review

- Spec coverage: each public contract and safety requirement maps to Tasks 1-5.
- Placeholder scan: no placeholder markers or open-ended implementation instructions remain.
- Type consistency: `HostSmokeReport`, `HostSmokeCheck`, `HostPreviewRequestTemplate`, and `run_host_smoke_check` are used consistently.
