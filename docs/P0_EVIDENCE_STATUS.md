# P0 Evidence Status

Target hosts: `Codex, Claude Code`
RC decision: `hold_rc`
RC ready: `false`

## Summary

- host_count: `2`
- passed_gate_count: `0`
- required_gate_count: `4`
- blocked_gate_count: `0`
- missing_gate_count: `4`

## Gate Status

| Host | Gate | Status | Next Action |
| --- | --- | --- | --- |
| Codex | `first_10_minutes_replay` | `missing` | `run_first_10_minutes_replay` |
| Codex | `manual_host_ui` | `missing` | `run_manual_host_ui` |
| Claude Code | `first_10_minutes_replay` | `missing` | `run_first_10_minutes_replay` |
| Claude Code | `manual_host_ui` | `missing` | `run_manual_host_ui` |

## Next Action

Run P0 host runbook and record real UI evidence.
