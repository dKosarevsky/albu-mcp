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

## Evidence Plan

- Claude Desktop: manual UI `missing`, first 10 minutes `missing`
  - Manual UI: `uv run python scripts/record_host_manual_run.py --host 'Claude Desktop' --status passed --date YYYY-MM-DD --evidence 'Claude Desktop listed MCP tools and completed run_host_smoke_check in the host UI.'`
  - First 10 Minutes: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Desktop' --status passed --date YYYY-MM-DD --evidence 'Claude Desktop completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md`
- Claude Code: manual UI `missing`, first 10 minutes `missing`
  - Manual UI: `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code listed MCP tools and completed run_host_smoke_check in the host UI.'`
  - First 10 Minutes: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md`
- Cursor: manual UI `missing`, first 10 minutes `missing`
  - Manual UI: `uv run python scripts/record_host_manual_run.py --host Cursor --status passed --date YYYY-MM-DD --evidence 'Cursor listed MCP tools and completed run_host_smoke_check in the host UI.'`
  - First 10 Minutes: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Cursor --status passed --date YYYY-MM-DD --evidence 'Cursor completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md`
- Codex: manual UI `missing`, first 10 minutes `missing`
  - Manual UI: `uv run python scripts/record_host_manual_run.py --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex listed MCP tools and completed run_host_smoke_check in the host UI.'`
  - First 10 Minutes: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md`

## Recommended Next Actions

- Run the host proof sprint in real MCP host UIs and record dated evidence.
- Replay docs/FIRST_10_MINUTES.md in target hosts and record artifacts.
- Re-run scripts/export_v1_launch_report.py after updating docs/HOST_MANUAL_RUNS.json.
