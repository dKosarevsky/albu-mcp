# Capability Profiles And Resource Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add opt-in, dependency-closed MCP capability profiles and a tool-based workflow-example fallback while
keeping the additive `full` surface as the v1.x default.

**Architecture:** Keep one canonical full registration path. Each adapter declares profile membership beside its
surface metadata. Registration occurs on an isolated FastMCP staging instance, then atomically copies the selected
profile view into the target server. Workflow examples remain application-owned typed values reused by both resource
handlers and one diagnostic tool.

**Tech Stack:** Python 3.10+, FastMCP, Pydantic v2, argparse, pytest fixtures/parametrization, Ruff, ty.

---

### Task 1: Workflow Example Fallback Tool

**Files:**
- Modify: `src/albumentationsx_mcp/workflows.py`
- Modify: `src/albumentationsx_mcp/adapters/mcp/diagnostics.py`
- Modify: `src/albumentationsx_mcp/adapters/mcp/registration.py`
- Modify: `src/albumentationsx_mcp/host_smoke.py`
- Create: `tests/test_workflow_example_fallback.py`
- Modify: `tests/test_workflows.py`
- Modify: `tests/test_host_smoke.py`
- Modify: `tests/fixtures/snapshots/mcp_contract.json`
- Modify: `tests/fixtures/snapshots/output_contracts.json`

- [x] **Step 1: Add failing closed-id, parity, and guidance tests**

Assert seven stable `HOST_EXAMPLE_IDS`, a deterministic accepted-id error, exact JSON parity between every
`albumentationsx://examples/{id}` resource and `get_workflow_example(example_id=id)`, and fallback guidance in
`run_host_smoke_check`.

- [x] **Step 2: Implement the application lookup contract**

Add `HostExampleId`, `HOST_EXAMPLE_IDS`, and stable unknown-id validation in `workflows.py`. Existing resources and the
new tool must both call `get_host_example`; no copied example payload is allowed in the adapter.

- [x] **Step 3: Register the additive diagnostic tool**

Add `get_workflow_example` to the diagnostics surface and full public tool inventory. Its argument schema must be a
closed enum and its response must be the existing typed `HostExample` JSON shape.

- [x] **Step 4: Update smoke guidance and snapshots**

When resource reads are unavailable, direct the host to
`get_workflow_example(example_id="client-smoke")`. Regenerate only the intentional additive MCP and output contract
changes and classify the MCP drift as additive.

- [x] **Step 5: Verify and commit**

Run focused workflow, host-smoke, adapter, contract, Ruff, format, and ty checks. Commit as
`feat: add workflow example fallback tool`.

### Task 2: Pure Capability Profile Contracts

**Files:**
- Create: `src/albumentationsx_mcp/capabilities.py`
- Modify: `src/albumentationsx_mcp/adapters/mcp/contracts.py`
- Modify: all focused modules under `src/albumentationsx_mcp/adapters/mcp/`
- Create: `tests/test_mcp_profiles.py`
- Modify: `tests/test_mcp_adapters.py`

- [x] **Step 1: Add failing profile declaration tests**

Parameterize `core`, `review`, `dataset`, and `full`. Require complete per-identifier declarations, deterministic order,
no duplicate profile ownership, and these final counts:

| Profile | Tools | Resources | Templates | Prompts |
| --- | ---: | ---: | ---: | ---: |
| `core` | 16 | 9 | 1 | 0 |
| `review` | 41 | 19 | 2 | 5 |
| `dataset` | 20 | 9 | 1 | 0 |
| `full` | 45 | 20 | 2 | 5 |

- [x] **Step 2: Implement pure profile values and metadata**

Add a string enum `CapabilityProfile` and immutable `ProfileSurface` declarations. `full` includes all identifiers;
focused profiles are explicit views, not alternate implementations. Validation rejects unknown, duplicate, missing,
or out-of-surface profile identifiers.

- [x] **Step 3: Declare every production identifier**

Catalog and pipeline tools are core. Preview/session/prompt items are review. Dataset tools are dataset. Resources that
reference both review and dataset tools are full-only. Add dependency-closure assertions for prompt and workflow
resource tool references.

- [x] **Step 4: Verify and commit**

Run profile contract, adapter, Ruff, format, and ty checks. Commit as `feat: declare MCP capability profiles`.

### Task 3: Atomic Profile Registration

**Files:**
- Modify: `src/albumentationsx_mcp/adapters/mcp/registration.py`
- Modify: `tests/test_mcp_profiles.py`
- Modify: `tests/test_mcp_adapters.py`

- [ ] **Step 1: Add failing registration tests**

For every profile, assert actual FastMCP managers exactly equal the declared filtered surface. Add tests proving an
excluded-name collision is preserved, a selected collision fails before target mutation, and staging failures leave
the target unchanged.

- [ ] **Step 2: Implement staged filtering**

Register the canonical full adapter set on an isolated FastMCP instance, verify it against the full declaration, select
manager entries by profile, then atomically append them to the target. Preserve registration order and rollback target
state on every failure.

- [ ] **Step 3: Verify and commit**

Run profile/adapter tests and all MCP contract tests plus static checks. Commit as
`feat: register filtered MCP profiles`.

### Task 4: Runtime Profile Selection

**Files:**
- Modify: `src/albumentationsx_mcp/server.py`
- Modify: `src/albumentationsx_mcp/adapters/cli/runtime.py`
- Modify: `tests/test_server.py`
- Modify: `tests/test_cli_adapters.py`
- Modify: `tests/test_cli_contract_snapshot.py`
- Modify: `tests/fixtures/snapshots/cli_contract.json`

- [ ] **Step 1: Add failing settings, environment, CLI, and capabilities tests**

Assert `full` default, `ALBU_MCP_CAPABILITY_PROFILE`, `--capability-profile`, accepted-value diagnostics, profile-specific
server managers, and a capabilities resource that lists only the active public surface.

- [ ] **Step 2: Wire profile selection through the composition root**

Add `capability_profile` to `ServerSettings`, parse the environment once, preserve all settings during CLI overrides,
build profile-aware `DiagnosticsService` data, and pass the profile to `register_mcp_adapters`.

- [ ] **Step 3: Regenerate the additive CLI contract and verify stdio**

Regenerate the CLI snapshot for the one new server option. Exercise at least `core`, `review`, and `dataset` through
in-process construction and one focused stdio smoke. Existing MCPB/install examples remain `full` by omission.

- [ ] **Step 4: Verify and commit**

Run server, CLI, profile, stdio, snapshot, Ruff, format, and ty checks. Commit as
`feat: expose MCP capability profiles`.

### Task 5: Documentation And Completion

**Files:**
- Modify: `README.md`
- Modify: `docs/CONFIGURATION.md`
- Modify: `docs/COMPATIBILITY.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/plans/2026-07-15-capability-profiles-resource-fallback.md`

- [ ] **Step 1: Document focused opt-in usage**

Keep the README concise: mention `full` default, one `review` example, and link to configuration. Document all profiles,
the environment equivalent, dependency closure, and the resource-blind fallback. State that changing the default is a
future-major decision.

- [ ] **Step 2: Run full verification**

Run full pytest, Ruff, format, ty, golden evals, contract snapshots, release readiness for `v1.19.0`, MCP App checks,
package build, MCPB validation, and wheel smoke. Verify only intentional snapshots changed.

- [ ] **Step 3: Review boundaries and complete the plan**

Run an independent diff review, update architecture budgets if necessary, mark all steps complete, and commit as
`docs: complete capability profiles and fallback` without creating a tag or release.
