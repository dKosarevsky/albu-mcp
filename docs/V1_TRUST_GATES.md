# V1 Trust Gates

Package: `albumentationsx-mcp==1.15.0`
Ready for v1: `false`
Manual evidence required: `true`

## Release Decision

Do not cut v1.0.0 until every manual gate is passed.

## Automated Gates

- `release_readiness`: `configured` — scripts/check_release_readiness.py covers committed release gates.
- `host_proof_sprint_docs`: `configured` — docs/HOST_PROOF_SPRINT_CHECKLIST.md provides host-by-host commands.
- `v1_launch_report`: `configured` — docs/V1_LAUNCH_REPORT.md is generated from committed evidence state.

## Manual Gates

- Claude Desktop / manual Host UI evidence: `pending` — manual host UI evidence not recorded
- Claude Code / manual Host UI evidence: `blocked` — Claude Code manual host UI run could not start in this environment because claude CLI was not found in PATH; MCP tools/resources were not observed in Claude Code.
- Cursor / manual Host UI evidence: `pending` — manual host UI evidence not recorded
- Codex / manual Host UI evidence: `blocked` — Codex CLI host listed AlbumentationsX MCP resources/tools and read client-smoke, but run_host_smoke_check was cancelled twice before preview_ready could be confirmed.
- Claude Desktop / first 10 minutes replay: `pending` — first 10 minutes replay not recorded
- Claude Code / first 10 minutes replay: `blocked` — Claude Code host run could not start in this environment because claude CLI was not found in PATH; first-10-minutes replay was not executed.
- Cursor / first 10 minutes replay: `pending` — first 10 minutes replay not recorded
- Codex / first 10 minutes replay: `blocked` — Codex CLI host run reached AlbumentationsX MCP discovery and read albumentationsx://examples/client-smoke, but run_host_smoke_check returned user cancelled MCP tool call twice; preview_ready was not confirmed.
