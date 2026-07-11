# Codex Plugin Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository a validated Codex plugin source that loads the canonical AlbumentationsX skill and a pinned, least-privilege MCP server.

**Architecture:** Add the native plugin manifest and companion MCP config at repository root. Keep validation in one focused script, compose that script into the existing release-readiness aggregate, and document the Codex path without replacing portable host setup.

**Tech Stack:** JSON plugin manifests, Python 3.10+, pytest, Ruff, ty, uv, existing release-readiness framework.

---

## File Map

- Create `.codex-plugin/plugin.json`: Codex plugin identity, component paths, and UI metadata.
- Create `.mcp.json`: one pinned stdio MCP server with an explicit environment pass-through allowlist.
- Create `scripts/check_codex_plugin.py`: structural, safety, and version-drift validator.
- Create `tests/test_codex_plugin.py`: focused unit and CLI contract tests.
- Modify `scripts/check_release_readiness.py`: compose the plugin validator into CI/release readiness.
- Modify `tests/test_release_readiness.py`: assert aggregate success and failure reporting.
- Modify `tests/test_project_scaffolding.py`: keep public README/plugin metadata requirements stable.
- Modify `README.md`: add a short Codex plugin bundle note while preserving the concise limit.
- Modify `docs/INSTALL.md`: document bundle behavior, bounded-root variables, validation, and fallback config.
- Modify `skills/albumentationsx-mcp/SKILL.md`: teach Codex agents to distinguish plugin base mode from preview-ready mode.
- Modify `tests/test_skills_package.py`: lock the updated skill guidance.
- Modify `CHANGELOG.md`: record the unreleased distribution improvement.

### Task 1: Native Plugin Contract

**Files:**
- Create: `.codex-plugin/plugin.json`
- Create: `.mcp.json`
- Create: `tests/test_codex_plugin.py`

- [ ] **Step 1: Write the failing bundle contract test**

Assert that both JSON files exist and that the manifest selects `./skills/` and `./.mcp.json`. Assert one
`albumentationsx` stdio process, exact pinned `uvx` args, exact environment pass-through, no implicit root args, and
safe UI metadata.

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
uv run pytest tests/test_codex_plugin.py -q
```

Expected: failure because `.codex-plugin/plugin.json` and `.mcp.json` do not exist.

- [ ] **Step 3: Add the minimal plugin files**

Use project version `1.15.0`. Keep `skills` canonical and pin the MCP package to
`albumentationsx-mcp==1.15.0`. Do not add default allowed or artifact roots.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the same pytest command. Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add .codex-plugin/plugin.json .mcp.json tests/test_codex_plugin.py
git commit -m "feat: add Codex plugin bundle"
```

### Task 2: Plugin Safety Validator

**Files:**
- Create: `scripts/check_codex_plugin.py`
- Modify: `tests/test_codex_plugin.py`

- [ ] **Step 1: Write failing validator tests**

Add a successful report test and parametrized mutations for:

- plugin version drift;
- unpinned or wrong package args;
- extra environment variables;
- implicit `--allowed-root`/`--artifact-root` args;
- wrong skill or MCP companion paths.

Add a CLI test that expects a concise success line.

- [ ] **Step 2: Run the tests and verify RED**

Expected: import or behavior failure because the validator is absent.

- [ ] **Step 3: Implement the validator**

Use dataclasses and structured JSON parsing. Raise `ValueError` with the first actionable mismatch. Keep filesystem
reads injectable through path arguments and return a report containing the validated versions and server name.

- [ ] **Step 4: Run tests and static checks**

```bash
uv run pytest tests/test_codex_plugin.py -q
uv run ruff check scripts/check_codex_plugin.py tests/test_codex_plugin.py
uv run ty check scripts/check_codex_plugin.py tests/test_codex_plugin.py
```

Expected: all pass.

- [ ] **Step 5: Run the local official plugin validator**

