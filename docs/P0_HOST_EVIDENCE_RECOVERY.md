# P0 Host Evidence Recovery

Recovery status: `blocked_until_real_host_evidence`
RC ready: `false`
RC reopen allowed: `false`

## Recovery Policy

Do not replace blocked P0 records until Codex and Claude Code complete the real MCP host flow and leave dated reviewer-observed evidence.

## Summary

- target_host_count: `2`
- required_gate_count: `4`
- passed_gate_count: `0`
- blocked_gate_count: `4`
- missing_gate_count: `0`

## Host Recovery Lanes

| Host | Status | Blocker | Gates | First Action | Next Doc |
| --- | --- | --- | --- | --- | --- |
| Codex | `blocked_tool_call_cancellation` | `codex_tool_call_cancelled` | `first_10_minutes_replay`, `manual_host_ui` | Run Codex with visible MCP tool approval and complete run_host_smoke_check. | `docs/CODEX_CANCELLATION_TRIAGE.md` |
| Claude Code | `blocked_until_claude_cli_visible` | `claude_cli_missing` | `first_10_minutes_replay`, `manual_host_ui` | Install or expose the Claude Code CLI, then import the AlbumentationsX MCP config. | `docs/CLAUDE_CODE_SETUP_PATH.md` |

## Record Commands

### Codex

Passed evidence:
- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex completed first_10_minutes_replay in a real MCP host UI.' --artifact docs/assets/demo/demo_report.md`
- `uv run python scripts/record_host_manual_run.py --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex completed manual_host_ui in a real MCP host UI.'`

Blocked evidence:
- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status blocked --date YYYY-MM-DD --evidence 'Codex cancelled or blocked run_host_smoke_check before first_10_minutes_replay could pass in the real MCP host UI.'`
- `uv run python scripts/record_host_manual_run.py --host Codex --status blocked --date YYYY-MM-DD --evidence 'Codex cancelled or blocked run_host_smoke_check before manual_host_ui could pass in the real MCP host UI.'`

### Claude Code

Passed evidence:
- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed first_10_minutes_replay in a real MCP host UI.' --artifact docs/assets/demo/demo_report.md`
- `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed manual_host_ui in a real MCP host UI.'`

Blocked evidence:
- `uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status blocked --date YYYY-MM-DD --evidence 'Claude Code CLI was not visible or could not start MCP before first_10_minutes_replay could pass.'`
- `uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status blocked --date YYYY-MM-DD --evidence 'Claude Code CLI was not visible or could not start MCP before manual_host_ui could pass.'`

## Post-Recovery Commands

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_p0_evidence_status.py --output docs/P0_EVIDENCE_STATUS.md`
- `uv run python scripts/export_p0_host_evidence_recovery.py --output docs/P0_HOST_EVIDENCE_RECOVERY.md`
- `uv run python scripts/export_rc_dry_run.py --output docs/RC_DRY_RUN.md`
- `uv run python scripts/check_v1_rc_cutover_gate.py --require-open --format json`

## Source Docs

- `docs/P0_EVIDENCE_STATUS.md`
- `docs/HOST_EVIDENCE_RUNNER.md`
- `docs/CODEX_CANCELLATION_TRIAGE.md`
- `docs/CLAUDE_CODE_SETUP_PATH.md`
- `docs/HOST_MANUAL_RUNS.json`
