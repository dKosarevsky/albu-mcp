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
- Claude Code / manual Host UI evidence: `blocked` — Claude Code manual host UI run could not start in this environment because claude CLI was not found in PATH during live setup probe; MCP tools/resources were not observed in Claude Code.
- Cursor / manual Host UI evidence: `pending` — manual host UI evidence not recorded
- Codex / manual Host UI evidence: `blocked` — Codex setup and P0 preflight passed, but no reviewer-observed real MCP host UI completed run_host_smoke_check or preview_ready confirmation in this session.
- Claude Desktop / first 10 minutes replay: `pending` — first 10 minutes replay not recorded
- Claude Code / first 10 minutes replay: `blocked` — Claude Code host run could not start in this environment because claude CLI was not found in PATH during live setup probe; first-10-minutes replay was not executed.
- Cursor / first 10 minutes replay: `pending` — first 10 minutes replay not recorded
- Codex / first 10 minutes replay: `blocked` — Codex setup and preflight passed in this environment, but this Codex API session did not expose a reviewer-observed real MCP host UI flow; first-10-minutes replay was not executed.