```bash
python3 /Users/if/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

Expected: `Plugin validation passed`.

- [ ] **Step 6: Commit**

```bash
git add scripts/check_codex_plugin.py tests/test_codex_plugin.py
git commit -m "test: guard Codex plugin contract"
```

### Task 3: Release Readiness Composition

**Files:**
- Modify: `scripts/check_release_readiness.py`
- Modify: `tests/test_release_readiness.py`

- [ ] **Step 1: Write failing aggregate tests**

Add `codex_plugin` to the expected check list and CLI output. Add a temporary malformed plugin fixture and assert the
aggregate reports exactly the plugin failure while preserving report structure.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
uv run pytest tests/test_release_readiness.py -q
```

Expected: expected check and malformed fixture assertions fail.

- [ ] **Step 3: Compose the validator**

Add manifest and MCP paths to `ReleaseReadinessConfig`, call `validate_codex_plugin`, and map success/failure into a
`ReleaseReadinessCheck` named `codex_plugin`. Expose optional CLI path overrides for deterministic tests.

- [ ] **Step 4: Run focused tests and readiness CLI**

```bash
uv run pytest tests/test_release_readiness.py tests/test_codex_plugin.py -q
uv run python scripts/check_release_readiness.py
```

Expected: all pass and `codex_plugin` appears in the success output.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_release_readiness.py tests/test_release_readiness.py
git commit -m "ci: validate Codex plugin readiness"
```

### Task 4: Public Guidance

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL.md`
- Modify: `skills/albumentationsx-mcp/SKILL.md`
- Modify: `tests/test_project_scaffolding.py`
- Modify: `tests/test_skills_package.py`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write failing documentation tests**

Require the README to identify the native bundle without claiming a public marketplace listing. Require install docs
to name both manifest files, the three environment variables, the no-implicit-root policy, restart/smoke validation,
and direct TOML fallback. Require the skill to stop rendering until plugin roots make `preview_ready` true.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
uv run pytest tests/test_project_scaffolding.py tests/test_skills_package.py -q
```

Expected: missing plugin guidance assertions fail.

- [ ] **Step 3: Update documentation and skill concisely**

Keep README under its existing 130-line guard and the skill body under 450 words. Make `uvx` remain the portable
quick start. State that the bundle is a repository plugin source, not a public marketplace claim.

- [ ] **Step 4: Run focused tests and skill validation**

```bash
uv run pytest tests/test_project_scaffolding.py tests/test_skills_package.py -q
python3 /Users/if/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/albumentationsx-mcp
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/INSTALL.md skills/albumentationsx-mcp/SKILL.md \
  tests/test_project_scaffolding.py tests/test_skills_package.py CHANGELOG.md
git commit -m "docs: explain Codex plugin setup"
```

### Task 5: Review, Verification, and Integration

**Files:**
- Review all branch changes.

- [ ] **Step 1: Review the diff against the design**

Check for implicit filesystem grants, unpinned runtime dependencies, duplicate skill sources, unsupported plugin
fields, public marketplace claims, and README/skill bloat. Fix findings through a focused RED→GREEN cycle.

- [ ] **Step 2: Run the complete verification matrix**

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/check_release_readiness.py
uv run python scripts/check_release_readiness.py --tag v1.15.0
uv run python scripts/run_golden_evals.py --work-dir .golden-evals
uv build
python3 /Users/if/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

Expected: every command passes.

- [ ] **Step 3: Verify runtime startup contract**

Run the exact `.mcp.json` command with `--help`, then run the existing stdio smoke or focused MCP integration test.
Confirm no evidence records changed.

- [ ] **Step 4: Push, open PR, wait for CI, and merge**

Push `codex/codex-plugin-bundle`, open a non-draft PR, wait for Python 3.10-3.13 checks, squash-merge, remove the
feature branch, fast-forward local `main`, and rerun focused post-merge checks.
