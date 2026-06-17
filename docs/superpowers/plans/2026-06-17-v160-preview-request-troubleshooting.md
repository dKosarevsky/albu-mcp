# v1.6 Preview Request Troubleshooting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only `validate_preview_request` MCP tool that returns structured remediation for common preview request failures before rendering.

**Architecture:** Implement a focused `preview_validation.py` domain module with typed report models and `PreviewRequestValidator`. Wire it through `server.py`, diagnostics public surface, contract snapshots, output snapshots, docs, and golden evals. Keep rendering behavior unchanged.

**Tech Stack:** Python 3.10+, Pydantic strict models, FastMCP, pytest, golden MCP stdio evals, ruff, ty, uv.

---

### Task 1: Domain Validator Tests

**Files:**
- Create: `tests/test_preview_validation.py`
- Create: `src/albumentationsx_mcp/preview_validation.py`

- [ ] **Step 1: Write RED tests**

Create `tests/test_preview_validation.py` with tests for:

```python
def test_validate_preview_request_reports_missing_input_path(tmp_path: Path) -> None:
    validator = _validator(tmp_path)
    request = _request(tmp_path / "images" / "missing.png")

    report = validator.validate(request, target=TargetSpec(targets=["image"]))

    assert report.valid is False
    assert report.status == "error"
    assert "input_path_missing" in {check.code for check in report.checks}
    assert any(action.code == "fix_input_paths" for action in report.remediation_actions)
```

Also cover:

```python
def test_validate_preview_request_reports_outside_allowed_root(tmp_path: Path) -> None: ...
def test_validate_preview_request_reports_annotation_count_mismatch(tmp_path: Path) -> None: ...
def test_validate_preview_request_reports_mask_path_missing(tmp_path: Path) -> None: ...
def test_validate_preview_request_accepts_valid_request(tmp_path: Path) -> None: ...
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/test_preview_validation.py -q`

Expected: FAIL because `albumentationsx_mcp.preview_validation` does not exist.

- [ ] **Step 3: Implement minimal validator**

Add `src/albumentationsx_mcp/preview_validation.py` with:

- `PreviewRequestCheck`
- `PreviewRequestRemediationAction`
- `PreviewRequestValidationReport`
- `PreviewRequestValidator`

The validator should:

- parse raw dicts through `PreviewRequest.model_validate`;
- call `pipeline_service.validate_pipeline`;
- check input paths and annotation mask paths by root membership, existence, and file type;
- check annotation count when `annotations` is present;
- aggregate `status`, `valid`, `warnings`, `next_actions`, and `remediation_actions`.

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/test_preview_validation.py -q`

Expected: PASS.

### Task 2: MCP Tool Registration

**Files:**
- Modify: `src/albumentationsx_mcp/server.py`
- Modify: `src/albumentationsx_mcp/diagnostics.py`
- Modify: `tests/test_server.py`
- Modify: `tests/test_diagnostics.py`

- [ ] **Step 1: Write RED surface assertions**

Add `validate_preview_request` to expected public tools in server and diagnostics tests.

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/test_server.py tests/test_diagnostics.py -q`

Expected: FAIL because the tool is not registered.

- [ ] **Step 3: Register the tool**

In `server.py`:

- import `PreviewRequestValidator`;
- add `validate_preview_request` to `_PUBLIC_TOOLS`;
- instantiate the validator next to `PreviewService`;
- expose:

```python
@mcp.tool(name="validate_preview_request")
def validate_preview_request_tool(request: dict[str, Any], target: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate a preview request before rendering local preview artifacts."""
    return preview_validator.validate(request, target=TargetSpec.model_validate(target or {})).model_dump(mode="json")
```

In `diagnostics.py`, add `validate_preview_request` to `_REQUIRED_TOOLS`.

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/test_server.py tests/test_diagnostics.py tests/test_preview_validation.py -q`

Expected: PASS.

### Task 3: Contract Snapshots and Output Snapshots

**Files:**
- Modify: `scripts/export_output_contracts.py`
- Modify: `tests/test_output_contract_snapshots.py`
- Modify: `tests/fixtures/snapshots/mcp_contract.json`
- Modify: `tests/fixtures/snapshots/output_contracts.json`

- [ ] **Step 1: Add RED output snapshot assertions**

In `tests/test_output_contract_snapshots.py`, assert snapshot keys:

```python
assert "validate_preview_request_ready" in snapshot
assert "validate_preview_request_missing_input" in snapshot
assert "validate_preview_request_outside_allowed_root" in snapshot
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/test_output_contract_snapshots.py -q`

Expected: FAIL because snapshot examples do not exist.

- [ ] **Step 3: Add snapshot exporters**

In `scripts/export_output_contracts.py`, build representative reports by creating a `PreviewRequestValidator` with one
valid image under the output root and one outside path. Normalize root paths using existing `_normalize_paths`.

- [ ] **Step 4: Regenerate snapshots**

Run:

```bash
uv run python scripts/export_mcp_contract.py --output tests/fixtures/snapshots/mcp_contract.json
uv run python scripts/export_output_contracts.py --output tests/fixtures/snapshots/output_contracts.json
```

- [ ] **Step 5: Verify GREEN**

Run: `uv run pytest tests/test_mcp_contract_snapshot.py tests/test_output_contract_snapshots.py -q`

Expected: PASS.

### Task 4: Golden Eval Coverage

**Files:**
- Modify: `evals/golden_mcp_scenarios.yaml`
- Modify: `scripts/run_golden_evals.py`
- Modify: `tests/test_golden_evals.py`

- [ ] **Step 1: Write RED golden assertions**

Add scenario `preview_request_troubleshooting` with `preview_request_troubleshooting: true`. Update
`test_golden_eval_assets_are_present` to expect it and to assert `_run_preview_request_troubleshooting` exists.

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/test_golden_evals.py::test_golden_eval_assets_are_present -q`

Expected: FAIL before the scenario/runner helper exists.

- [ ] **Step 3: Implement scenario**

The helper should:

1. Write one allowed image.
2. Call `run_host_smoke_check`.
3. Fill the template with a missing allowed-root path and call `validate_preview_request`.
4. Assert `valid=false`, `input_path_missing`, and `fix_input_paths`.
5. Fill the template with the valid image and call `validate_preview_request`.
6. Assert `valid=true`.
7. Render the valid request with `render_preview_batch`.
8. Delete the preview run.

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/test_golden_evals.py -q`

Expected: PASS and stdout includes `preview_request_troubleshooting: ok`.

### Task 5: Docs and Release

**Files:**
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `docs/INSTALL.md`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`
- Modify: `server.json`
- Modify: `uv.lock`

- [ ] **Step 1: Document `validate_preview_request`**

Add it to core tools, host workflow, troubleshooting guidance, and release notes.

- [ ] **Step 2: Bump to `1.6.0`**

Update `pyproject.toml`, `server.json`, pinned install examples, and `uv.lock`.

- [ ] **Step 3: Verify release metadata**

Run: `uv run python scripts/check_release_version.py v1.6.0`

Expected: `release version 1.6.0 is consistent`.

### Task 6: Full Verification, Push, Release

**Files:**
- No further edits expected.

- [ ] **Step 1: Full local gate**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv run python scripts/check_release_version.py v1.6.0
uv build
```

Expected: all commands exit 0.

- [ ] **Step 2: Commit, tag, push**

Create logical commits, tag `v1.6.0`, push `main` and the tag.

- [ ] **Step 3: Watch GitHub**

Watch CI, Release, post-release smoke, and dispatch `publish-mcp.yml`.
