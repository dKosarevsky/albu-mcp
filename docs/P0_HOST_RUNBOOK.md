# P0 Host Runbook

Package: `albumentationsx-mcp==1.16.0`
Target hosts: `Codex, Claude Code`
Ready for v1: `false`

## Evidence Policy

Never mark a host passed until a reviewer runs the real host UI. Keep hosts pending or blocked until the real UI run is observed.

## P0 Queue

| Order | Host | Next Action | Packet |
| --- | --- | --- | --- |
| 1 | Claude Code | `triage_blocker` | `uv run python scripts/export_manual_host_acceptance_packet.py --host 'Claude Code' --output /tmp/albu-host-claude-code.md` |

## Record Commands

### Claude Code

```bash
uv run python scripts/record_host_manual_run.py --kind first-10-minutes --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code completed First 10 Minutes smoke, validation, baseline/candidate render, comparison, and export in the real host UI.' --artifact docs/assets/demo/demo_report.md
uv run python scripts/record_host_manual_run.py --host 'Claude Code' --status passed --date YYYY-MM-DD --evidence 'Claude Code listed AlbumentationsX MCP tools/resources and completed run_host_smoke_check in the real host UI.'
```

## After P0 Runs

- `uv run python scripts/validate_host_manual_runs.py`
- `uv run python scripts/export_v1_rc_readiness_report.py --output docs/V1_RC_READINESS.md`
- `uv run python scripts/export_v1_decision_report.py --output docs/V1_DECISION_REPORT.md`
- `uv run python scripts/check_release_readiness.py`
