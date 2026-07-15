# MCP Adapter Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce `server.py` to the MCP composition root and move all FastMCP handlers into focused adapters without
changing the published full MCP contract.

**Architecture:** Introduce `albumentationsx_mcp.adapters.mcp` with explicit registrar dependencies, a pure declared
surface model, and one ordered registration coordinator. Domain/application modules remain unaware of FastMCP;
`server.create_mcp_server`, settings APIs, and the existing private test compatibility helper remain available.

**Tech Stack:** Python 3.10+, MCP Python SDK/FastMCP, dataclasses, pytest with fixtures and parametrization, Ruff, ty.

---

### Task 1: Adapter Surface Contract

**Files:**
- Create: `src/albumentationsx_mcp/adapters/__init__.py`
- Create: `src/albumentationsx_mcp/adapters/mcp/__init__.py`
- Create: `src/albumentationsx_mcp/adapters/mcp/contracts.py`
- Create: `tests/test_mcp_adapters.py`

- [x] **Step 1: Write failing pure manifest tests**

Add tests for `AdapterSurface`, `combine_adapter_surfaces`, and `validate_adapter_surfaces` that assert:

```python
surface = combine_adapter_surfaces(
    [
        AdapterSurface(adapter="catalog", tools=("search_transforms",), resources=("catalog://all",)),
        AdapterSurface(adapter="policy", tools=("validate_pipeline",), prompts=("policy_prompt",)),
    ]
)
assert surface.tools == ("search_transforms", "validate_pipeline")
assert surface.resources == ("catalog://all",)
assert surface.prompts == ("policy_prompt",)
```

Parameterize duplicate tests over `tools`, `resources`, `resource_templates`, and `prompts`. The error must include the
surface kind, duplicate identifier, and both adapter names.

- [x] **Step 2: Confirm RED**

Run: `uv run pytest -q tests/test_mcp_adapters.py`

Expected: import failure because `albumentationsx_mcp.adapters.mcp.contracts` does not exist.

- [x] **Step 3: Implement the immutable surface model**

Use frozen, slotted dataclasses. Preserve tuple order when combining surfaces. Reject empty adapter names, duplicate
adapter names, duplicate identifiers within one adapter, and identifiers declared by two adapters. Keep this module
free of FastMCP and domain imports.

- [x] **Step 4: Verify the pure contract**

Run:

```bash
uv run pytest -q tests/test_mcp_adapters.py
uv run ruff check src/albumentationsx_mcp/adapters tests/test_mcp_adapters.py
uv run ty check src/albumentationsx_mcp/adapters tests/test_mcp_adapters.py
```

### Task 2: Catalog And Policy Registrars

**Files:**
- Create: `src/albumentationsx_mcp/adapters/mcp/catalog.py`
- Create: `src/albumentationsx_mcp/adapters/mcp/policy.py`
- Modify: `tests/test_mcp_adapters.py`

- [x] **Step 1: Add failing registrar ownership tests**

Register each adapter into a fresh `FastMCP` and assert exact ownership:

```text
catalog tools: search_transforms, get_transform_schema, list_feedback_tags, list_quality_profiles, recommend_recipe
catalog resources: transforms/catalog, schemas/pipeline, feedback-tags, quality-profiles, recipes/catalog
catalog templates: transforms/{name}

policy tools: validate_pipeline, recommend_pipeline, adjust_pipeline, explain_pipeline, plan_augmentation_policy,
              plan_augmentation_policy_candidates, plan_policy_iteration, export_pipeline
policy resources: policy-assistant/contract
```

The test must compare manager keys with each module's `SURFACE`, not repeat a second expected set in assertions.

- [x] **Step 2: Confirm RED for missing registrars**

Run: `uv run pytest -q tests/test_mcp_adapters.py -k 'catalog or policy'`

- [x] **Step 3: Move catalog handlers unchanged**

`register_catalog_adapter(mcp, *, catalog)` owns catalog/search/schema resources, feedback/quality/recipe discovery,
and their five tools. Keep handler names, explicit FastMCP names, docstrings, annotations, defaults, JSON sorting, and
Pydantic dump options byte-for-byte compatible with the existing server implementation.

- [x] **Step 4: Move policy handlers unchanged**

