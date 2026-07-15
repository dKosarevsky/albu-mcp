# V1 Launch Report

> **Historical status snapshot.** This document preserves a pre-release decision and does not describe the current published release. See [STATUS.md](STATUS.md).

Package: `albumentationsx-mcp`
MCP name: `io.github.dKosarevsky/albu-mcp`
Package version: `1.19.0`
Server version: `1.19.0`
Ready for v1: `false`
Host proof status: `docs/HOST_PROOF_STATUS.md`

## Blockers

- `manual_host_ui_pending` (high): At least one supported host lacks passed manual UI evidence.
- `first_10_minutes_replay_pending` (high): At least one supported host lacks passed First 10 Minutes replay evidence.

## Host Blockers

| Host | Priority | Gate | Status | Next Action |
| --- | --- | --- | --- | --- |
| Claude Desktop | `p1` | `first_10_minutes_replay` | `missing` | `run_first_10_minutes_replay` |
| Claude Code | `p0` | `first_10_minutes_replay` | `blocked` | `triage_blocker` |
| Claude Code | `p0` | `manual_host_ui` | `blocked` | `triage_blocker` |
| Cursor | `p1` | `first_10_minutes_replay` | `missing` | `run_first_10_minutes_replay` |
| Cursor | `p1` | `manual_host_ui` | `missing` | `run_manual_host_ui` |

Packet commands:
- Claude Desktop / first_10_minutes_replay: `uv run python scripts/export_manual_host_acceptance_packet.py --host 'Claude Desktop' --output /tmp/albu-host-claude-desktop.md`
- Claude Code / first_10_minutes_replay: `uv run python scripts/export_manual_host_acceptance_packet.py --host 'Claude Code' --output /tmp/albu-host-claude-code.md`
- Claude Code / manual_host_ui: `uv run python scripts/export_manual_host_acceptance_packet.py --host 'Claude Code' --output /tmp/albu-host-claude-code.md`
- Cursor / first_10_minutes_replay: `uv run python scripts/export_manual_host_acceptance_packet.py --host Cursor --output /tmp/albu-host-cursor.md`
- Cursor / manual_host_ui: `uv run python scripts/export_manual_host_acceptance_packet.py --host Cursor --output /tmp/albu-host-cursor.md`

## Manual Host UI

- Claude Desktop: `passed` — Claude Desktop has dated manual host UI evidence
- Claude Code: `blocked` — Claude Code manual host UI evidence is blocked
- Cursor: `pending` — manual host UI evidence not recorded
- Codex: `passed` — Codex has dated manual host UI evidence

## First 10 Minutes Replay

- Claude Desktop: `pending` — first 10 minutes replay not recorded
- Claude Code: `blocked` — Claude Code first 10 minutes replay is blocked
- Cursor: `pending` — first 10 minutes replay not recorded
- Codex: `passed` — Codex has dated passed first 10 minutes replay evidence

## Evidence Plan

- Claude Desktop: manual UI `recorded`, first 10 minutes `missing`
  - Manual UI: `uv run python scripts/record_host_manual_run.py --host 'Claude Desktop' --status passed --date YYYY-MM-DD --evidence 'Claude Desktop listed MCP tools and completed run_host_smoke_check in the host UI.'`
  - First 10 Minutes: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Desktop' --status passed --date YYYY-MM-DD --evidence 'Claude Desktop completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md`
- Claude Code: manual UI `blocked`, first 10 minutes `blocked`
  - Manual UI: `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code listed MCP tools and completed run_host_smoke_check in the host UI.'`
  - First 10 Minutes: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md`
- Cursor: manual UI `missing`, first 10 minutes `missing`
  - Manual UI: `uv run python scripts/record_host_manual_run.py --host Cursor --status passed --date YYYY-MM-DD --evidence 'Cursor listed MCP tools and completed run_host_smoke_check in the host UI.'`
  - First 10 Minutes: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Cursor --status passed --date YYYY-MM-DD --evidence 'Cursor completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md`
- Codex: manual UI `recorded`, first 10 minutes `recorded`
  - Manual UI: `uv run python scripts/record_host_manual_run.py --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex listed MCP tools and completed run_host_smoke_check in the host UI.'`
  - First 10 Minutes: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md`

## Recommended Next Actions

- Run the host proof sprint in real MCP host UIs and record dated evidence.
- Replay docs/FIRST_10_MINUTES.md in target hosts and record artifacts.
- Re-run scripts/export_v1_launch_report.py after updating docs/HOST_MANUAL_RUNS.json.
