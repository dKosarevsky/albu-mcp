# V1 Launch Report

Package: `albumentationsx-mcp`
MCP name: `io.github.dKosarevsky/albu-mcp`
Package version: `1.15.0`
Server version: `1.15.0`
Ready for v1: `false`
Host proof status: `docs/HOST_PROOF_STATUS.md`

## Blockers

- `manual_host_ui_pending` (high): At least one supported host lacks passed manual UI evidence.
- `first_10_minutes_replay_pending` (high): At least one supported host lacks passed First 10 Minutes replay evidence.

## Manual Host UI

- Claude Desktop: `pending` — manual host UI evidence not recorded
- Claude Code: `pending` — manual host UI evidence not recorded
- Cursor: `pending` — manual host UI evidence not recorded
- Codex: `pending` — manual host UI evidence not recorded

## First 10 Minutes Replay

- Claude Desktop: `pending` — first 10 minutes replay not recorded
- Claude Code: `pending` — first 10 minutes replay not recorded
- Cursor: `pending` — first 10 minutes replay not recorded
- Codex: `pending` — first 10 minutes replay not recorded

## Recommended Next Actions

- Run the host proof sprint in real MCP host UIs and record dated evidence.
- Replay docs/FIRST_10_MINUTES.md in target hosts and record artifacts.
- Re-run scripts/export_v1_launch_report.py after updating docs/HOST_MANUAL_RUNS.json.
