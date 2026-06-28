# Host Acceptance Evidence

- Project: albumentationsx-mcp
- Version: 1.15.0
- Registry name: io.github.dKosarevsky/albu-mcp
- PyPI package: albumentationsx-mcp==1.15.0
- Automated Coverage: recorded
- Manual Host UI: blocked
- First 10 Minutes Replay: blocked

## Automated Coverage

| Check | Status | Evidence |
| --- | --- | --- |
| pytest | automated | uv run pytest |
| golden stdio evals | automated | uv run python scripts/run_golden_evals.py |
| output contract snapshots | automated | tests/fixtures/snapshots/output_contracts.json |
| release build | automated | uv build and GitHub Release workflow |
| PyPI publish check | automated | Release workflow publish-pypi and post-release-smoke jobs |
| published package smoke | automated | uv run python scripts/check_published_package_smoke.py |
| MCP Registry metadata publish check | automated | .github/workflows/publish-mcp.yml |
| host acceptance evidence freshness | automated | uv run python scripts/check_host_acceptance_report.py |

## Manual Host UI

| Host | Status | Date | Evidence |
| --- | --- | --- | --- |
| Claude Desktop | pending | none | manual UI run not recorded |
| Claude Code | blocked | 2026-06-28 | Claude Code manual host UI run could not start in this environment because claude CLI was not found in PATH; MCP tools/resources were not observed in Claude Code. |
| Cursor | pending | none | manual UI run not recorded |
| Codex | blocked | 2026-06-28 | Codex CLI host listed AlbumentationsX MCP resources/tools and read client-smoke, but run_host_smoke_check was cancelled twice before preview_ready could be confirmed. |

## First 10 Minutes Replay

| Host | Status | Date | Evidence | Artifacts |
| --- | --- | --- | --- | --- |
| Claude Desktop | pending | none | first 10 minutes replay not recorded |  |
| Claude Code | blocked | 2026-06-28 | Claude Code host run could not start in this environment because claude CLI was not found in PATH; first-10-minutes replay was not executed. |  |
| Cursor | pending | none | first 10 minutes replay not recorded |  |
| Codex | blocked | 2026-06-28 | Codex CLI host run reached AlbumentationsX MCP discovery and read albumentationsx://examples/client-smoke, but run_host_smoke_check returned user cancelled MCP tool call twice; preview_ready was not confirmed. | /private/tmp/albu-mcp-codex-host-run.txt |

## Minimum Release Acceptance

1. `albumentationsx://capabilities` lists expected tools, prompts, resources, roots, and limits.
2. `diagnose_environment` returns `status="ok"` or actionable `remediation_actions`.
3. `validate_preview_request` rejects missing and outside-root paths before rendering.
4. `export_preview_report` includes contact sheets, concrete feedback, and interactive tuning session timelines.
5. `export_preview_report` links exported Markdown tuning session artifacts when matching sessions exist.
6. `export_tuning_session` returns Markdown or JSON content plus artifact metadata suitable for handoff.
