# P0 Host Evidence Unblock Pack

Pack status: `blocked_evidence_triage_required`
RC reopen allowed: `false`

## Recovery Policy

Do not mark any P0 gate as passed until a real host run completes the gate and leaves a dated, reviewer-observed artifact or evidence note.

## Summary

- lane_count: `4`
- blocked_lane_count: `4`
- missing_lane_count: `0`

## Recovery Lanes

| Host | Gate | Failure Class | First Diagnostic | Record Command |
| --- | --- | --- | --- | --- |
| Codex | `first_10_minutes_replay` | `codex_tool_call_cancelled` | Confirm the host can list AlbumentationsX MCP tools and read albumentationsx://examples/client-smoke. | `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex completed first_10_minutes_replay in a real MCP host UI.' --artifact docs/assets/demo/demo_report.md` |
| Codex | `manual_host_ui` | `codex_tool_call_cancelled` | Confirm the host can list AlbumentationsX MCP tools and read albumentationsx://examples/client-smoke. | `uv run python scripts/record_host_manual_run.py --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex completed manual_host_ui in a real MCP host UI.'` |
| Claude Code | `first_10_minutes_replay` | `claude_cli_missing` | Install or expose the Claude Code CLI before running the MCP host proof. | `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed first_10_minutes_replay in a real MCP host UI.' --artifact docs/assets/demo/demo_report.md` |
| Claude Code | `manual_host_ui` | `claude_cli_missing` | Install or expose the Claude Code CLI before running the MCP host proof. | `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed manual_host_ui in a real MCP host UI.'` |

## Lane Details

### Codex / first_10_minutes_replay

- Evidence status: `blocked`
- Failure class: `codex_tool_call_cancelled`
- Acceptance criterion: Replace this blocked record with a dated passed record only after the real host completes first_10_minutes_replay.
- Diagnostics:
  - Confirm the host can list AlbumentationsX MCP tools and read albumentationsx://examples/client-smoke.
  - Repeat run_host_smoke_check from an interactive Codex session where MCP tool approval is visible.
  - If the tool is cancelled again, capture the host approval state and record a blocked note, not a pass.

- Record command: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex completed first_10_minutes_replay in a real MCP host UI.' --artifact docs/assets/demo/demo_report.md`

### Codex / manual_host_ui

- Evidence status: `blocked`
- Failure class: `codex_tool_call_cancelled`
- Acceptance criterion: Replace this blocked record with a dated passed record only after the real host completes manual_host_ui.
- Diagnostics:
  - Confirm the host can list AlbumentationsX MCP tools and read albumentationsx://examples/client-smoke.
  - Repeat run_host_smoke_check from an interactive Codex session where MCP tool approval is visible.
  - If the tool is cancelled again, capture the host approval state and record a blocked note, not a pass.

- Record command: `uv run python scripts/record_host_manual_run.py --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex completed manual_host_ui in a real MCP host UI.'`

### Claude Code / first_10_minutes_replay

- Evidence status: `blocked`
- Failure class: `claude_cli_missing`
- Acceptance criterion: Replace this blocked record with a dated passed record only after the real host completes first_10_minutes_replay.
- Diagnostics:
  - Install or expose the Claude Code CLI before running the MCP host proof.
  - Run `claude --version` in the same shell/session that starts the host proof.
  - Only replay the First 10 Minutes workflow after Claude Code can start the configured MCP server.

- Record command: `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed first_10_minutes_replay in a real MCP host UI.' --artifact docs/assets/demo/demo_report.md`

### Claude Code / manual_host_ui

- Evidence status: `blocked`
- Failure class: `claude_cli_missing`
- Acceptance criterion: Replace this blocked record with a dated passed record only after the real host completes manual_host_ui.
- Diagnostics:
  - Install or expose the Claude Code CLI before running the MCP host proof.
  - Run `claude --version` in the same shell/session that starts the host proof.
  - Only replay the First 10 Minutes workflow after Claude Code can start the configured MCP server.

- Record command: `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed manual_host_ui in a real MCP host UI.'`

## Post-Recovery Commands

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_p0_host_unblock_pack.py --output docs/P0_HOST_UNBLOCK_PACK.md`
- `uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md`
- `uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json`

## Source Docs

- `docs/P0_BLOCKER_TRIAGE.md`
- `docs/HOST_FAILURE_COOKBOOK.md`
- `docs/HOST_MANUAL_RUNS.json`
