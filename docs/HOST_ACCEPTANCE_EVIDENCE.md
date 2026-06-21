# Host Acceptance Evidence

- Project: albumentationsx-mcp
- Version: 1.14.0
- Registry name: io.github.dKosarevsky/albu-mcp
- PyPI package: albumentationsx-mcp==1.14.0
- Automated Coverage: recorded
- Manual Host UI: pending

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
| Claude Code | pending | none | manual UI run not recorded |
| Cursor | pending | none | manual UI run not recorded |
| Codex | pending | none | manual UI run not recorded |

## Minimum Release Acceptance

1. `albumentationsx://capabilities` lists expected tools, prompts, resources, roots, and limits.
2. `diagnose_environment` returns `status="ok"` or actionable `remediation_actions`.
3. `validate_preview_request` rejects missing and outside-root paths before rendering.
4. `export_preview_report` includes contact sheets, concrete feedback, and interactive tuning session timelines.
5. `export_preview_report` links exported Markdown tuning session artifacts when matching sessions exist.
6. `export_tuning_session` returns Markdown or JSON content plus artifact metadata suitable for handoff.
