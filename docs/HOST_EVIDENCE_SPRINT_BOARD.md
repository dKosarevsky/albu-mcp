# Host Evidence Sprint Board

Package: `albumentationsx-mcp==1.15.0`
Ready for v1: `false`

## Manual Evidence Policy

Never mark a host passed until a reviewer runs the real host UI. Do not paste synthetic evidence or mark generated smoke checks as host UI.

## Summary

- Hosts: `4`
- Passed manual Host UI: `0`
- Passed First 10 Minutes replay: `0`
- Blocked hosts: `2`

## Sprint Board

| Host | Priority | Manual UI | First 10 Minutes | Next Gate |
| --- | --- | --- | --- | --- |
| Codex | `p0` | `blocked` | `blocked` | `blocked` |
| Claude Code | `p0` | `blocked` | `blocked` | `blocked` |
| Cursor | `p1` | `missing` | `missing` | `first_10_minutes_replay` |
| Claude Desktop | `p1` | `missing` | `missing` | `first_10_minutes_replay` |

## Run Queue

| Order | Host | Priority | Next Action |
| --- | --- | --- | --- |
| 1 | Codex | `p0` | `triage_blocker` |
| 2 | Claude Code | `p0` | `triage_blocker` |
| 3 | Cursor | `p1` | `run_first_10_minutes_replay` |
| 4 | Claude Desktop | `p1` | `run_first_10_minutes_replay` |

## Packet Commands

### Codex

```bash
uv run python scripts/export_manual_host_acceptance_packet.py --host Codex --output /tmp/albu-host-codex.md
```

### Claude Code

```bash
uv run python scripts/export_manual_host_acceptance_packet.py --host 'Claude Code' --output /tmp/albu-host-claude-code.md
```

### Cursor

```bash
uv run python scripts/export_manual_host_acceptance_packet.py --host Cursor --output /tmp/albu-host-cursor.md
```

### Claude Desktop

```bash
uv run python scripts/export_manual_host_acceptance_packet.py --host 'Claude Desktop' --output /tmp/albu-host-claude-desktop.md
```


## Host Commands

### Codex

```bash
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md
uv run python scripts/record_host_manual_run.py --host Codex --status passed --date YYYY-MM-DD --evidence 'Codex listed MCP tools and completed run_host_smoke_check in the host UI.'
uv run python scripts/check_first_10_minutes_replay.py --host Codex
uv run python scripts/check_manual_host_acceptance.py --host Codex
```

### Claude Code

```bash
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md
uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code listed MCP tools and completed run_host_smoke_check in the host UI.'
uv run python scripts/check_first_10_minutes_replay.py --host 'Claude Code'
uv run python scripts/check_manual_host_acceptance.py --host 'Claude Code'
```

### Cursor

```bash
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host Cursor --status passed --date YYYY-MM-DD --evidence 'Cursor completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md
uv run python scripts/record_host_manual_run.py --host Cursor --status passed --date YYYY-MM-DD --evidence 'Cursor listed MCP tools and completed run_host_smoke_check in the host UI.'
uv run python scripts/check_first_10_minutes_replay.py --host Cursor
uv run python scripts/check_manual_host_acceptance.py --host Cursor
```

### Claude Desktop

```bash
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Desktop' --status passed --date YYYY-MM-DD --evidence 'Claude Desktop completed smoke check, preview validation, baseline and candidate render, comparison, and pipeline export.' --artifact docs/assets/demo/demo_report.md
uv run python scripts/record_host_manual_run.py --host 'Claude Desktop' --status passed --date YYYY-MM-DD --evidence 'Claude Desktop listed MCP tools and completed run_host_smoke_check in the host UI.'
uv run python scripts/check_first_10_minutes_replay.py --host 'Claude Desktop'
uv run python scripts/check_manual_host_acceptance.py --host 'Claude Desktop'
```

## Next Checks

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/check_first_10_minutes_replay.py`
- `uv run python scripts/check_manual_host_acceptance.py`
- `uv run python scripts/export_host_acceptance_report.py --output docs/HOST_ACCEPTANCE_EVIDENCE.md`
- `uv run python scripts/export_v1_launch_report.py --output docs/V1_LAUNCH_REPORT.md`
- `uv run python scripts/export_host_evidence_sprint_board.py --output docs/HOST_EVIDENCE_SPRINT_BOARD.md`