`register_policy_adapter(mcp, *, catalog, pipeline_service)` owns validation, pipeline recommendation/adjustment/
explanation/export, policy planning, and the policy safety resource. Define `OutputFormat` in this module and re-export
it from the eventual server facade.

- [x] **Step 5: Run focused tests and static checks**

Run:

```bash
uv run pytest -q tests/test_mcp_adapters.py
uv run ruff check src/albumentationsx_mcp/adapters/mcp tests/test_mcp_adapters.py
uv run ruff format --check src/albumentationsx_mcp/adapters/mcp tests/test_mcp_adapters.py
uv run ty check src/albumentationsx_mcp/adapters/mcp tests/test_mcp_adapters.py
```

### Task 3: Dataset, Diagnostics, And Prompt Registrars

**Files:**
- Create: `src/albumentationsx_mcp/adapters/mcp/dataset.py`
- Create: `src/albumentationsx_mcp/adapters/mcp/diagnostics.py`
- Create: `src/albumentationsx_mcp/adapters/mcp/prompts.py`
- Modify: `tests/test_mcp_adapters.py`

- [x] **Step 1: Add failing exact-surface tests**

Use a `tmp_path` dependency fixture and assert:

```text
dataset tools: plan_dataset_onboarding, build_review_packet, inspect_dataset_quality,
               score_dataset_preview_candidates

diagnostics tools: diagnose_environment, run_host_smoke_check
diagnostics resources: capabilities, diagnostics/guide, workflows/catalog, workflows/task-profiles,
                       workflows/preview-tuning, workflows/annotation-preview, and all seven examples

prompts: build_robustness_augmentation_session, compare_preview_runs_for_feedback, run_first_preview_review,
         tune_pipeline_from_preview_feedback, export_reproducible_pipeline
```

- [x] **Step 2: Confirm RED**

Run: `uv run pytest -q tests/test_mcp_adapters.py -k 'dataset or diagnostics or prompts'`

- [x] **Step 3: Implement focused registrars**

- `register_dataset_adapter` receives `path_policy`, `pipeline_service`, and `preview_service` explicitly.
- `register_diagnostics_adapter` receives `diagnostics_service` and `pipeline_service`; capabilities read settings and
  public surface from the service rather than process environment.
- `register_prompt_adapter` has no storage or settings dependencies and delegates to existing prompt functions.

Keep all existing names, docstrings, annotations, defaults, content, and serialization behavior.

- [x] **Step 4: Run focused tests and static checks**

Run:

```bash
uv run pytest -q tests/test_mcp_adapters.py
uv run ruff check src/albumentationsx_mcp/adapters/mcp tests/test_mcp_adapters.py
uv run ruff format --check src/albumentationsx_mcp/adapters/mcp tests/test_mcp_adapters.py
uv run ty check src/albumentationsx_mcp/adapters/mcp tests/test_mcp_adapters.py
```

### Task 4: Preview And Session Registrars

**Files:**
- Create: `src/albumentationsx_mcp/adapters/mcp/preview.py`
- Create: `src/albumentationsx_mcp/adapters/mcp/sessions.py`
- Modify: `tests/test_mcp_adapters.py`

- [x] **Step 1: Add failing exact-surface tests**

Assert these ownership boundaries:

```text
preview tools: validate_preview_request, render_preview, render_preview_batch, compare_preview_runs,
               interpret_preview_feedback, plan_preview_review, rank_preview_candidates, export_preview_report
preview resources/templates: preview-review MCP App and verified artifact template

sessions tools: summarize_tuning_session, start_tuning_session, record_tuning_session_step, list_tuning_sessions,
                export_tuning_session, close_tuning_session, archive_tuning_session, cleanup_tuning_sessions,
                record_preview_feedback, list_preview_feedback, record_tuning_decision, list_tuning_decisions,
                export_tuning_report, list_preview_runs, get_preview_manifest, delete_preview_run,
                cleanup_preview_runs
```

- [x] **Step 2: Confirm RED**

Run: `uv run pytest -q tests/test_mcp_adapters.py -k 'preview or sessions'`

- [x] **Step 3: Implement preview registration and report helpers**

Move preview validation/render/compare/review/ranking/report handlers and the matching decision/feedback/session helper
functions into `preview.py`. Call `register_preview_review_resources` from this registrar with the explicit
`artifact_store`. Expose `export_matching_tuning_session_artifacts` for the compatibility facade.

