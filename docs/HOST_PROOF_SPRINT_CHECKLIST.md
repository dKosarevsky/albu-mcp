# Host Proof Sprint Checklist

Package: `albumentationsx-mcp==1.17.1`
Ready for v1: `false`

## Current Blockers

- `manual_host_ui_pending`: At least one supported host lacks passed manual UI evidence.
- `first_10_minutes_replay_pending`: At least one supported host lacks passed First 10 Minutes replay evidence.

## Setup

- `uv run python scripts/export_manual_host_acceptance_packet.py --host '<host>' --output /tmp/albu-host-<host>.md`
- `uv run python scripts/check_host_proof_sprint.py`

## Host Runs

### Claude Desktop

- Manual UI status: `recorded`
- First 10 Minutes status: `missing`
- Run the packet prompt in the real host UI before recording evidence.
- Manual UI record command: `uv run python scripts/record_host_manual_run.py --host 'Claude Desktop' --status passed --date YYYY-MM-DD --evidence 'Claude Desktop listed MCP tools and completed run_host_smoke_check in the host UI.'`
- First 10 Minutes record command: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Desktop' --status passed --date YYYY-MM-DD --evidence 'Claude Desktop completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md`

### Claude Code

- Manual UI status: `blocked`
- First 10 Minutes status: `blocked`
- Run the packet prompt in the real host UI before recording evidence.
- Manual UI record command: `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code listed MCP tools and completed run_host_smoke_check in the host UI.'`
- First 10 Minutes record command: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md`

### Cursor

- Manual UI status: `missing`
- First 10 Minutes status: `missing`
- Run the packet prompt in the real host UI before recording evidence.
- Manual UI record command: `uv run python scripts/record_host_manual_run.py --host Cursor --status passed --date YYYY-MM-DD --evidence 'Cursor listed MCP tools and completed run_host_smoke_check in the host UI.'`
- First 10 Minutes record command: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Cursor --status passed --date YYYY-MM-DD --evidence 'Cursor completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md`

### Codex

- Manual UI status: `recorded`
- First 10 Minutes status: `recorded`
- Run the packet prompt in the real host UI before recording evidence.
- Manual UI record command: `uv run python scripts/record_host_manual_run.py --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex listed MCP tools and completed run_host_smoke_check in the host UI.'`
- First 10 Minutes record command: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md`


## Record After Each Host

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/check_first_10_minutes_replay.py --host '<host>'`

## Regenerate After Sprint

- `uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md`
- `uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md`
- `uv run python scripts/export_host_proof_sprint_checklist.py --output docs/HOST_PROOF_SPRINT_CHECKLIST.md`
- `uv run python scripts/check_release_readiness.py`
