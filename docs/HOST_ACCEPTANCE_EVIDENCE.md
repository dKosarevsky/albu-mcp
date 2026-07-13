# Host Acceptance Evidence

- Project: albumentationsx-mcp
- Version: 1.17.1
- Registry name: io.github.dKosarevsky/albu-mcp
- PyPI package: albumentationsx-mcp==1.17.1
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
| Claude Desktop | passed | 2026-07-13 | Reviewer observed Claude Desktop Free install and enable the MCPB, discover tools/prompts/resources, and complete run_host_smoke_check with preview_ready=true; sanitized receipt: docs/host-evidence/claude-desktop-2026-07-13.md. |
| Claude Code | blocked | 2026-06-28 | Claude Code manual host UI run could not start in this environment because claude CLI was not found in PATH during live setup probe; MCP tools/resources were not observed in Claude Code. |
| Cursor | pending | none | manual UI run not recorded |
| Codex | passed | 2026-07-11 | Reviewer observed the interactive Codex TUI discover AlbumentationsX MCP tools; run_host_smoke_check returned status=ok, preview_ready=true, six passing diagnostics, and no warnings. Receipt: docs/host-evidence/codex-2026-07-11.md. |

## First 10 Minutes Replay

| Host | Status | Date | Evidence | Artifacts |
| --- | --- | --- | --- | --- |
| Claude Desktop | pending | none | first 10 minutes replay not recorded |  |
| Claude Code | blocked | 2026-06-28 | Claude Code host run could not start in this environment because claude CLI was not found in PATH during live setup probe; first-10-minutes replay was not executed. | /tmp/albu-host-setup-probe-live.json, /tmp/albu-host-Claude-Code.md |
| Cursor | pending | none | first 10 minutes replay not recorded |  |
| Codex | passed | 2026-07-11 | Reviewer-observed interactive Codex TUI replay loaded the installed plugin and completed smoke check, onboarding, baseline and candidate previews, visual review, tuning decision, and export over one local fixture; sanitized receipt and contact sheets are committed. | docs/host-evidence/codex-2026-07-11.md, docs/assets/host-evidence/codex-2026-07-11-baseline.png, docs/assets/host-evidence/codex-2026-07-11-accepted.png |

## Minimum Release Acceptance

1. `albumentationsx://capabilities` lists expected tools, prompts, resources, roots, and limits.
2. `diagnose_environment` returns `status="ok"` or actionable `remediation_actions`.
3. `validate_preview_request` rejects missing and outside-root paths before rendering.
4. `export_preview_report` includes contact sheets, concrete feedback, and interactive tuning session timelines.
5. `export_preview_report` links exported Markdown tuning session artifacts when matching sessions exist.
6. `export_tuning_session` returns Markdown or JSON content plus artifact metadata suitable for handoff.
