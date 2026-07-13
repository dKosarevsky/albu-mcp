# Claude Desktop Host Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make host smoke guidance work without model-visible MCP resource reads, record real Claude Desktop evidence, and release the verified MCPB as v1.17.0.

**Architecture:** Add one typed guidance object to the core `HostSmokeReport`; keep FastMCP and MCPB adapters thin. Treat MCP resources as optional detailed documentation, preserve bounded-root enforcement in existing services, and record host observations separately from generated-fixture preview evidence.

**Tech Stack:** Python 3.10+, Pydantic, FastMCP, AlbumentationsX, pytest, Ruff, ty, uv, MCPB CLI, GitHub Actions.

---

### Task 1: Host-neutral smoke guidance

**Files:**
- Modify: `tests/test_host_smoke.py`
- Modify: `tests/test_server.py`
- Modify: `src/albumentationsx_mcp/host_smoke.py`
- Modify: `src/albumentationsx_mcp/server.py`

- [ ] **Step 1: Write failing core contract assertions**

Extend the ready-report test with:

```python
assert report.workflow_guidance.resource_uri == "albumentationsx://examples/client-smoke"
assert report.workflow_guidance.resource_access == "optional"
assert any("otherwise" in instruction.lower() for instruction in report.workflow_guidance.instructions)
assert any("preview_ready" in instruction for instruction in report.workflow_guidance.instructions)
assert any("validate_preview_request" in instruction for instruction in report.workflow_guidance.instructions)
```

- [ ] **Step 2: Write a failing discovery-description assertion**

Add a server test that inspects `server._tool_manager._tools["run_host_smoke_check"].description` and requires both
`resource` and `optional` in the lower-cased description.

- [ ] **Step 3: Run focused tests and observe failure**

Run:

```console
uv run pytest tests/test_host_smoke.py tests/test_server.py -q
```

Expected: failures because `workflow_guidance` and the fallback description do not exist.

- [ ] **Step 4: Implement the typed core contract**

Add this model and field in `host_smoke.py`:

```python
class HostWorkflowGuidance(StrictModel):
    """Host-neutral instructions that do not require model-visible MCP resources."""

    resource_uri: str = "albumentationsx://examples/client-smoke"
    resource_access: Literal["optional"] = "optional"
    instructions: list[str]


class HostSmokeReport(StrictModel):
    # existing fields remain unchanged
    workflow_guidance: HostWorkflowGuidance
```

Construct it with instructions that permit direct smoke execution, require `preview_ready=true`, validate the request
before rendering, and keep the first preview bounded. Update the tool docstring to state that reading the client-smoke
resource is optional because the report contains the complete safe next-step guidance.

- [ ] **Step 5: Run focused tests**

Run the command from Step 3. Expected: all focused tests pass.

- [ ] **Step 6: Commit**

```console
git add src/albumentationsx_mcp/host_smoke.py src/albumentationsx_mcp/server.py tests/test_host_smoke.py tests/test_server.py
git commit -m "feat: make host smoke resources optional"
```

### Task 2: Host-facing guidance and contracts

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL.md`
- Modify: `docs/USAGE.md`
- Modify: `src/albumentationsx_mcp/prompts.py`
- Modify: `.agents/skills/albumentationsx-mcp/SKILL.md`
- Modify: `skills/albumentationsx-mcp/SKILL.md`
- Modify: `tests/test_project_scaffolding.py`
- Modify: `tests/test_skills_package.py`
- Modify: `tests/fixtures/snapshots/output_contracts.json`
- Modify: `tests/fixtures/snapshots/mcp_contract.json`

- [ ] **Step 1: Add failing documentation and skill assertions**

Require first-run text to say that hosts may read `albumentationsx://examples/client-smoke` when resource access is
available, otherwise call `run_host_smoke_check` directly. Require the skill to stop unless `preview_ready` is true.

- [ ] **Step 2: Update prompt and user-facing guidance**

Use this semantic sequence everywhere:

```text
Read albumentationsx://examples/client-smoke when the host exposes resource reads; otherwise call
run_host_smoke_check directly. Continue only when preview_ready is true.
```

Keep README concise and put operational detail in install/usage docs and packaged skills.

- [ ] **Step 3: Regenerate public contract snapshots**

Run:

```console
uv run python scripts/export_mcp_contract.py --output tests/fixtures/snapshots/mcp_contract.json
uv run python scripts/export_output_contracts.py --output tests/fixtures/snapshots/output_contracts.json
```

Expected: only the smoke output contract and tool description/schema-related snapshot content changes.

- [ ] **Step 4: Run targeted tests and commit**

