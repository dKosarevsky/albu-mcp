# MCP Apps Preview Review Implementation Plan

> Execute each task with test-first changes and one logical commit per completed phase.

**Goal:** Add a secure, self-contained MCP Apps review surface to the existing preview tools while preserving all
text-only behavior and improving release verification reliability.

**Architecture:** `ArtifactStore` enforces binary access, `mcp_app.py` adapts that boundary to MCP resources, and a
separate TypeScript workspace produces one packaged HTML resource. Existing render and feedback tools remain the only
application actions.

**Technology:** Python 3.10+, FastMCP v1, Pydantic, pytest, uv, Ruff, ty, TypeScript, Vite,
`@modelcontextprotocol/ext-apps`, Lucide, Vitest, Prettier, Playwright, official MCP Apps basic host.

---

## Task 1: Harden Registry release verification

**Files:**
- Modify: `.github/workflows/release.yml`
- Modify: `scripts/check_mcp_registry_status.py`
- Modify: `tests/test_mcp_registry_status.py`

1. Add a failing test that requires each retryable failure to be observable and preserves semantic mismatch failures.
2. Add attempt diagnostics without logging response bodies or credentials.
3. Replace the measured-insufficient 30-second release profile with fewer, longer attempts.
4. Run the focused tests, Ruff, and ty.
5. Commit: `fix: tolerate slow MCP Registry reads`.

## Task 2: Add the secure artifact read boundary

**Files:**
- Modify: `src/albumentationsx_mcp/preview.py`
- Modify: `tests/test_artifacts.py`

1. Add failing parameterized tests for valid reads, traversal, unknown artifacts, disallowed kinds, path mismatch,
   size mismatch, and digest mismatch.
2. Implement one `ArtifactStore` read API that validates the recorded artifact before returning bytes.
3. Run focused tests, Ruff, and ty.
4. Commit: `feat: add verified preview artifact reads`.

## Task 3: Register MCP Apps resources and render metadata

**Files:**
- Create: `src/albumentationsx_mcp/mcp_app.py`
- Create initially: `src/albumentationsx_mcp/ui/preview-review.html`
- Modify: `src/albumentationsx_mcp/server.py`
- Modify: `scripts/export_mcp_contract.py`
- Modify: `tests/test_mcp_app.py`
- Modify: `tests/fixtures/snapshots/mcp_contract.json`

1. Add failing tests for render-tool metadata, UI MIME/CSP, resource-template reads, and HTML packaging.
2. Register the static `ui://` app resource and verified `artifact://` image template in a focused adapter.
3. Link both render tools with modern nested `_meta.ui` metadata.
4. Extend the public contract snapshot to include non-empty metadata and refresh it intentionally.
5. Prove static and binary resources over MCP stdio.
6. Commit: `feat: expose preview review MCP App resources`.

## Task 4: Build the interactive review view

**Files:**
- Create: `mcp-app/package.json`
- Create: `mcp-app/package-lock.json`
- Create: `mcp-app/tsconfig.json`
- Create: `mcp-app/vite.config.ts`
- Create: `mcp-app/review.html`
- Create: `mcp-app/src/main.ts`
- Create: `mcp-app/src/styles.css`
- Create: `mcp-app/src/review-state.ts`
- Create: `mcp-app/src/review-state.test.ts`
- Generate: `src/albumentationsx_mcp/ui/preview-review.html`

1. Scaffold the workspace with package versions resolved by npm.
2. Write failing state tests for ordinal navigation, artifact mapping, feedback composition, and sanitized labels.
3. Implement the pure state layer.
4. Implement all MCP Apps handlers before `connect()`, host styles/safe areas, verified artifact reads, feedback saves,
   teardown, and explicit UI states.
5. Build one self-contained HTML file and verify it has no remote dependencies.
6. Run Vitest, TypeScript, Prettier, Vite, and Python app-resource tests.
7. Commit: `feat: add interactive preview review UI`.

## Task 5: Add CI and packaging guards

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/release.yml`
- Modify: `tests/test_project_scaffolding.py`
- Modify: `tests/test_release_version.py` if required

1. Add a dedicated UI job with npm cache, unit tests, typecheck, format check, build, and generated-file drift check.
2. Rebuild and drift-check the UI in release before Python packaging.
3. Assert the wheel and MCPB contain the app HTML.
4. Run package and extension builds and inspect their contents.
5. Commit: `ci: verify the packaged MCP App`.

## Task 6: Document progressive enhancement and operator validation

**Files:**
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `docs/HOST_PROOF_STATUS.md`
- Modify: `CHANGELOG.md`
- Create: `docs/MCP_APPS_REVIEW.md`

1. Document supported workflow, fallback behavior, privacy boundary, and host compatibility without inflating the
   README.
2. Add a reproducible official basic-host runbook and an honest evidence classification table.
3. Add the Unreleased changelog entry.
4. Run documentation/scaffolding guards.
5. Commit: `docs: add MCP Apps preview review guide`.

## Task 7: Verify in the official basic host

1. Build the UI and start the MCP server over streamable HTTP with bounded fixture/artifact roots.
2. Run the official MCP Apps v1.7.4 basic host against that server.
3. Render a real generated local image fixture through `render_preview_batch`.
4. Use Playwright to verify nonblank contact sheet and selected image, navigation, feedback persistence, error-free
   console, responsive desktop/mobile layouts, and no external network requests from the app.
5. Save privacy-safe screenshots under `docs/assets/mcp-app/` only when they improve user documentation.
6. Record the run as generated-fixture machine evidence, not beta evidence.
7. Commit any evidence/docs update separately: `test: record MCP Apps basic-host proof`.

## Task 8: Complete v1.18.0 release integration

1. Bump all package, Registry, plugin, and MCPB versions to `1.18.0` using existing project conventions.
2. Regenerate required release/readiness receipts without rewriting historical records.
3. Run the full Python suite, Ruff, format check, ty, frontend gates, golden evals, release readiness, wheel/sdist build,
   MCPB build, metadata inspection, and text-only stdio fallback replay.
4. Request an independent code review and resolve findings with focused tests.
5. Push a PR, wait for all CI jobs, merge, tag `v1.18.0`, and watch the complete release pipeline.
6. Independently verify PyPI metadata, GitHub assets/checksums, published-package smoke, and MCP Registry state.
7. Do not mark real beta/adoption evidence complete unless an external reviewer has actually supplied it.
