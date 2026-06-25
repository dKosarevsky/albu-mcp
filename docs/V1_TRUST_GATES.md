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
- Claude Code / manual Host UI evidence: `pending` — manual host UI evidence not recorded
- Cursor / manual Host UI evidence: `pending` — manual host UI evidence not recorded
- Codex / manual Host UI evidence: `pending` — manual host UI evidence not recorded
- Claude Desktop / first 10 minutes replay: `pending` — first 10 minutes replay not recorded
- Claude Code / first 10 minutes replay: `pending` — first 10 minutes replay not recorded
- Cursor / first 10 minutes replay: `pending` — first 10 minutes replay not recorded
- Codex / first 10 minutes replay: `pending` — first 10 minutes replay not recorded