```console
uv run pytest tests/test_project_scaffolding.py tests/test_skills_package.py tests/test_contract_snapshots.py -q
git add README.md docs/INSTALL.md docs/USAGE.md src/albumentationsx_mcp/prompts.py .agents/skills/albumentationsx-mcp/SKILL.md skills/albumentationsx-mcp/SKILL.md tests/fixtures/snapshots tests/test_project_scaffolding.py tests/test_skills_package.py
git commit -m "docs: add resource-read fallback guidance"
```

### Task 3: Claude Desktop evidence and bounded preview

**Files:**
- Create: `docs/host-evidence/claude-desktop-2026-07-13.md`
- Modify: `docs/HOST_MANUAL_RUNS.json`
- Regenerate: `docs/HOST_ACCEPTANCE_EVIDENCE.md`

- [ ] **Step 1: Verify installed host configuration and discovery**

Confirm the extension setting is enabled with dedicated fixture/artifact roots, then verify Claude's MCP log contains
successful `initialize`, `tools/list`, `prompts/list`, `resources/list`, and `tools/call` responses.

- [ ] **Step 2: Render one bounded fixture preview**

Use `sample-grid.png` under the configured fixture root, one image, one variant, seed `0`, and maximum side `512`.
Validate the request before calling `render_preview_batch`. Inspect the resulting manifest and contact sheet under the
configured artifact root. Do not count the fixture as beta/adoption evidence.

- [ ] **Step 3: Write the sanitized receipt**

Record product version, Desktop version, MCPB installation path semantics, protocol calls, smoke outcome, preview
artifact hashes, the resource-read limitation, and evidence boundaries. Redact account identifiers and absolute private
paths.

- [ ] **Step 4: Record manual host acceptance and regenerate evidence**

Add a unique `Claude Desktop` `manual_host_ui` passed record. Add `first_10_minutes_replay` only if the real Desktop UI
completed the preview call. Regenerate the canonical evidence report with the repository's exporter and validate it.

- [ ] **Step 5: Commit**

```console
git add docs/host-evidence/claude-desktop-2026-07-13.md docs/HOST_MANUAL_RUNS.json docs/HOST_ACCEPTANCE_EVIDENCE.md
git commit -m "docs: record Claude Desktop host acceptance"
```

### Task 4: v1.17.0 release preparation

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `server.json`
- Modify: `.mcp.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `desktop-extension/manifest.json`
- Modify: `desktop-extension/pyproject.toml`
- Modify: `CHANGELOG.md`
- Modify version-scoped README/docs/tests required by release guards.

- [ ] **Step 1: Bump all distributable metadata to 1.17.0**

Set the package, MCP Registry, Codex plugin, MCP config, MCPB manifest, MCPB wrapper project, and exact MCPB dependency
pin to `1.17.0`. Run `uv lock` to update the lockfile.

- [ ] **Step 2: Write bounded release notes**

Create `## 1.17.0 - 2026-07-13` in `CHANGELOG.md` covering the MCPB installer, explicit roots, Claude Desktop Free host
acceptance, optional resource-read guidance, and generated-fixture evidence boundary. Keep unrelated prior entries
unchanged.

- [ ] **Step 3: Run release metadata checks**

```console
uv run python scripts/check_release_version.py v1.17.0
uv run python scripts/check_desktop_extension.py
uv run python scripts/extract_release_notes.py --tag v1.17.0 --output /tmp/albu-v1.17.0-notes.md
```

Expected: all commands succeed and extracted notes contain only the 1.17.0 section.

- [ ] **Step 4: Commit**

```console
git add pyproject.toml uv.lock server.json .mcp.json .codex-plugin/plugin.json desktop-extension CHANGELOG.md README.md docs tests
git commit -m "release: prepare v1.17.0"
```

### Task 5: Verification, integration, and publication

**Files:**
- No product files unless verification exposes a defect.

- [ ] **Step 1: Run complete local verification**

```console
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/check_release_readiness.py --tag v1.17.0
uv run python scripts/run_golden_evals.py --work-dir /tmp/albu-v1.17.0-golden
uv build
uv run python -m scripts.build_desktop_extension --output-dir /tmp/albu-v1.17.0-mcpb
```

Expected: all checks pass and both Python artifacts and `albumentationsx-mcp-1.17.0.mcpb` are produced.

- [ ] **Step 2: Push a branch and open a PR**

Push `codex/claude-desktop-host-acceptance-v1.17`, create a ready PR, and wait for required checks.

- [ ] **Step 3: Review and merge**

Review the final diff for path leaks, generated artifacts, unrelated changes, and release-version consistency. Merge only
after CI passes.

- [ ] **Step 4: Tag and verify publication**

Create annotated tag `v1.17.0` on the merged `main`, push it, watch the release workflow, and verify PyPI, the GitHub
Release MCPB/checksum assets, post-release `uvx` smoke, and MCP Registry metadata.