- [x] **Step 4: Implement session, feedback, and retention registration**

Move persistent tuning sessions, preview feedback, tuning decisions/reports, and preview run retention handlers into
`sessions.py`. Keep feedback target validation private to this adapter.

- [x] **Step 5: Run focused tests and static checks**

Run the same pytest/Ruff/format/ty commands as Task 3 over the adapter package and `tests/test_mcp_adapters.py`.

### Task 5: Ordered Composition And Server Facade

**Files:**
- Create: `src/albumentationsx_mcp/adapters/mcp/dependencies.py`
- Create: `src/albumentationsx_mcp/adapters/mcp/registration.py`
- Modify: `src/albumentationsx_mcp/adapters/mcp/__init__.py`
- Modify: `src/albumentationsx_mcp/server.py`
- Modify: `tests/test_mcp_adapters.py`
- Modify: `tests/test_server.py`

- [x] **Step 1: Add failing composition and architecture tests**

Tests must assert:

```python
assert len(combined_surface.tools) == 44
assert len(combined_surface.resources) == 20
assert len(combined_surface.resource_templates) == 2
assert len(combined_surface.prompts) == 5
assert "@mcp." not in Path("src/albumentationsx_mcp/server.py").read_text(encoding="utf-8")
assert len(Path("src/albumentationsx_mcp/server.py").read_text(encoding="utf-8").splitlines()) <= 220
```

Add a test that pre-registers `search_transforms`, calls the coordinator, and expects a deterministic duplicate error
before any adapter mutates the server. Keep the existing private helper test through the server facade.

- [x] **Step 2: Confirm RED against the monolithic facade**

Run: `uv run pytest -q tests/test_mcp_adapters.py tests/test_server.py`

- [x] **Step 3: Add explicit dependency transport**

Create a frozen, slotted `McpDependencies` dataclass containing only already-constructed services/policies/stores. It
must not construct storage, read environment variables, or import `ServerSettings`.

- [x] **Step 4: Implement ordered registration**

`register_mcp_adapters(mcp, dependencies)` validates all declared surfaces, checks the target FastMCP server for
collisions before mutation, invokes registrars in the documented stable order, and verifies that the resulting manager
keys exactly match the combined manifest. Export canonical `PUBLIC_TOOLS`, `PUBLIC_PROMPTS`, and
`PUBLIC_WORKFLOW_RESOURCES` in their existing order for diagnostics.

- [x] **Step 5: Reduce `server.py` to composition**

Keep `ServerSettings`, `settings_from_environment`, `OutputFormat`, and `create_mcp_server`. Construct `PathPolicy`,
catalog, services, stores, `PublicSurface`, and `McpDependencies` once; create FastMCP; call the coordinator; return it.
Keep `_export_matching_tuning_session_artifacts` as a thin compatibility wrapper over the public adapter helper.

- [x] **Step 6: Prove contract identity**

Run:

```bash
uv run pytest -q tests/test_mcp_adapters.py tests/test_server.py tests/test_mcp_contract_snapshot.py tests/test_mcp_app.py
uv run python scripts/check_contract_snapshots.py
git diff --exit-code -- tests/fixtures/snapshots/mcp_contract.json tests/fixtures/snapshots/output_contracts.json
```

Expected: all tests pass and neither canonical snapshot changes.

### Task 6: MCP Extraction Verification

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/plans/2026-07-14-mcp-adapter-extraction.md`

- [x] **Step 1: Add an Unreleased changelog entry**

Document the internal adapter extraction and explicit composition without claiming a new release or a public contract
change.

- [x] **Step 2: Run focused and full verification**

Run:

```bash
uv run pytest -q tests/test_mcp_adapters.py tests/test_server.py tests/test_mcp_contract_snapshot.py tests/test_mcp_app.py
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/run_golden_evals.py
uv run python scripts/check_contract_snapshots.py
uv run python scripts/check_release_readiness.py --tag v1.19.0
```

- [x] **Step 3: Mark the plan complete and commit**

```bash
git add CHANGELOG.md docs/superpowers/plans/2026-07-14-mcp-adapter-extraction.md \
  src/albumentationsx_mcp/adapters src/albumentationsx_mcp/server.py \
  tests/test_mcp_adapters.py tests/test_server.py
git commit -m "refactor: extract MCP registration adapters"
```
